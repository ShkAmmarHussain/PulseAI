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
    """Global hotkeys (Windows RegisterHotKey): push-to-talk + dictation toggle.

    id 1 = push-to-talk (voice.hotkey), id 2 = dictate-to-cursor
    (voice.dictation_hotkey, default ctrl+alt+d - spec 29, section 3.2).
    """

    def __init__(self, voice):
        self.voice = voice
        self._loop = None
        self._thread = None
        self._tid = None
        self._tid_ready = threading.Event()
        self._spec = None
        self._dict_spec = None

    def start(self, spec, dictation_spec=None):
        self.stop()
        self._spec = spec or None
        self._dict_spec = dictation_spec or None
        parsed = parse_hotkey(self._spec)
        dparsed = parse_hotkey(self._dict_spec)
        if self._spec and parsed is None:
            logger.warning("invalid voice.hotkey '%s' (use e.g. ctrl+alt+j)", self._spec)
        elif not self._spec:
            logger.info("push-to-talk hotkey disabled")
        if self._dict_spec and dparsed is None:
            logger.warning("invalid voice.dictation_hotkey '%s' (use e.g. ctrl+alt+d)", self._dict_spec)
        if dparsed and dparsed == parsed:
            logger.warning("dictation hotkey '%s' collides with push-to-talk; dictation hotkey disabled", self._dict_spec)
            dparsed = None
        if parsed is None and dparsed is None:
            return False
        if sys.platform != "win32":
            logger.warning("global hotkeys only supported on Windows")
            return False
        self._loop = asyncio.get_event_loop()
        self._tid_ready.clear()
        self._tid = None
        self._thread = threading.Thread(
            target=self._run, args=(parsed, dparsed), daemon=True, name="hotkey"
        )
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

    def _run(self, voice_combo, dict_combo):
        user32 = ctypes.windll.user32
        self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
        self._tid_ready.set()
        registered = []
        try:
            for hid, combo, label in (
                (1, voice_combo, self._spec),
                (2, dict_combo, self._dict_spec),
            ):
                if combo is None:
                    continue
                mods, vk = combo
                if user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk):
                    registered.append(hid)
                    logger.info("hotkey registered: %s (id=%d, vk=0x%02X mods=0x%X)", label, hid, vk, mods)
                else:
                    logger.error("register hotkey failed (combo already in use?): id=%d %s", hid, label)
            if not registered:
                return
            from ctypes import byref, wintypes

            msg = wintypes.MSG()
            while user32.GetMessageW(byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY and self._loop:
                    if msg.wParam == 2:
                        asyncio.run_coroutine_threadsafe(self._toggle_dictation(), self._loop)
                    else:
                        asyncio.run_coroutine_threadsafe(self._toggle(), self._loop)
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        finally:
            for hid in registered:
                user32.UnregisterHotKey(None, hid)
            if registered:
                logger.info("hotkeys unregistered (%d)", len(registered))

    async def _toggle(self):
        try:
            if not self.voice:
                return
            if self.voice.state == "test":
                return
            await self.voice.set_listening(self.voice.state != "listening")
        except Exception:
            logger.exception("hotkey toggle failed")

    async def _toggle_dictation(self):
        try:
            if not self.voice:
                return
            if self.voice.state == "test":
                return
            await self.voice.set_dictation(not self.voice.is_dictating)
        except Exception:
            logger.exception("dictation hotkey toggle failed")
