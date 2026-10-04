"""Win32 dictation injector tests (spec 29, section 3.2).

Types into a focused tkinter widget owned by this test - never into random
windows. Run: .venv/Scripts/python tests/injector_test.py   (exit 0 = pass)
"""

import ctypes
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# keep the test's history out of the real dictation log
_tmp_hist = tempfile.mkdtemp(prefix="jarvis-dict-test-")
os.environ["JARVIS_DICTATION_HISTORY"] = _tmp_hist

from tools import dictation_injector as di

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def focus_editor(root, text):
    """Force the test editor to the OS foreground (SendInput targets the
    foreground window, so this must hold before every injection).

    Uses GetAncestor + AttachThreadInput - no synthetic key events (an ALT
    tap would drop Tk into a modal menu loop inside update())."""
    import ctypes

    u32 = ctypes.windll.user32
    GA_ROOT = 2
    top = u32.GetAncestor(root.winfo_id(), GA_ROOT)
    for _ in range(3):
        if u32.GetForegroundWindow() == top:
            root.focus_force()
            text.focus_set()
            root.update()
            return True
        fg = u32.GetForegroundWindow()
        fg_tid = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        u32.AttachThreadInput(my_tid, fg_tid, True)
        u32.SetForegroundWindow(top)
        u32.AttachThreadInput(my_tid, fg_tid, False)
        time.sleep(0.15)
        root.focus_force()
        text.focus_set()
        root.update()
    return u32.GetForegroundWindow() == top


def make_focused_editor():
    import tkinter as tk

    root = tk.Tk()
    root.title("Jarvis injector test")
    root.geometry("420x180+120+120")
    root.attributes("-topmost", True)
    text = tk.Text(root, font=("Consolas", 12))
    text.pack(fill="both", expand=True)
    root.update()
    root.lift()
    root.focus_force()
    text.focus_set()
    root.update()
    time.sleep(0.25)
    root.update()
    return root, text


def main():
    orig_clip = di._clipboard_get()
    root, text = make_focused_editor()

    try:
        check("editor focused", focus_editor(root, text), hex(ctypes.windll.user32.GetForegroundWindow()))

        # foreground app title is readable
        title = di.foreground_app()
        check("foreground app title captured", bool(title), title)

        # short text goes through SendInput into the focused widget
        check("focused before sendinput", focus_editor(root, text))
        res = di.inject("hello jarvis 42")
        text.update()
        time.sleep(0.3)
        text.update()
        got = text.get("1.0", "end-1c")
        check("sendinput injection", res.get("injected") and got == "hello jarvis 42", (res, repr(got)))
        check("injection method recorded", res.get("method") == "sendinput", res.get("method"))
        check("app title on result", res.get("app") == "Jarvis injector test", res.get("app"))

        # newline maps to Enter
        text.delete("1.0", "end")
        check("focused before newline inject", focus_editor(root, text))
        res = di.inject("line one\nline two")
        text.update()
        time.sleep(0.3)
        text.update()
        got = text.get("1.0", "end-1c")
        check("newline injection", res.get("injected") and got == "line one\nline two", (res, repr(got)))

        # large block uses clipboard paste and restores the previous clipboard
        di._clipboard_set("PREVIOUS-CLIP-XYZ")
        time.sleep(0.1)
        big = ("dictation block " * 20).strip()  # > 200 chars
        text.delete("1.0", "end")
        check("focused before clipboard inject", focus_editor(root, text))
        # pump the widget WHILE inject runs, so Ctrl+V is processed while the
        # block is still on the clipboard (not after the restore)
        import threading

        box = {}
        done = threading.Event()

        def _run():
            box["res"] = di.inject(big)
            done.set()

        th = threading.Thread(target=_run, daemon=True)
        th.start()
        while not done.wait(0.03):
            root.update()
        th.join()
        text.update()
        time.sleep(0.3)
        text.update()
        got = text.get("1.0", "end-1c")
        res = box.get("res") or {}
        check("clipboard path for large block", res.get("injected") and res.get("method") == "clipboard", res)
        check("large block content", got == big, f"{len(got)}/{len(big)}")
        restored = di._clipboard_get()
        check("clipboard restored", restored == "PREVIOUS-CLIP-XYZ", repr(restored[:40]))

        # empty text is rejected without typing
        res = di.inject("   ")
        check("empty text rejected", res.get("injected") is False, res)
        check("widget untouched by empty inject", text.get("1.0", "end-1c") == got)

        # history append/read roundtrip (test-local directory)
        di.append_history({"ts": time.time(), "text": "hello", "app": "notepad", "injected": True})
        di.append_history({"ts": time.time(), "text": "world", "app": "notepad", "injected": False})
        entries = di.read_history(10)
        check("history roundtrip", [e["text"] for e in entries] == ["world", "hello"], entries)
        check("history path is test-local", str(di.HISTORY_PATH).startswith(_tmp_hist), str(di.HISTORY_PATH))
        limited = di.read_history(1)
        check("history limit", len(limited) == 1 and limited[0]["text"] == "world", limited)
    finally:
        if orig_clip:
            di._clipboard_set(orig_clip)
        try:
            root.destroy()
        except Exception:
            pass

    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
