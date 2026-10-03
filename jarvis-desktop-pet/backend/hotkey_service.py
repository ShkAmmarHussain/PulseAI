import asyncio
import ctypes
import logging
import sys
import threading

logger = logging.getLogger("backend")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "super": MOD_WIN,
}
_NAMED_KEYS = {
    "space": 0x20,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "enter": 0x0D,
    "return": 0x0D,
}


def parse_hotkey(spec):
    """'ctrl+alt+j' -> (mods, vk). Returns None when invalid/empty."""
    if not spec or not str(spec).strip():
        return None
    tokens = [t.strip().lower() for t in str(spec).split("+") if t.strip()]
    if len(tokens) < 2:
        return None
    mods = 0
    for t in tokens[:-1]:
        if t not in _MODIFIERS:
            return None
        mods |= _MODIFIERS[t]
    key = tokens[-1]
    if key in _MODIFIERS:
        return None
    if len(key) == 1 and key.isalpha():
        vk = ord(key.upper())
    elif len(key) == 1 and key.isdigit():
        vk = ord(key)
    elif key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    elif key in _NAMED_KEYS:
        vk = _NAMED_KEYS[key]
    else:
        return None
    return mods, vk


class HotkeyService:
    """Global push-to-talk hotkey (Windows RegisterHotKey) toggling voice listen."""

    def __init__(self, voice):
        self.voice = voice
        self._loop = None
        self._thread = None
        self._tid = None
        self._tid_ready = threading.Event()
        self._spec = None

    def start(self, spec):
        self.stop()
        self._spec = spec or None
        parsed = parse_hotkey(self._spec)
        if parsed is None:
            if self._spec:
                logger.warning("invalid voice.hotkey '%s' (use e.g. ctrl+alt+j)", self._spec)
            else:
                logger.info("push-to-talk hotkey disabled")
            return False
        if sys.platform != "win32":
            logger.warning("push-to-talk hotkey only supported on Windows")
            return False
        self._loop = asyncio.get_event_loop()
        self._tid_ready.clear()
        self._tid = None
        self._thread = threading.Thread(target=self._run, args=parsed, daemon=True, name="hotkey")
        self._thread.start()
        return True

    def stop(self):
        t = self._thread
        if t and t.is_alive():
            if self._tid_ready.wait(1.0) and self._tid:
                ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            t.join(timeout=2.0)
        self._thread = None
        self._tid = None
        self._tid_ready.clear()

    def _run(self, mods, vk):
        user32 = ctypes.windll.user32
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        self._tid_ready.set()
        if not user32.RegisterHotKey(None, 1, mods | MOD_NOREPEAT, vk):
            logger.error("register hotkey failed (combo already in use?): vk=0x%02X mods=0x%X", vk, mods)
            return
        logger.info("push-to-talk hotkey registered: %s (vk=0x%02X, mods=0x%X)", self._spec, vk, mods)
        from ctypes import byref, wintypes

        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and self._loop:
                    asyncio.run_coroutine_threadsafe(self._toggle(), self._loop)
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        finally:
            user32.UnregisterHotKey(None, 1)
            logger.info("push-to-talk hotkey unregistered")

    async def _toggle(self):
        try:
            if not self.voice:
                return
            if self.voice.state == "test":
                return
            await self.voice.set_listening(self.voice.state != "listening")
        except Exception:
            logger.exception("hotkey toggle failed")
