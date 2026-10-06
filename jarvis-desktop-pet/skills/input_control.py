"""PC input automation (spec 32, section 4): mouse + keyboard via Win32
``SendInput``/``user32`` so no extra dependency is required.

Safety guardrails (spec 14, section 3):
- **Failsafe:** if the cursor is parked in the top-left ``(0, 0)`` corner,
  every operation aborts immediately with :class:`FailsafeError` (same
  contract as pyautogui's failsafe).
- **Boundary clamp:** coordinates are clamped to the primary screen.
- **Rate limit:** at most ``MAX_RATE_PER_SEC`` operations per second.

These functions never run on their own: the planner routes them through
guardrails (risk 7/10), so an approval card must be answered first unless
the permission policy is set to ``autonomous``.
"""

import ctypes
import ctypes.wintypes as wt
import logging
import threading
import time

logger = logging.getLogger(__name__)

MAX_RATE_PER_SEC = 20
_TYPE_CHUNK = 20          # failsafe re-check cadence while typing
_TYPE_DELAY = 0.012       # seconds between chunks

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

VK = {
    "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
    "win": 0x5B, "super": 0x5B, "meta": 0x5B,
    "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B,
    "tab": 0x09, "space": 0x20, "spacebar": 0x20,
    "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22, "pgup": 0x21, "pgdn": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "capslock": 0x14, "numlock": 0x90, "scrolllock": 0x91,
    "printscreen": 0x2C, "pause": 0x13,
    "comma": 0xBC, "period": 0xBE, "dot": 0xBE, "slash": 0xBF,
    "backslash": 0xDC, "semicolon": 0xBA, "quote": 0xDE,
    "backtick": 0xC0, "minus": 0xBD, "plus": 0xBB, "equals": 0xBB,
    "lbracket": 0xDB, "rbracket": 0xDD,
    ",": 0xBC, ".": 0xBE, "/": 0xBF, "\\": 0xDC, ";": 0xBA,
    "'": 0xDE, "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
}
for _i in range(1, 25):
    VK[f"f{_i}"] = 0x70 + _i - 1
for _c in range(26):
    VK[chr(ord("a") + _c)] = ord("A") + _c
for _d in range(10):
    VK[str(_d)] = ord("0") + _d
MODIFIERS = {"ctrl", "control", "alt", "shift", "win", "super", "meta"}

_rate_lock = threading.Lock()
_rate_hits: list = []


class FailsafeError(RuntimeError):
    """Cursor reached the (0, 0) corner: abort the whole input action."""


class InputError(RuntimeError):
    """Bad key name / coordinates."""


def _check_rate() -> None:
    now = time.monotonic()
    with _rate_lock:
        while _rate_hits and now - _rate_hits[0] > 1.0:
            _rate_hits.pop(0)
        if len(_rate_hits) >= MAX_RATE_PER_SEC:
            raise InputError(f"input rate limit ({MAX_RATE_PER_SEC}/s) exceeded")
        _rate_hits.append(now)


def check_failsafe() -> None:
    """Raise FailsafeError when the mouse sits in the top-left corner."""
    pt = wt.POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        return
    if pt.x <= 0 and pt.y <= 0:
        raise FailsafeError("mouse at top-left corner (0,0): input aborted")


def _screen_size() -> tuple:
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (w or 1920, h or 1080)


def _clamp(x: int, y: int) -> tuple:
    w, h = _screen_size()
    return max(0, min(int(x), w - 1)), max(0, min(int(y), h - 1))


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", _INPUTUNION)]


def _send(inputs: list) -> int:
    arr = (_INPUT * len(inputs))(*inputs)
    return user32.SendInput(len(inputs), ctypes.byref(arr), ctypes.sizeof(_INPUT))


def _key_input(vk: int = 0, scan: int = 0, flags: int = 0, unicode_: bool = False) -> _INPUT:
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki = _KEYBDINPUT(0 if unicode_ else vk, scan, flags, 0, None)
    if unicode_:
        inp.union.ki.wVk = 0
        inp.union.ki.wScan = scan
        inp.union.ki.dwFlags = flags | KEYEVENTF_UNICODE
    return inp


def _resolve(key: str) -> int:
    k = str(key).strip().lower().replace(" ", "")
    if k in VK:
        return VK[k]
    if len(k) == 1:
        if k.isalnum():
            return ord(k.upper())
        shifted = user32.VkKeyScanW(ord(k))
        if shifted != -1:
            return shifted & 0xFF
    raise InputError(f"unknown key: {key!r}")


# ---------- capabilities ----------


def type_text(text: str) -> str:
    """Type into whichever field currently has focus (Unicode SendInput)."""
    text = str(text or "")
    if not text:
        return "Nothing to type."
    _check_rate()
    total = 0
    for i in range(0, len(text), _TYPE_CHUNK):
        check_failsafe()
        chunk = text[i:i + _TYPE_CHUNK]
        inputs = [_key_input(scan=ord(c), flags=KEYEVENTF_UNICODE, unicode_=True) for c in chunk]
        total += _send(inputs) or len(inputs)
        time.sleep(_TYPE_DELAY)
    return f"Typed {total} character(s)."


def press_hotkey(keys) -> str:
    """Press a combination like ["ctrl", "c"] or "ctrl+shift+s"."""
    if isinstance(keys, str):
        keys = [p for p in keys.replace("+", " ").split() if p]
    keys = list(keys or [])
    if not keys:
        raise InputError("no keys given")
    _check_rate()
    vks = [_resolve(k) for k in keys]
    held = [vk for vk, k in zip(vks, keys) if str(k).strip().lower() in MODIFIERS]
    tap = [vk for vk in vks if vk not in held]
    check_failsafe()
    down, up = [], []
    for vk in held:
        down.append(_key_input(vk=vk))
    for vk in tap or held[-1:]:
        down.append(_key_input(vk=vk))
        up.append(_key_input(vk=vk, flags=KEYEVENTF_KEYUP))
    for vk in reversed(held):
        up.append(_key_input(vk=vk, flags=KEYEVENTF_KEYUP))
    if _send(down + up) == 0:
        raise InputError("SendInput failed (blocked by UIPI?)")
    return "Pressed " + "+".join(keys) + "."


def click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Move to (x, y) and click. Clamped to the screen, failsafe checked."""
    _check_rate()
    x, y = _clamp(x, y)
    check_failsafe()
    if not user32.SetCursorPos(int(x), int(y)):
        raise InputError("SetCursorPos failed")
    btn = str(button or "left").lower()
    if btn.startswith("r"):
        flags = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
    elif btn.startswith("m"):
        flags = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
    else:
        flags = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
    n = max(1, min(int(clicks or 1), 5))
    for i in range(n):
        check_failsafe()
        mi = _MOUSEINPUT(0, 0, 0, flags[0], 0, None)
        inp = _INPUT(); inp.type = INPUT_MOUSE; inp.union.mi = mi
        mi2 = _MOUSEINPUT(0, 0, 0, flags[1], 0, None)
        inp2 = _INPUT(); inp2.type = INPUT_MOUSE; inp2.union.mi = mi2
        _send([inp, inp2])
        if i < n - 1:
            time.sleep(0.06)
    return f"Clicked {btn} at {x},{y} ({n}x)."


def move_mouse(x: int, y: int, steps: int = 20) -> str:
    """Smooth cursor glide to (x, y) with failsafe checks on every step."""
    _check_rate()
    x, y = _clamp(x, y)
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    steps = max(1, min(int(steps or 20), 60)
                )
    for i in range(1, steps + 1):
        check_failsafe()
        nx = int(pt.x + (x - pt.x) * i / steps)
        ny = int(pt.y + (y - pt.y) * i / steps)
        user32.SetCursorPos(nx, ny)
        time.sleep(0.008)
    return f"Moved mouse to {x},{y}."
