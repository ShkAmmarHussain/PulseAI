"""Dictation end-to-end over the backend WS (spec 29, sections 3.2 + 3.3 + 7.1).

Covers: vocabulary get/save, dictation start/stop events, apply (dictionary ->
injection -> history -> dictation.result) into a focused test widget, history
readback, and the global Ctrl+Alt+D hotkey roundtrip.

Run (backend on :8765): .venv/Scripts/python tests/dictation_flow_test.py
exit 0 = pass
"""

import asyncio
import ctypes
import json
import sys
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

WS = "ws://127.0.0.1:8765/ws"
VK_CONTROL, VK_MENU, VK_D = 0x11, 0x12, 0x44

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def press_ctrl_alt_d():
    u = ctypes.windll.user32
    for vk, down in ((VK_CONTROL, True), (VK_MENU, True), (VK_D, True), (VK_D, False), (VK_MENU, False), (VK_CONTROL, False)):
        u.keybd_event(vk, 0, 0 if down else 0x0002, 0)
        time.sleep(0.05)


def focus_top(hwnd_child):
    """Bring the target toplevel to the OS foreground (GetAncestor +
    AttachThreadInput - no synthetic keys, they can trap Tk in a menu loop)."""
    import ctypes

    u32 = ctypes.windll.user32
    top = u32.GetAncestor(hwnd_child, 2)
    for _ in range(3):
        if u32.GetForegroundWindow() == top:
            return True
        fg = u32.GetForegroundWindow()
        fg_tid = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        u32.AttachThreadInput(my_tid, fg_tid, True)
        u32.SetForegroundWindow(top)
        u32.AttachThreadInput(my_tid, fg_tid, False)
        time.sleep(0.15)
    return u32.GetForegroundWindow() == top


def make_focus_target():
    """A tkinter widget this test owns - the backend types into IT, never
    into the user's real windows."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Jarvis dictation flow")
    root.geometry("400x150+160+420")
    root.attributes("-topmost", True)
    text = tk.Text(root)
    text.pack(fill="both", expand=True)
    root.update()
    root.lift()
    root.focus_force()
    text.focus_set()
    hwnd = root.winfo_id()
    focus_top(hwnd)
    time.sleep(0.2)
    root.update()
    return root, text, hwnd


class Client:
    def __init__(self, ws):
        self.ws = ws
        self.msgs = []

    async def send(self, obj):
        await self.ws.send_str(json.dumps(obj))

    async def wait_for(self, pred, seconds):
        end = time.time() + seconds
        while time.time() < end:
            for m in self.msgs:
                if pred(m):
                    return m
            try:
                m = await asyncio.wait_for(self.ws.receive(), timeout=max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                break
            if m.type != aiohttp.WSMsgType.TEXT:
                break
            self.msgs.append(json.loads(m.data))
        for m in self.msgs:
            if pred(m):
                return m
        return None


async def main():
    root, text, hwnd = make_focus_target()
    focus_lost = []

    def ensure_focus():
        ok = focus_top(hwnd)
        root.focus_force()
        text.focus_set()
        root.update()
        return ok

    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(WS, timeout=30) as ws:
                c = Client(ws)

                # --- vocabulary (spec 3.3) ---
                await c.send({"type": "vocabulary_get"})
                r = await c.wait_for(lambda m: m.get("type") == "vocabulary" and not (m.get("payload") or {}).get("saved"), 5)
                mappings = (r or {}).get("payload", {}).get("mappings") or []
                check("vocabulary_get returns mappings", isinstance(mappings, list) and len(mappings) >= 1, len(mappings))

                original = mappings
                test_maps = original + [{"word": "jarviston", "heard_as": ["jarvis town", "jarvistown"]}]
                await c.send({"type": "vocabulary_save", "payload": {"mappings": test_maps}})
                r = await c.wait_for(lambda m: m.get("type") == "vocabulary" and (m.get("payload") or {}).get("saved"), 5)
                saved = (r or {}).get("payload", {}).get("mappings") or []
                check("vocabulary_save roundtrip", any(m.get("word") == "jarviston" for m in saved), len(saved))

                # --- dictation start via ws (spec 7.1) ---
                await c.send({"type": "dictation", "payload": {"action": "start"}})
                r = await c.wait_for(lambda m: m.get("type") == "dictation_ack", 6)
                ack = (r or {}).get("payload", {})
                check("dictation start ack", ack.get("ok") is True and ack.get("active") is True, ack)
                r = await c.wait_for(lambda m: m.get("topic") == "dictation.start", 4)
                check("dictation.start broadcast (spec 7.1)",
                      r is not None and (r.get("payload") or {}).get("mode") == "system_wide",
                      (r or {}).get("payload"))

                # --- apply: dictionary -> injector -> history -> result ---
                check("focus target in foreground", ensure_focus())
                test_text = "bring up cube control in element studio"
                await c.send({"type": "dictation", "payload": {"action": "apply", "text": test_text}})
                r = await c.wait_for(lambda m: m.get("type") == "dictation_ack" and (m.get("payload") or {}).get("text"), 8)
                ack = (r or {}).get("payload", {})
                expected = "bring up kubectl in LM Studio"
                check("apply ok + vocabulary applied", ack.get("ok") is True and ack.get("text") == expected, ack)
                check("apply injected", ack.get("injected") is True, ack)
                r = await c.wait_for(lambda m: m.get("topic") == "dictation.result", 5)
                check("dictation.result broadcast (spec 7.1)",
                      r is not None and (r.get("payload") or {}).get("text") == expected,
                      (r or {}).get("payload"))

                root.update()
                time.sleep(0.6)
                root.update()
                typed = text.get("1.0", "end-1c")
                check("text typed into focused widget", typed == expected, repr(typed))
                app = (r or {}).get("payload", {}).get("app") or ack.get("app")
                check("app title in result", "Jarvis dictation flow" in str(app), app)

                # --- history readback ---
                await c.send({"type": "dictation_history", "payload": {"limit": 10}})
                r = await c.wait_for(lambda m: m.get("type") == "dictation_history", 5)
                entries = (r or {}).get("payload", {}).get("entries") or []
                check("history contains the dictation",
                      any(e.get("text") == expected for e in entries), [e.get("text") for e in entries][:3])

                # --- stop via ws ---
                await c.send({"type": "dictation", "payload": {"action": "stop"}})
                r = await c.wait_for(lambda m: m.get("type") == "dictation_ack" and m.get("payload", {}).get("active") is False, 6)
                check("dictation stop ack", r is not None, (r or {}).get("payload"))
                r = await c.wait_for(lambda m: m.get("topic") == "dictation.stop", 4)
                check("dictation.stop broadcast", r is not None)

                # --- global hotkey Ctrl+Alt+D roundtrip (spec 3.2) ---
                c.msgs.clear()
                press_ctrl_alt_d()
                r = await c.wait_for(lambda m: m.get("topic") == "dictation.start", 6)
                check("ctrl+alt+d starts dictation", r is not None)
                await asyncio.sleep(0.8)
                c.msgs.clear()
                press_ctrl_alt_d()
                r = await c.wait_for(lambda m: m.get("topic") == "dictation.stop", 6)
                check("ctrl+alt+d stops dictation", r is not None)

                # restore original vocabulary
                await c.send({"type": "vocabulary_save", "payload": {"mappings": original}})
                await c.wait_for(lambda m: m.get("type") == "vocabulary" and (m.get("payload") or {}).get("saved"), 5)
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    if focus_lost:
        check("focus stayed on target", False, focus_lost)
    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
