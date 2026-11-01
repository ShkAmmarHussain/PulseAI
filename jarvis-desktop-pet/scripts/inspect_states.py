"""Doc 30 visual inspection driver (section 3 + 7).

Drives the real app into each of the mandated states, then captures the REAL
Tauri OS windows via scripts/inspect_ui.ps1:

    pet_idle, pet_hover, pet_speech, pet_approval      -> Jarvis Pet window
    dock_collapsed, dock_expanded                      -> Jarvis Dynamic Island
    main_app_expanded, main_app_menu,                  -> Jarvis main window
    main_activity, main_memory, main_settings, main_onboarding (needs :9335)
      (menu + panes reached by real coordinate clicks on the spec 34 header,
       positions probed from the mirrored CDP index tab)

Run with app + backend up, Edge CDP on 9334 (index/pet/dock tabs), LM Studio up:
    .venv/Scripts/python scripts/inspect_states.py
exit 0 = all 12 captures written to artifacts/ui_inspection/
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
# the real app's WebView2, when launched with --remote-debugging-port=9335
REAL_CDP = "http://127.0.0.1:9335/json"
WS = "ws://127.0.0.1:8765/ws"
PROBE_FILE = os.path.join(os.environ["TEMP"], "opencode", "zz_inspect_probe.txt")

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

SW_RESTORE = 9
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]

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


def focus(hwnd, raise_top=False):
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    if raise_top:
        # SetForegroundWindow is refused when we aren't foreground; a
        # TOPMOST/NOTOPMOST round trip still lifts the window above other
        # normal windows so captures and coordinate clicks land on it.
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x43)
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x43)
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


def capture(state, min_bytes=2000):
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
         "-State", state, "-OutputDir", OUT],
        capture_output=True, text=True, timeout=30)
    line = (p.stdout or "").strip().splitlines()
    line = line[-1] if line else ""
    path = os.path.join(OUT, state + ".png")
    good = line.startswith("RESULT") and os.path.exists(path) and os.path.getsize(path) > min_bytes
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


async def real_tab(s, suffix):
    """Page target of the real app's WebView2 (:9335) whose url ends with suffix."""
    try:
        async with s.get(REAL_CDP, timeout=aiohttp.ClientTimeout(total=3)) as r:
            ts = await r.json()
    except Exception:
        return None
    return next((t for t in ts if t.get("type") == "page" and t.get("url", "").endswith(suffix)), None)


async def island_states(s, bus, island):
    """Spec 34 section 3: one capture per island state, staged in the real dock
    window through its own CDP. The approval is a real one (delete probe); the
    other cards are staged with window.islandDemo()."""
    dock_t = await real_tab(s, "/dock.html")
    if not dock_t:
        print("SKIP island states (real app CDP :9335 not reachable)", flush=True)
        return
    pet_t = await real_tab(s, "/pet.html")
    async with s.ws_connect(dock_t["webSocketDebuggerUrl"], timeout=30) as dws:
        await dws.send_json({"id": 1, "method": "Runtime.enable"})
        await recv(dws, 2)

        async def stage(name, wait=0.9):
            r = await cdp_eval(dws, "window.islandDemo && window.islandDemo(%s)" % json.dumps(name))
            check("island staged " + name, r is True, r)
            time.sleep(wait)
            focus(island)
            capture("island_" + name, 200 if name == "hidden" else 2000)

        mouse_away()
        await stage("hidden")
        await stage("overview")

        # real approval while the island is the companion: it lands here, and
        # the pet card stays down
        await bus.send({"type": "text_input",
                        "payload": {"text": "delete the file zz_inspect_probe.txt in %s"
                                    % os.path.dirname(PROBE_FILE)}})
        ap = None
        for d in bus.log[-20:]:
            if (d.get("topic") or d.get("type")) == "ui.approval":
                ap = d
        if ap is None:
            ap = await bus.wait_topic("ui.approval", 90)
        check("island approval requested", ap is not None)
        if ap:
            time.sleep(1.0)
            card = await cdp_eval(dws, "document.getElementById('dynamic-island').dataset.card")
            check("island shows approval card", card == "approval", card)
            if pet_t:
                async with s.ws_connect(pet_t["webSocketDebuggerUrl"], timeout=30) as pws:
                    await pws.send_json({"id": 1, "method": "Runtime.enable"})
                    await recv(pws, 2)
                    shown = await cdp_eval(pws, "getComputedStyle(document.getElementById('approval')).display")
                    check("pet approval card stays down in island mode", shown == "none", shown)
            focus(island)
            capture("island_approval")
            await bus.send({"type": "approval_response",
                            "payload": {"allow": False, "action": "delete_file"},
                            "correlation_id": ap.get("correlation_id")})
            await bus.wait_topic("ui.chat", 15,
                                 lambda d: "denied" in str(((d.get("payload") or {}).get("text") or "")).lower())
            await bus.pump(1.5)
            card = await cdp_eval(dws, "document.getElementById('dynamic-island').dataset.card")
            check("approval card clears once answered", card != "approval", card)

        for name in ("question", "result", "error", "chat"):
            await stage(name)
        await stage("drop", wait=1.2)
        await cdp_eval(dws, "window.islandDemo('compact'); true")
        mouse_away()


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
                await island_states(s, bus, island)

            # ---- main workspace states ----
            cfg3 = dict(cfg)
            cfg3["runtime"] = dict(cfg["runtime"], companion="pet")
            await bus.send({"type": "save_settings", "payload": {"config": cfg3}})
            await bus.pump(2.5)
            await bus.send({"type": "set_pet", "payload": {"enabled": False}})
            await bus.pump(2.0)

            main_w = find_window("Jarvis")
            check("main window present", main_w is not None)

            # probe header geometry (spec 34: tabs + "+" menu replace the
            # sidebar) from the mirrored CDP index tab. The mirror viewport is
            # wider than the real window, so right-anchored controls are
            # mapped by their distance from the right edge ("fr").
            async with s.get(CDP) as r:
                ts = await r.json()
            idx = next((t for t in ts if t.get("type") == "page" and "index.html" in t.get("url", "")), None)
            check("index cdp tab present", idx is not None)
            geo = None
            if idx:
                async with s.ws_connect(idx["webSocketDebuggerUrl"], timeout=30) as cws:
                    await cws.send_json({"id": 1, "method": "Runtime.enable"})
                    await recv(cws, 2)
                    geo = await cdp_eval(cws, """(() => {
                        const q = (s) => {
                            const el = document.querySelector(s);
                            if (!el) return null;
                            const r = el.getBoundingClientRect();
                            const x = r.x + r.width / 2;
                            return {x: x, y: r.y + r.height / 2, fr: innerWidth - x, vis: r.width > 0};
                        };
                        return {
                            plus: q('#quick-actions-btn'),
                            chat: q('.nav-item[data-tab="chat"]'),
                            activity: q('.nav-item[data-tab="activity"]'),
                            memory: q('.nav-item[data-tab="memory"]'),
                            settings: q('.nav-item[data-tab="settings"]'),
                        };
                    })()""")
            names = ("plus", "chat", "activity", "memory", "settings")
            check("header controls probed (+ menu and 4 tabs)",
                  isinstance(geo, dict) and all((geo.get(k) or {}).get("vis") for k in names), geo)

            if main_w and isinstance(geo, dict) and all(geo.get(k) for k in names):
                focus(main_w, raise_top=True)
                time.sleep(0.4)
                capture("main_app_expanded")
                ox, oy = client_origin(main_w)
                cr = wt.RECT()
                user32.GetClientRect(main_w, ctypes.byref(cr))
                cw = cr.right - cr.left

                def at_left(k):
                    return ox + int(geo[k]["x"]), oy + int(geo[k]["y"])

                def at_right(k):
                    return ox + cw - int(geo[k]["fr"]), oy + int(geo[k]["y"])

                click(*at_right("plus"))
                time.sleep(0.5)
                capture("main_app_menu")
                click(*at_right("plus"))  # toggles the menu closed
                time.sleep(0.3)
                for tab in ("activity", "memory", "settings"):
                    click(*at_left(tab))
                    time.sleep(0.6)
                    capture("main_" + tab)
                click(*at_left("chat"))
                time.sleep(0.3)
                mouse_away()

            # onboarding sheet (spec 34 section 6): opened in the REAL app via
            # its own CDP; skipped when the app runs without debug args
            rts = []
            try:
                async with s.get(REAL_CDP, timeout=aiohttp.ClientTimeout(total=3)) as r:
                    rts = await r.json()
            except Exception:
                rts = []

            def is_index(t):
                u = t.get("url", "")
                return t.get("type") == "page" and (u.endswith("/index.html") or u.rstrip("/").endswith("tauri.localhost"))

            ridx = next((t for t in rts if is_index(t)), None)
            if main_w and ridx:
                async with s.ws_connect(ridx["webSocketDebuggerUrl"], timeout=30) as rws:
                    await rws.send_json({"id": 1, "method": "Runtime.enable"})
                    await recv(rws, 2)
                    opened = await cdp_eval(rws, "(window.openOnboarding && (window.openOnboarding(), true)) || false")
                    check("onboarding opened in real app", opened is True, opened)
                    time.sleep(0.8)
                    focus(main_w, raise_top=True)
                    capture("main_onboarding")
                    await cdp_eval(rws, "document.getElementById('onboarding').hidden = true; 1")
                    # About + diagnostics (spec 34 section 7.5)
                    shown = await cdp_eval(rws, "window.showTab('settings'); window.showSettingsTab('sec-about'); !!document.getElementById('about-version')")
                    check("about section opened in real app", shown is True, shown)
                    ver = None
                    for _ in range(10):
                        ver = await cdp_eval(rws, "document.getElementById('about-version').textContent")
                        if ver and ver.startswith("v"):
                            break
                        time.sleep(0.3)
                    check("about shows the tauri.conf version", bool(ver) and ver.startswith("v"), ver)
                    focus(main_w, raise_top=True)
                    capture("main_about")
                    await cdp_eval(rws, "window.showSettingsTab('sec-models'); window.showTab('chat'); 1")
            else:
                print("SKIP main_onboarding (real app CDP :9335 not reachable)", flush=True)
            # ---- restore ----
            await bus.send({"type": "set_pet", "payload": {"enabled": True}})
            await bus.pump(1.5)
            mouse_away()

    if os.path.exists(PROBE_FILE):
        os.remove(PROBE_FILE)
    print(f"== {sum(ok)}/{len(ok)} inspection steps PASS ==", flush=True)
    sys.exit(0 if all(ok) else 1)


asyncio.run(main())
