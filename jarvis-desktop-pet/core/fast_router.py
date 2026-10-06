"""Zero-LLM deterministic fast-path intent router (spec 29, section 3.4).

Frequent one-turn commands (volume, media transport, app launching, power,
timers) execute in milliseconds through Windows-native APIs instead of the
Orchestrator -> Planner -> LLM pipeline. Anything that does not match a rule
with >= 90% confidence transparently falls back to the full pipeline.

Compound conjunctions ("pause spotify and turn down volume") are split into
parts and every part must route, otherwise the whole utterance falls back -
so no partial actions are ever executed.
"""

import asyncio
import difflib
import json
import logging
import os
import re
import time
import uuid

from core.bus import create_event

logger = logging.getLogger("fast_path")

CONFIDENCE_MIN = 0.9
_SPLIT_RE = re.compile(r"\s+(?:and|then)\s+|;\s*")

# ---------- pure pattern rules (no side effects) ----------


def _route_volume(t: str):
    if not re.search(r"\bvolume\b|\blouder\b|\bquieter\b|\bsofter\b", t):
        return None
    if re.search(r"\bunmute\b|\bvolume (?:back )?on\b", t):
        return {"op": "unmute"}
    if re.search(r"\bmute\b|\bvolume off\b", t):
        return {"op": "mute"}
    m = re.search(r"\bvolume\b[^\d]{0,14}(\d{1,3})\s*(?:%|percent)?", t) or re.search(
        r"\b(\d{1,3})\s*%\s*(?:volume|sound)\b", t
    )
    if m:
        pct = int(m.group(1))
        if 0 <= pct <= 100:
            return {"op": "set", "level": pct / 100.0}
    if re.search(r"\b(?:max(?:imum)?|full)\b.{0,12}\bvolume\b|\bvolume\b.{0,12}\b(?:max(?:imum)?|full)\b", t):
        return {"op": "set", "level": 1.0}
    if re.search(r"\bvolume\s*(?:up|higher)\b|\bturn(?:\s+it)?\s*up\b|\bincrease\s+(?:the\s+)?volume\b|\blouder\b", t):
        return {"op": "up"}
    if re.search(r"\bvolume\s*(?:down|lower)\b|\bturn(?:\s+it)?\s*down\b|\bdecrease\s+(?:the\s+)?volume\b|\bquieter\b|\bsofter\b", t):
        return {"op": "down"}
    return None


_MEDIA_NOUNS = ("spotify", "music", "media", "song", "track", "playlist", "podcast", "audio", "video")


def _route_media(t: str):
    has_noun = any(n in t for n in _MEDIA_NOUNS)
    if not has_noun:
        return None
    if re.search(r"\b(next|skip)\b", t):
        return {"op": "next"}
    if re.search(r"\b(previous|prev|back|last)\b", t):
        return {"op": "prev"}
    if re.search(r"\b(pause|stop)\b", t):
        return {"op": "pause"}
    if re.search(r"\b(play|resume|start)\b", t):
        return {"op": "play"}
    return None


def _route_power(t: str):
    if re.search(r"\bcancel(?:\s+the)?\s+(?:pending\s+)?(?:shut\s?down|shutdown)\b", t):
        return {"action": "cancel_shutdown"}
    if re.search(r"\bshut\s?down\b|\bpower\s*off\b|\bturn\s+off\s+(?:the\s+)?(?:pc|computer|machine)\b", t):
        return {"action": "shutdown"}
    if re.search(r"\block\s+(?:the\s+)?(?:pc|computer|screen|workstation|windows|desktop)\b", t):
        return {"action": "lock"}
    if re.search(
        r"\b(?:put\s+(?:the\s+)?(?:pc|computer|machine)\s+to\s+sleep|go\s+to\s+sleep|"
        r"(?:pc|computer|workstation)\s+sleep)\b",
        t,
    ):
        return {"action": "sleep"}
    return None


_TIMER_RE = re.compile(
    r"\b(?:set|start)?\s*(?:a|an)?\s*(?:timer|alarm|countdown)\s+for\s+(\d{1,4})\s*"
    r"(second|sec|minute|min|hour|hr)s?\b",
    re.IGNORECASE,
)
_TIMER_CANCEL_RE = re.compile(r"\b(?:cancel|stop|kill)\s+(?:the\s+|any\s+)?(?:timer|alarm|countdown)s?\b")


def _route_timer(t: str):
    if _TIMER_CANCEL_RE.search(t):
        return {"action": "cancel"}
    m = _TIMER_RE.search(t)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    mult = 1 if unit.startswith("sec") else 60 if unit.startswith("min") else 3600
    seconds = n * mult
    if seconds <= 0 or seconds > 24 * 3600:
        return None
    return {"action": "set", "seconds": seconds}


def _route_app(t: str):
    m = re.match(r"^(?:please\s+)?(?:open|launch|start|run|bring\s+up)\s+(?:the\s+|my\s+)?(.+?)[.!?]*$", t)
    if not m:
        return None
    target = m.group(1).strip()
    if not target or len(target) < 2:
        return None
    hit = match_app(target)
    if not hit:
        return None
    name, cmd, conf = hit
    return {"app": name, "cmd": cmd, "_confidence": conf}


def route_one(text: str):
    """(action, params, confidence) for a single clause, or None."""
    t = (text or "").strip().lower()
    if not t:
        return None
    for family, fn in (
        ("system_timer", _route_timer),
        ("system_power", _route_power),
        ("media_volume", _route_volume),
        ("media_control", _route_media),
    ):
        params = fn(t)
        if params:
            conf = params.pop("_confidence", 0.98)
            return family, params, max(conf, CONFIDENCE_MIN)
    params = _route_app(t)
    if params:
        conf = params.pop("_confidence", 0.95)
        if conf >= CONFIDENCE_MIN:
            return "app_open", params, conf
    return None


def split_compound(text: str):
    return [p.strip() for p in _SPLIT_RE.split((text or "").strip()) if p.strip()]


def route(text: str):
    """List of (action, params, confidence), or None if any part misses."""
    parts = split_compound(text)
    if not parts:
        return None
    out = []
    for part in parts:
        hit = route_one(part)
        if not hit:
            return None
        out.append(hit)
    return out


# ---------- application registry (apps.json + Start Menu) ----------

APPS_NAME = "apps.json"

DEFAULT_APPS = [
    {"name": "Notepad", "cmd": "notepad.exe", "aliases": ["notepad", "not pad", "notes"]},
    {"name": "Calculator", "cmd": "calc.exe", "aliases": ["calculator", "calc"]},
    {"name": "File Explorer", "cmd": "explorer.exe", "aliases": ["explorer", "file explorer", "files", "folder"]},
    {"name": "Command Prompt", "cmd": "cmd.exe", "aliases": ["cmd", "command prompt", "command"]},
    {"name": "PowerShell", "cmd": "powershell.exe", "aliases": ["powershell", "ps", "terminal shell"]},
    {"name": "Windows Terminal", "cmd": "wt.exe", "aliases": ["terminal", "windows terminal"]},
    {"name": "Task Manager", "cmd": "taskmgr.exe", "aliases": ["task manager", "taskmgr"]},
    {"name": "Control Panel", "cmd": "control.exe", "aliases": ["control panel", "controls"]},
    {"name": "Settings", "cmd": "ms-settings:", "aliases": ["settings", "windows settings"]},
    {"name": "Registry Editor", "cmd": "regedit.exe", "aliases": ["regedit", "registry editor", "registry"]},
    {"name": "Paint", "cmd": "mspaint.exe", "aliases": ["paint", "mspaint"]},
    {"name": "Snipping Tool", "cmd": "snippingtool.exe", "aliases": ["snipping tool", "snip", "screenshot tool"]},
    {"name": "Microsoft Edge", "cmd": "msedge.exe", "aliases": ["edge", "microsoft edge"]},
    {"name": "Google Chrome", "cmd": "chrome.exe", "aliases": ["chrome", "google chrome"]},
    {"name": "Spotify", "cmd": "spotify.exe", "aliases": ["spotify"]},
    {"name": "Visual Studio Code", "cmd": "code", "aliases": ["vs code", "vscode", "visual studio code", "code"]},
    {"name": "Device Manager", "cmd": "devmgmt.msc", "aliases": ["device manager"]},
    {"name": "Disk Cleanup", "cmd": "cleanmgr.exe", "aliases": ["disk cleanup", "cleanup"]},
]

_apps_cache = {"curated": None, "start_menu": None}


def load_apps(path=None):
    """Curated app list from the user copy of apps.json, else bundled/defaults."""
    if path is None:
        from core.config import BUNDLED_CONFIG_DIR, CONFIG_DIR

        for p in (CONFIG_DIR / APPS_NAME, BUNDLED_CONFIG_DIR / APPS_NAME):
            if p.exists():
                path = p
                break
    if path is not None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            apps = data.get("apps")
            if isinstance(apps, list) and apps:
                return [a for a in apps if isinstance(a, dict) and a.get("name")]
        except Exception:
            logger.exception("apps.json load failed (%s)", path)
    return [dict(a) for a in DEFAULT_APPS]


def _curated_apps():
    if _apps_cache["curated"] is None:
        _apps_cache["curated"] = load_apps()
    return _apps_cache["curated"]


def _start_menu_apps():
    """[(display_name, shortcut_path)] lazily scanned from the Start Menu."""
    if _apps_cache["start_menu"] is not None:
        return _apps_cache["start_menu"]
    found = []
    try:
        bases = []
        pd = os.environ.get("PROGRAMDATA")
        if pd:
            bases.append(os.path.join(pd, "Microsoft", "Windows", "Start Menu", "Programs"))
        ad = os.environ.get("APPDATA")
        if ad:
            bases.append(os.path.join(ad, "Microsoft", "Windows", "Start Menu", "Programs"))
        for base in bases:
            for root, _dirs, files in os.walk(base):
                for fn in files:
                    if fn.lower().endswith(".lnk"):
                        name = fn[:-4]
                        if name and "uninstall" not in name.lower():
                            found.append((name, os.path.join(root, fn)))
    except Exception:
        logger.exception("start menu scan failed")
    _apps_cache["start_menu"] = found
    return found


def match_app(target: str):
    """(display_name, command, confidence) for a spoken app name, or None."""
    t = (target or "").strip().lower()
    if not t:
        return None
    best = None
    for app in _curated_apps():
        name = str(app.get("name") or "")
        cmd = str(app.get("cmd") or "")
        stem = os.path.splitext(os.path.basename(cmd))[0].lower()
        aliases = [name] + [str(a) for a in app.get("aliases") or []]
        aliases = [a.strip().lower() for a in aliases if a and a.strip()]
        for alias in aliases:
            if alias == t or t == cmd.lower() or t == stem:
                return name, cmd, 1.0
            if len(t) >= 4 and (alias in t or t in alias):
                cand = (name, cmd, 0.95)
                if best is None or cand[2] > best[2]:
                    best = cand
            r = difflib.SequenceMatcher(None, alias, t).ratio()
            if r >= CONFIDENCE_MIN and (best is None or r > best[2]):
                best = (name, cmd, r)
    if best:
        return best
    for name, path in _start_menu_apps():
        low = name.lower()
        if low == t:
            return name, path, 0.98
        r = difflib.SequenceMatcher(None, low, t).ratio()
        if r >= CONFIDENCE_MIN and r > 0.9:
            return name, path, r
    return None


# ---------- Windows-native executors ----------


def _volume_endpoint():
    from pycaw.pycaw import AudioUtilities

    return AudioUtilities.GetSpeakers().EndpointVolume


def volume_state():
    import pythoncom

    pythoncom.CoInitialize()
    try:
        vol = _volume_endpoint()
        return int(round(vol.GetMasterVolumeLevelScalar() * 100)), bool(vol.GetMute())
    finally:
        pythoncom.CoUninitialize()


def apply_volume(params: dict) -> dict:
    import pythoncom

    op = (params or {}).get("op")
    pythoncom.CoInitialize()
    try:
        vol = _volume_endpoint()
        cur = vol.GetMasterVolumeLevelScalar()
        if op == "up":
            vol.SetMasterVolumeLevelScalar(min(1.0, cur + 0.1), None)
        elif op == "down":
            vol.SetMasterVolumeLevelScalar(max(0.0, cur - 0.1), None)
        elif op == "set":
            vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, float(params.get("level", cur)))), None)
        elif op == "mute":
            vol.SetMute(1, None)
        elif op == "unmute":
            vol.SetMute(0, None)
        pct, muted = int(round(vol.GetMasterVolumeLevelScalar() * 100)), bool(vol.GetMute())
        return {"percent": pct, "muted": muted}
    finally:
        pythoncom.CoUninitialize()


def apply_media(params: dict) -> str:
    from tools.dictation_injector import press_virtual_key

    op = (params or {}).get("op")
    key = {"pause": 0xB3, "play": 0xB3, "next": 0xB0, "prev": 0xB1}.get(op, 0xB3)
    press_virtual_key(key)
    return op


def apply_power(action: str) -> bool:
    import ctypes

    if action == "lock":
        return bool(ctypes.windll.user32.LockWorkStation())
    if action == "sleep":
        # SetSuspendState(Hibernate=FALSE, ForceCritical=TRUE, DisableWakeEvent=FALSE)
        return bool(ctypes.windll.powrprof.SetSuspendState(0, 1, 0))
    import subprocess

    if action == "shutdown":
        subprocess.Popen(["shutdown", "/s", "/t", "15"], creationflags=0x08000000)
        return True
    if action == "cancel_shutdown":
        subprocess.Popen(["shutdown", "/a"], creationflags=0x08000000)
        return True
    return False


def open_app(cmd: str) -> bool:
    try:
        os.startfile(cmd)
        return True
    except Exception:
        logger.exception("app open failed (%s)", cmd)
        return False


def _chime_block():
    import winsound

    for freq, ms in ((880, 150), (1174, 150), (1568, 320)):
        winsound.Beep(freq, ms)


# ---------- router service ----------


class FastRouter:
    def __init__(self, bus, cfg: dict):
        self.bus = bus
        self.cfg = cfg or {}
        self.enabled = True
        self._pending = {}
        self._timers = set()
        self._hits = 0
        self._by_action = {}
        self._last_latency_ms = 0.0
        self.update_config(self.cfg)

    def update_config(self, cfg: dict):
        self.cfg = cfg or {}
        fp = (self.cfg.get("config") or {}).get("fast_path") or {}
        self.enabled = bool(fp.get("enabled", True))

    def _approval_timeout_s(self) -> float:
        appr = (self.cfg.get("permissions") or {}).get("approvals") or {}
        try:
            return max(5.0, float(appr.get("timeout_ms", 45000))) / 1000.0
        except Exception:
            return 45.0

    def stats(self) -> dict:
        return {
            "enabled": self.enabled,
            "hits": self._hits,
            "by_action": dict(self._by_action),
            "last_latency_ms": round(self._last_latency_ms, 2),
            "approvals_pending": len(self._pending),
        }

    async def start(self):
        self.bus.subscribe("ui.approval.response", self._on_approval)

    # ---- dispatch ----

    async def try_handle(self, text: str, cid: str = None) -> bool:
        if not self.enabled or not (text or "").strip():
            return False
        t0 = time.perf_counter()
        intents = route(text)
        if not intents:
            return False
        await self.bus.publish(
            create_event("ui.chat", "chat", {"role": "user", "text": text.strip()}, correlation_id=cid)
        )
        replies = []
        for action, params, conf in intents:
            latency = (time.perf_counter() - t0) * 1000.0
            await self.bus.publish(
                create_event(
                    "intent.fast_path",
                    "fast_path",
                    {
                        "action": action,
                        "params": params,
                        "bypassed_llm": True,
                        "latency_ms": round(latency, 1),
                    },
                    correlation_id=cid,
                )
            )
            self._hits += 1
            self._by_action[action] = self._by_action.get(action, 0) + 1
            self._last_latency_ms = latency
            reply = await self._run(action, params, cid)
            if reply:
                replies.append(reply)
        summary = "; ".join(replies)
        if summary:
            await self.bus.publish(
                create_event("ui.chat", "chat", {"role": "assistant", "text": summary}, correlation_id=cid)
            )
            await self.bus.publish(create_event("voice.say", "say", {"text": summary}, correlation_id=cid))
        logger.info("fast path handled %d action(s) in %.1fms: %s", len(intents), self._last_latency_ms, text[:80])
        return True

    async def _run(self, action: str, params: dict, cid: str):
        try:
            if action == "media_volume":
                res = await asyncio.to_thread(apply_volume, params)
                op = params.get("op")
                if op == "mute":
                    return "Volume muted."
                if op == "unmute":
                    return "Volume unmuted."
                if op == "up" or op == "down":
                    return f"Volume {res['percent']} percent."
                return f"Volume set to {res['percent']} percent."
            if action == "media_control":
                await asyncio.to_thread(apply_media, params)
                return {
                    "pause": "Paused.",
                    "play": "Playing.",
                    "next": "Skipped to the next track.",
                    "prev": "Skipped to the previous track.",
                }.get(params.get("op"), "Done.")
            if action == "app_open":
                ok = await asyncio.to_thread(open_app, params.get("cmd") or "")
                return f"Opened {params.get('app')}." if ok else f"Could not open {params.get('app')}."
            if action == "system_power":
                return await self._power(params.get("action"), cid)
            if action == "system_timer":
                return await self._timer(params)
        except Exception:
            logger.exception("fast path action failed (%s %s)", action, params)
            return f"Could not run {action}."
        return None

    async def _power(self, action: str, cid: str):
        if action == "shutdown":
            return await self._request_shutdown_approval(cid)
        ok = await asyncio.to_thread(apply_power, action)
        if action == "lock":
            return "Locking the PC." if ok else "Could not lock the PC."
        if action == "sleep":
            return "Going to sleep." if ok else "Could not sleep."
        if action == "cancel_shutdown":
            return "Shutdown cancelled." if ok else "Nothing to cancel."
        return None

    async def _timer(self, params: dict):
        seconds = int(params.get("seconds") or 0)
        if params.get("action") == "cancel" or seconds <= 0:
            n = len(self._timers)
            for tsk in list(self._timers):
                tsk.cancel()
            self._timers.clear()
            return f"Cancelled {n} timer(s)." if n else "No timers to cancel."
        label = self._timer_label(seconds)

        async def _fire():
            try:
                await asyncio.sleep(seconds)
                await asyncio.to_thread(_chime_block)
                await self.bus.publish(
                    create_event("ui.chat", "chat", {"role": "assistant", "text": f"Done - {label} finished."})
                )
                await self.bus.publish(create_event("voice.say", "say", {"text": f"Done. {label} finished."}))
            except asyncio.CancelledError:
                raise
            finally:
                self._timers.discard(task)

        task = asyncio.create_task(_fire())
        self._timers.add(task)
        return f"Timer set for {self._timer_label(seconds)}."

    @staticmethod
    def _timer_label(seconds: int) -> str:
        if seconds % 3600 == 0 and seconds >= 3600:
            n = seconds // 3600
            unit = "hour" if n == 1 else "hours"
        elif seconds % 60 == 0 and seconds >= 60:
            n = seconds // 60
            unit = "minute" if n == 1 else "minutes"
        else:
            n = seconds
            unit = "second" if n == 1 else "seconds"
        return f"{n} {unit} timer"

    # ---- shutdown approval gate (spec 29, section 3.4) ----

    async def _request_shutdown_approval(self, cid: str):
        appr_cid = uuid.uuid4().hex

        async def _expire():
            await asyncio.sleep(self._approval_timeout_s())
            if self._pending.pop(appr_cid, None) is None:
                return
            await self.bus.publish(
                create_event("ui.approval_cancelled", "approval_cancelled", {"reason": "timeout"}, correlation_id=appr_cid)
            )
            await self.bus.publish(
                create_event(
                    "ui.chat", "chat",
                    {"role": "system", "text": "Approval timed out - treated as denied. Nothing was changed."},
                    correlation_id=appr_cid,
                )
            )
            await self.bus.publish(create_event("voice.say", "say", {"text": "Action denied. Nothing was changed."}))

        self._pending[appr_cid] = {"input_cid": cid, "expire": asyncio.create_task(_expire())}
        await self.bus.publish(
            create_event(
                "ui.approval",
                "approval",
                {
                    "action": {"action": "system_power", "cmd": "shutdown /s /t 15"},
                    "risk": 9,
                    "message": "Allow shutting down the PC? (system_power, risk 9/10)",
                },
                correlation_id=appr_cid,
            )
        )
        await self.bus.publish(
            create_event("ui.chat", "chat", {"role": "assistant", "text": "Shutting down needs your approval."})
        )
        await self.bus.publish(create_event("voice.say", "say", {"text": "I need your approval to proceed."}))
        return "Shutting down the PC needs approval."

    async def _on_approval(self, ev) -> bool:
        """True when the response belonged to a fast-path approval."""
        cid = ev.correlation_id
        pending = self._pending.get(cid) if cid else None
        if pending is None:
            return False
        entry = self._pending.pop(cid, None)
        if entry is None:
            return False
        entry["expire"].cancel()
        if (ev.payload or {}).get("allow"):
            await asyncio.to_thread(apply_power, "shutdown")
            reply = "Shutting down in 15 seconds. Say 'cancel shutdown' to abort."
        else:
            reply = "Action denied. Nothing was changed."
        await self.bus.publish(create_event("ui.chat", "chat", {"role": "assistant", "text": reply}, correlation_id=cid))
        await self.bus.publish(create_event("voice.say", "say", {"text": reply}, correlation_id=cid))
        return True
