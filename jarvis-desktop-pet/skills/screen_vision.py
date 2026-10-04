import asyncio
import base64
import io
import logging
import threading
import uuid

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = "Describe what is on this screenshot in detail."

_capture_lock = threading.Lock()


def capture(region: dict | None = None, max_width: int = 1280) -> tuple[bytes, int, int]:
    """Grab the primary monitor (or a region) -> (png_bytes, width, height)."""
    import mss
    from PIL import Image

    with mss.mss() as sct:
        if region:
            mon = {k: int(region.get(k, 0)) for k in ("left", "top", "width", "height")}
        else:
            mon = dict(sct.monitors[1])
        with _capture_lock:
            shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
    if img.width > max_width:
        img = img.resize((max_width, max(1, int(img.height * max_width / img.width))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img.width, img.height


def _vision_model(cfg: dict) -> str:
    roles = (((cfg or {}).get("agents") or {}).get("agent_roles")) or {}
    return (roles.get("vision") or {}).get("model_id") or "qwen2.5-vl-7b-instruct"


def describe_sync(cfg: dict, query: str, region: dict | None = None) -> str:
    from core import llm

    png, w, h = capture(region)
    b64 = base64.b64encode(png).decode("ascii")
    text = (query or "").strip() or DEFAULT_PROMPT
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Screenshot of the user's Windows desktop ({w}x{h}). {text}"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
            ],
        }
    ]
    return llm.chat_sync(cfg, _vision_model(cfg), messages, temperature=0.2, max_tokens=400)


async def _acquire(rtm, task_id: str) -> bool:
    if rtm is None:
        return False
    for _ in range(6):
        try:
            if await rtm.acquire_vision(task_id):
                return True
        except Exception:
            logger.exception("vision mutex acquire failed")
            return False
        await asyncio.sleep(0.5)
    return False


async def describe(
    cfg: dict,
    query: str,
    region: dict | None = None,
    rtm=None,
    task_id: str | None = None,
) -> str:
    """Screen describe under the vision mutex: capture on a worker thread,
    then hand the image to the on-demand VLM (loaded lazily via llm lifecycle)."""
    tid = task_id or uuid.uuid4().hex
    got = await _acquire(rtm, tid)
    if rtm is not None and not got:
        logger.warning("vision mutex busy - proceeding without it")
    try:
        return await asyncio.to_thread(describe_sync, cfg, query, region)
    finally:
        if got:
            await rtm.release_vision(tid)
