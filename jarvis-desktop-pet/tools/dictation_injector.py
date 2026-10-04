"""System-wide dictation text injection (spec 29, section 3.2).

Types transcribed text into whatever control holds keyboard focus:
  * primary - Win32 SendInput with KEYEVENTF_UNICODE per character
  * fallback / large blocks - clipboard Ctrl+V, restoring the previous
    clipboard contents 100ms afterwards

Every dictation is appended to %LOCALAPPDATA%\\Jarvis\\dictation_history.jsonl
(override the directory with JARVIS_DICTATION_HISTORY).
"""

import ctypes
import json
import logging
import os
import time
from ctypes import wintypes
from pathlib import Path

logger = logging.getLogger("dictation")

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_TAB = 0x09
VK_CONTROL = 0x11
VK_V = 0x56
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
CLIPBOARD_CHAR_LIMIT = 200

_hist_dir = os.environ.get("JARVIS_DICTATION_HISTORY")
HISTORY_PATH = (Path(_hist_dir) if _hist_dir else Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Jarvis") / "dictation_history.jsonl"


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _MOUSEINPUT(ctypes.Structure):
    # present so the INPUT union matches the native 40-byte layout on x64
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _user32():
    return ctypes.windll.user32


def _send(inputs) -> None:
    n = _user32().SendInput(len(inputs), inputs, ctypes.sizeof(_INPUT))
    if n != len(inputs):
        raise RuntimeError("SendInput failed (sent %d/%d)" % (n, len(inputs)))


def foreground_app() -> str:
    """Title of the window that currently holds keyboard focus."""
    u32 = _user32()
    hwnd = u32.GetForegroundWindow()
    if not hwnd:
        return ""
    n = u32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    u32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _press(vk: int, up: bool = False) -> None:
    arr = (_INPUT * 1)(
        _INPUT(type=INPUT_KEYBOARD,
               ki=_KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP if up else 0,
                              time=0, dwExtraInfo=0)),
    )
    _send(arr)


def _type_char(ch: str) -> None:
    arr = (_INPUT * 2)(
        _INPUT(type=INPUT_KEYBOARD, ki=_KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)),
        _INPUT(type=INPUT_KEYBOARD, ki=_KEYBDINPUT(wVk=0, wScan=ord(ch), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
    )
    _send(arr)


def press_virtual_key(vk: int) -> None:
    """Tap a virtual-key key (media transport, Enter, Tab...) via SendInput."""
    _press(vk)
    _press(vk, up=True)


def _clipboard_get() -> str:
    u32 = _user32()
    k32 = ctypes.windll.kernel32
    if not u32.OpenClipboard(None):
        return ""
    try:
        u32.GetClipboardData.restype = ctypes.c_void_p
        u32.GetClipboardData.argtypes = [wintypes.UINT]
        handle = u32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        ptr = k32.GlobalLock(handle)
        if not ptr:
            return ""
        text = ctypes.wstring_at(ptr)
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        k32.GlobalUnlock(handle)
        return text
    except Exception:
        return ""
    finally:
        u32.CloseClipboard()


def _clipboard_set(text: str) -> bool:
    u32 = _user32()
    k32 = ctypes.windll.kernel32
    if not u32.OpenClipboard(None):
        return False
    try:
        u32.EmptyClipboard()
        data = (text + "\0").encode("utf-16-le")
        k32.GlobalAlloc.restype = ctypes.c_void_p
        k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        handle = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        k32.GlobalLock.restype = ctypes.c_void_p
        k32.GlobalLock.argtypes = [ctypes.c_void_p]
        ptr = k32.GlobalLock(handle)
        if not ptr:
            k32.GlobalFree(handle)
            return False
        ctypes.memmove(ptr, data, len(data))
        k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        k32.GlobalUnlock(handle)
        u32.SetClipboardData.restype = ctypes.c_void_p
        u32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
        return bool(u32.SetClipboardData(CF_UNICODETEXT, handle))
    except Exception:
        logger.exception("clipboard set failed")
        return False
    finally:
        u32.CloseClipboard()


def _type_text(text: str) -> None:
    """SendInput per character; Enter/Tab are sent as virtual keys."""
    for ch in text:
        if ch == "\n":
            _press(VK_RETURN)
            _press(VK_RETURN, up=True)
        elif ch == "\r":
            continue
        elif ch == "\t":
            _press(VK_TAB)
            _press(VK_TAB, up=True)
        else:
            _type_char(ch)


def _paste_text(text: str) -> bool:
    prev = _clipboard_get()
    if not _clipboard_set(text):
        return False
    time.sleep(0.05)
    _press(VK_CONTROL)
    _press(VK_V)
    _press(VK_V, up=True)
    _press(VK_CONTROL, up=True)
    time.sleep(0.2)
    _clipboard_set(prev or "")
    return True


def inject(text: str) -> dict:
    """Type text into the focused control.

    Returns {"injected": bool, "app": str, "method": str}.
    """
    text = text if isinstance(text, str) else str(text or "")
    app = foreground_app()
    if not text.strip():
        return {"injected": False, "app": app, "method": "none", "error": "empty"}
    method = "clipboard" if len(text) > CLIPBOARD_CHAR_LIMIT else "sendinput"
    try:
        if method == "clipboard" and not _paste_text(text):
            method = "sendinput"
        if method == "sendinput":
            _type_text(text)
    except Exception as e:
        logger.exception("text injection failed")
        return {"injected": False, "app": app, "method": method, "error": str(e)}
    logger.info("injected %d char(s) via %s into '%s'", len(text), method, app or "?")
    return {"injected": True, "app": app, "method": method}


def append_history(entry: dict) -> None:
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("dictation history append failed")


def read_history(limit: int = 100) -> list:
    """Newest-first history entries."""
    entries = []
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-max(1, int(limit)):]:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        logger.exception("dictation history read failed")
    entries.reverse()
    return entries
