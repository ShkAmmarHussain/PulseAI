"""Doc 30 visual inspection driver (section 3 + 7).

Drives the real app into each of the 8 mandated states, then captures the REAL
Tauri OS windows via scripts/inspect_ui.ps1:

    pet_idle, pet_hover, pet_speech, pet_approval      -> Jarvis Pet window
    dock_collapsed, dock_expanded                      -> Jarvis Dynamic Island
    main_app_expanded, main_app_collapsed              -> Jarvis main window
      (collapsed state reached by a real coordinate click on #sb-toggle,
       position probed from the mirrored CDP index tab)

Run with app + backend up, Edge CDP on 9334 (index/pet/dock tabs), LM Studio up:
    .venv/Scripts/python scripts/inspect_states.py
exit 0 = all 8 captures written to artifacts/ui_inspection/
"""

import asyncio
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_pet", "src")
OUT = os.path.join(ROOT, "artifacts", "ui_inspection")
PS1 = os.path.join(ROOT, "scripts", "inspect_ui.ps1")
CDP = "http://127.0.0.1:9334/json"
WS = "ws://127.0.0.1:8765/ws"
PROBE_FILE = os.path.join(os.environ["TEMP"], "opencode", "zz_inspect_probe.txt")

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

SW_RESTORE = 9

ok = []


def check(name, cond, extra=""):
    ok.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ((" | " + str(extra)) if extra != "" else ""), flush=True)


def find_window(title):
    result = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _l):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, buf, 512)
        if buf.value == title and user32.IsWindowVisible(h):
            result.append(h)
            return False
        return True

    user32.EnumWindows(cb, 0)
    return result[0] if result else None


def rect_of(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def client_origin(hwnd):
    p = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return (p.x, p.y)


def focus(hwnd):
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)


def move_cursor(x, y):
    user32.SetCursorPos(int(x), int(y))


def click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.12)
    user32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
    time.sleep(0.15)


def mouse_away():
    move_cursor(8, ctypes.windll.user32.GetSystemMetrics(1) - 8)


def capture(state):
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
         "-State", state, "-OutputDir", OUT],
        capture_output=True, text=True, timeout=30)
    line = (p.stdout or "").strip().splitlines()
    line = line[-1] if line else ""
    path = os.path.join(OUT, state + ".png")
    good = line.startswith("RESULT") and os.path.exists(path) and os.path.getsize(path) > 2000
    check("capture " + state, good, line or (p.stderr or "")[:200])
    return good


# ---------------------------------------------------------------- ws helpers
async def recv(ws, timeout):
    try:
        m = await asyncio.wait_for(ws.receive(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    if m.type == aiohttp.WSMsgType.TEXT:
        try:
            return json.loads(m.data)
        except Exception:
            return None
    return None


class Bus:
    """ws client that keeps draining broadcasts; records topics of interest."""

    def __init__(self, ws):
        self.ws = ws
        self.log = []

    async def pump(self, seconds):
        t = time.time() + seconds
        while time.time() < t:
            d = await self.recv(min(0.4, max(0.05, t - time.time())))
            if d:
                self.log.append(d)

    async def recv(self, timeout):
        return await recv(self.ws, timeout)

    async def send(self, obj):
        await self.ws.send_json(obj)
        # drain until quiet so we don't miss immediate replies
        return await self.pump(0.6)

    async def wait_topic(self, name, seconds, pred=None):
        t = time.time() + seconds
        while time.time() < t:
            d = await self.recv(min(1.0, max(0.1, t - time.time())))
            if not d:
                continue
            self.log.append(d)
            if (d.get("topic") or d.get("type")) == name and (pred is None or pred(d)):
                return d
        return None


# ---------------------------------------------------------------- cdp helpers
async def cdp_eval(ws, expr, timeout=15):
    await ws.send_json({"id": 999, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
    t = time.time() + timeout
    while time.time() < t:
        d = await recv(ws, timeout - (time.time() - t))
        if d and d.get("id") == 999:
            res = d.get("result", {})
            if "exceptionDetails" in res:
                return {"exc": str(res["exceptionDetails"])[:200]}
            return res.get("result", {}).get("value")
    return None


async def main():
    os.makedirs(OUT, exist_ok=True)
    io.open(PROBE_FILE, "w").write("visual inspection probe - safe to delete")

    async with aiohttp.ClientSession() as s:
        # ---- preflight ----
        async with s.ws_connect(WS, heartbeat=30) as ws:
            bus = Bus(ws)
            await bus.send({"type": "get_settings"})
            got = None
            for d in reversed(bus.log):
                if d.get("type") == "settings" or d.get("topic") == "settings":
                    got = d
                    break
            cfg = ((got or {}).get("payload") or {}).get("config") or {}
            check("backend settings reachable", bool(cfg), list(cfg.keys()))
            rt = cfg.get("runtime") or {}
            check("companion currently dock", rt.get("companion") == "dock" or rt.get("companion") == "pet",
                  rt.get("companion"))

            # normalize to spec defaults: porcelain colorway, pet companion, pet visible
            cfg.setdefault("runtime", {})
            cfg["runtime"]["companion"] = "pet"
            cfg["runtime"]["pet_enabled"] = True
            cfg["runtime"]["pet_colorway"] = "porcelain"
            await bus.send({"type": "save_settings", "payload": {"config": cfg}})
            await bus.pump(1.5)
            await bus.send({"type": "set_pet", "payload": {"enabled": True}})
            await bus.pump(1.5)

            # ---- pet states ----
            mouse_away()
            pet = find_window("Jarvis Pet")
            check("pet window present", pet is not None)
            if pet:
                focus(pet)
                time.sleep(6.5)  # let greeting/voice bubbles time out
                capture("pet_idle")

                l, t_, r, b = rect_of(pet)
                move_cursor((l + r) // 2, (t_ + b) // 2)
                time.sleep(0.8)
                capture("pet_hover")
                mouse_away()

                await bus.send({"type": "voice_listen", "payload": {"on": True}})
                await bus.wait_topic("ui.voice_state", 4, lambda d: ((d.get("payload") or {}).get("state")) == "listening")
                time.sleep(0.8)
                focus(pet)
                capture("pet_speech")
                await bus.send({"type": "voice_listen", "payload": {"on": False}})
                await bus.pump(2.0)

                # approval card on the pet. NOTE: text_input gets an instant
                # fast-path approval, so send()'s 0.6s drain may have already
                # consumed the broadcast - scan the log before waiting fresh.
                await bus.send({"type": "text_input",
                                "payload": {"text": "delete the file zz_inspect_probe.txt in %s"
                                            % os.path.dirname(PROBE_FILE)}})
                ap = None
                for d in bus.log:
                    if (d.get("topic") or d.get("type")) == "ui.approval":
                        ap = d
                if ap is None:
                    ap = await bus.wait_topic("ui.approval", 90)
                check("approval requested for inspection", ap is not None)
                if ap:
                    time.sleep(0.6)
                    focus(pet)
                    time.sleep(0.3)
                    capture("pet_approval")
                    cid = ap.get("correlation_id")
                    await bus.send({"type": "approval_response",
                                    "payload": {"allow": False, "action": "delete_file"},
                                    "correlation_id": cid})
                    await bus.wait_topic("ui.chat", 15,
                                         lambda d: "denied" in str(((d.get("payload") or {}).get("text") or "")).lower())
                    await bus.pump(4.0)

            # ---- dock states ----
            cfg2 = dict(cfg)
            cfg2["runtime"] = dict(cfg["runtime"], companion="dock")
            await bus.send({"type": "save_settings", "payload": {"config": cfg2}})
            await bus.pump(3.0)
            mouse_away()
            island = find_window("Jarvis Dynamic Island")
            check("dock window present", island is not None)
            if island:
                focus(island)
                time.sleep(1.0)
                capture("dock_collapsed")
                l, t_, r, b = rect_of(island)
                move_cursor((l + r) // 2, (t_ + b) // 2)
                time.sleep(1.0)
                focus(island)
                capture("dock_expanded")
                mouse_away()

            # ---- main workspace states ----
            cfg3 = dict(cfg)
            cfg3["runtime"] = dict(cfg["runtime"], companion="pet")
            await bus.send({"type": "save_settings", "payload": {"config": cfg3}})
            await bus.pump(2.5)
            await bus.send({"type": "set_pet", "payload": {"enabled": False}})
            await bus.pump(2.0)

            main_w = find_window("Jarvis")
            check("main window present", main_w is not None)

            # probe #sb-toggle geometry from the mirrored CDP index tab
            async with s.get(CDP) as r:
                ts = await r.json()
            idx = next((t for t in ts if t.get("type") == "page" and "index.html" in t.get("url", "")), None)
            check("index cdp tab present", idx is not None)
            tog_exp = tog_col = None
            if idx:
                async with s.ws_connect(idx["webSocketDebuggerUrl"], timeout=30) as cws:
                    await cws.send_json({"id": 1, "method": "Runtime.enable"})
                    await recv(cws, 2)
                    tog_exp = await cdp_eval(cws, """(() => {
                        const el = document.getElementById('app');
                        el.classList.remove('sb-collapsed');
                        const r = document.getElementById('sb-toggle').getBoundingClientRect();
                        return {x: r.x + r.width/2, y: r.y + r.height/2, vis: r.width > 0};
                    })()""")
                    await cdp_eval(cws, "document.getElementById('sb-toggle').click(); 1")
                    time.sleep(0.4)
                    tog_col = await cdp_eval(cws, """(() => {
                        const r = document.getElementById('sb-toggle').getBoundingClientRect();
                        return {x: r.x + r.width/2, y: r.y + r.height/2, vis: r.width > 0};
                    })()""")
                    await cdp_eval(cws, "document.getElementById('sb-toggle').click(); 1")
                    time.sleep(0.3)
            check("sb-toggle probed (expanded+collapsed)",
                  tog_exp and tog_col and tog_exp.get("vis") and tog_col.get("vis"),
                  (tog_exp, tog_col))

            if main_w and tog_exp:
                focus(main_w)
                time.sleep(0.4)
                capture("main_app_expanded")
                ox, oy = client_origin(main_w)
                click(ox + int(tog_exp["x"]), oy + int(tog_exp["y"]))
                time.sleep(0.6)
                capture("main_app_collapsed")
                if tog_col:
                    click(ox + int(tog_col["x"]), oy + int(tog_col["y"]))
                    time.sleep(0.4)
                mouse_away()

            # ---- restore ----
            await bus.send({"type": "set_pet", "payload": {"enabled": True}})
            await bus.pump(1.5)
            mouse_away()

    if os.path.exists(PROBE_FILE):
        os.remove(PROBE_FILE)
    print(f"== {sum(ok)}/{len(ok)} inspection steps PASS ==", flush=True)
    sys.exit(0 if all(ok) else 1)


asyncio.run(main())
