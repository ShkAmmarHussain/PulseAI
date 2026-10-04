import asyncio
import logging

from openai import OpenAI

logger = logging.getLogger("llm")

DEFAULT_BASE_URL = "http://localhost:1234/v1"


def _base_url(url: str | None) -> str:
    base = (url or DEFAULT_BASE_URL).strip().rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    # ::1 ("localhost") can blackhole SYNs when nothing listens; IPv4 refuses fast
    if base.lower().startswith("http://localhost"):
        base = "http://127.0.0.1" + base[len("http://localhost"):]
    elif base.lower().startswith("https://localhost"):
        base = "https://127.0.0.1" + base[len("https://localhost"):]
    return base


def _client(lm_cfg: dict, base_url: str | None = None) -> OpenAI:
    return OpenAI(
        base_url=_base_url(base_url or lm_cfg.get("base_url")),
        api_key=lm_cfg.get("api_key") or "lm-studio",
        timeout=(lm_cfg.get("timeout_ms") or 30000) / 1000,
        max_retries=int(lm_cfg.get("max_retries") or 1),
    )


def _model_name(model_id: str) -> str:
    return (model_id or "").strip().removesuffix("-gguf")


_lifecycle = None


def set_lifecycle(lc) -> None:
    """Installed by the app so chat calls load/offload models on demand."""
    global _lifecycle
    _lifecycle = lc


def chat_sync(cfg: dict, model_id: str, messages: list, temperature: float = 0.7, max_tokens: int = 256) -> str:
    lm = (cfg.get("config") or {}).get("lm_studio") or {}
    name = _model_name(model_id)
    if _lifecycle:
        _lifecycle.before_chat(name)
    client = _client(lm)
    try:
        last = None
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return (resp.choices[0].message.content or "").strip()
            except Exception as e:
                last = e
                # transient "model unloaded" right after startup/eviction -
                # re-ensure the model and retry once
                if attempt == 0 and "unloaded" in str(e).lower() and _lifecycle:
                    logger.info("model %s unloaded mid-call - reloading and retrying", name)
                    _lifecycle.before_chat(name)
                    continue
                raise
        raise last  # pragma: no cover
    finally:
        if _lifecycle:
            _lifecycle.after_chat(name)


async def chat(cfg: dict, model_id: str, messages: list, temperature: float = 0.7, max_tokens: int = 256) -> str:
    return await asyncio.to_thread(chat_sync, cfg, model_id, messages, temperature, max_tokens)


def test_lm_sync(url: str | None = None, cfg: dict | None = None) -> dict:
    lm = ((cfg or {}).get("config") or {}).get("lm_studio") or {}
    try:
        client = _client(lm, base_url=url)
        models = [m.id for m in client.models.list().data]
        return {"ok": True, "models": models, "base_url": _base_url(url or lm.get("base_url"))}
    except Exception as e:
        logger.warning("lm test failed: %s", e)
        return {"ok": False, "error": str(e), "base_url": _base_url(url or lm.get("base_url"))}


async def test_lm(url: str | None = None, cfg: dict | None = None) -> dict:
    return await asyncio.to_thread(test_lm_sync, url, cfg)
