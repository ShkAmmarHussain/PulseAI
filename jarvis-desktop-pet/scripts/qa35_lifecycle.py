"""docs/35 lifecycle + chat-window cases on the INSTALLED build (test_install).

Launches test_install\\JarvisDesktopPet.exe exactly like the shortcut (it spawns
its own jarvis-backend sidecar), then drives it with physical mouse clicks on
real screen coordinates (element rects come from CDP :9335, read-only) and
checks processes, ports and window state with Win32.

Covers: L1/L2 launch, L3/L4 second launch (B3), L5 close button (B1/B2),
C1-style reopen paths (pet click, pet dock Chat, island Workspace, tray-equivalent
second launch), L10 minimize/maximize/restore, close-to-tray off, L6 Quit,
L8 UI crash -> backend exits, L9 backend crash -> offline banner.

Run: .venv/Scripts/python scripts/qa35_lifecycle.py      exit 0 = all pass
Screenshots: artifacts/qa35/<case>.png
"""

import asyncio
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes as wt

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(os.path.dirname(ROOT), "test_install")
EXE = os.path.join(INSTALL, "JarvisDesktopPet.exe")
OUT = os.path.join(ROOT, "artifacts", "qa35")
CDP = "http://127.0.0.1:9335/json"
PS1 = os.path.join(ROOT, "scripts", "inspect_ui.ps1")

u = ctypes.windll.user32
u.SetProcessDPIAware()
results = []


def check(case, ok, extra=""):
    results.append((case, bool(ok), str(extra)))
    print(("PASS " if ok else "FAIL ") + case + (" | " + str(extra) if extra != "" else ""), flush=True)


# ---------------------------------------------------------------- processes
def procs():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-Process JarvisDesktopPet,jarvis-backend -ErrorAction SilentlyContinue | "
                          "ForEach-Object { $_.ProcessName + ':' + $_.Id }"],
                         capture_output=True, text=True).stdout.split()
    ui = [p for p in out if p.startswith("JarvisDesktopPet")]
    be = [p for p in out if p.startswith("jarvis-backend")]
    return ui, be


def port_open(port=8765):
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | Measure-Object).Count" % port],
                         capture_output=True, text=True).stdout.strip()
    return out not in ("", "0")


def wait_for(pred, seconds, step=0.5):
    t = time.time() + seconds
    while time.time() < t:
        if pred():
            return True
        time.sleep(step)
    return pred()


def kill_all():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process JarvisDesktopPet,jarvis-backend -ErrorAction SilentlyContinue | Stop-Process -Force"],
                   capture_output=True)
    wait_for(lambda: procs() == ([], []) and not port_open(), 15)


def launch(extra_args=None):
    env = dict(os.environ)
    env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--remote-debugging-port=9335 --allow-file-access-from-files"
    subprocess.Popen([EXE] + (extra_args or []), cwd=INSTALL, env=env,
                     creationflags=0x00000008)  # DETACHED_PROCESS, like a shortcut launch


# ---------------------------------------------------------------- windows
def find_window(title):
    res = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _l):
        b = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, b, 256)
        if b.value == title:
            res.append(h)
        return True

    u.EnumWindows(cb, 0)
    return res[0] if res else None


def main_state():
    h = find_window("Jarvis")
    if not h:
        return {"exists": False}
    return {"exists": True, "visible": bool(u.IsWindowVisible(h)), "minimized": bool(u.IsIconic(h)),
            "foreground": u.GetForegroundWindow() == h, "zoomed": bool(u.IsZoomed(h))}


def client_origin(h):
    p = wt.POINT(0, 0)
    u.ClientToScreen(h, ctypes.byref(p))
    return p.x, p.y


def click_at(x, y):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.2)


def mouse_away():
    u.SetCursorPos(8, u.GetSystemMetrics(1) - 8)


def screenshot(case, state="main_app_expanded"):
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
                    "-State", state, "-OutputDir", OUT], capture_output=True, text=True, timeout=30)
    names = {"main_app_expanded": "main_app_expanded.png", "pet_idle": "pet_idle.png", "dock_collapsed": "dock_collapsed.png"}
    src = os.path.join(OUT, names.get(state, state + ".png"))
    dst = os.path.join(OUT, case + ".png")
    if os.path.exists(src):
        os.replace(src, dst)
    return dst


# ---------------------------------------------------------------- cdp (read-only rects)
async def targets(s):
    try:
        async with s.get(CDP, timeout=aiohttp.ClientTimeout(total=3)) as r:
            return await r.json()
    except Exception:
        return []


async def page(s, suffix):
    for t in await targets(s):
        url = t.get("url", "")
        if t.get("type") == "page" and (url.endswith(suffix) if suffix != "/" else url.rstrip("/").endswith("tauri.localhost")):
            return t
    return None


async def ev(s, suffix, expr):
    t = await page(s, suffix)
    if not t:
        return None
    async with s.ws_connect(t["webSocketDebuggerUrl"], timeout=10) as ws:
        await ws.send_json({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
        while True:
            m = await asyncio.wait_for(ws.receive(), 10)
            d = json.loads(m.data)
            if d.get("id") == 1:
                return ((d.get("result") or {}).get("result") or {}).get("value")


async def click_el(s, suffix, title, selector):
    """Physical click on the element's centre in the real window."""
    h = find_window(title)
    rect = await ev(s, suffix, "(() => { const e = document.querySelector(%s); if (!e) return null;"
                                " const r = e.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2,"
                                " dpr: devicePixelRatio, w: r.width}; })()" % json.dumps(selector))
    if not h or not rect or not rect.get("w"):
        return False
    ox, oy = client_origin(h)
    click_at(ox + rect["x"] * rect["dpr"], oy + rect["y"] * rect["dpr"])
    return True


async def hover_el(s, suffix, title, selector):
    h = find_window(title)
    rect = await ev(s, suffix, "(() => { const e = document.querySelector(%s); if (!e) return null;"
                                " const r = e.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2, dpr: devicePixelRatio}; })()" % json.dumps(selector))
    if not h or not rect:
        return False
    ox, oy = client_origin(h)
    u.SetCursorPos(int(ox + rect["x"] * rect["dpr"]), int(oy + rect["y"] * rect["dpr"]))
    return True


async def close_main_by_button(s):
    return await click_el(s, "/", "Jarvis", "#win-close")


def reopened(st):
    return st.get("exists") and st.get("visible") and not st.get("minimized")


# ---------------------------------------------------------------- run
async def run():
    kill_all()
    async with aiohttp.ClientSession() as s:
        # L1/L2: launch
        launch()
        up = wait_for(lambda: port_open(), 40)
        ui, be = procs()
        check("L2 launch: one UI, backend sidecar up, :8765 listening",
              up and len(ui) == 1 and len(be) >= 1, (ui, be))
        wait_for(lambda: main_state().get("visible"), 15)
        time.sleep(4)
        # make sure the CDP index target is reachable before driving
        wait_for(lambda: True, 1)
        await ev(s, "/", "document.getElementById('onboarding') && (document.getElementById('onboarding').hidden = true); 1")
        screenshot("L2_launch")

        # L3 (B3): second launch while running
        ui0, be0 = procs()
        launch()
        time.sleep(6)
        ui1, be1 = procs()
        st = main_state()
        check("L3 (B3) second launch: no duplicate UI or backend",
              len(ui1) == 1 and len(be1) == len(be0), (ui0, be0, ui1, be1))
        check("L3 second launch: existing main window shown", reopened(st), st)

        # L5 (B1/B2): titlebar close hides to tray, window survives
        ok = await close_main_by_button(s)
        time.sleep(1.5)
        st = main_state()
        ui, be = procs()
        check("L5 close button hides the main window (not destroyed)",
              ok and st.get("exists") and not st.get("visible"), st)
        check("L5 after close: UI + backend keep running (tray mode)", len(ui) == 1 and port_open(), (ui, be))
        main_target = await page(s, "/")
        check("B2 root cause: main webview still alive after close", main_target is not None)

        # C5: pet click reopens chat
        mouse_away()
        pet = find_window("Jarvis Pet")
        if pet:
            r = wt.RECT()
            u.GetWindowRect(pet, ctypes.byref(r))
            click_at((r.left + r.right) // 2, r.top + (r.bottom - r.top) * 0.72)
            time.sleep(1.5)
        st = main_state()
        tab = await ev(s, "/", "document.querySelector('.nav-item[aria-current]') && document.querySelector('.nav-item[aria-current]').dataset.tab")
        check("C5 (B2) pet click reopens the chat window on Chat", reopened(st) and tab == "chat", (st, tab))
        screenshot("C5_pet_click_reopens")

        # C6: pet hover-dock Chat button after closing again
        await close_main_by_button(s)
        time.sleep(1.2)
        await hover_el(s, "/pet.html", "Jarvis Pet", ".pet-stage, #pet-stage")
        time.sleep(0.8)
        ok = await click_el(s, "/pet.html", "Jarvis Pet", "#dock-btn-chat")
        time.sleep(1.5)
        check("C6 (B2) pet dock Chat button reopens chat", ok and reopened(main_state()), main_state())

        # C7: pet dock Settings button opens Settings
        await close_main_by_button(s)
        time.sleep(1.2)
        await hover_el(s, "/pet.html", "Jarvis Pet", "#pet-stage")
        time.sleep(0.8)
        ok = await click_el(s, "/pet.html", "Jarvis Pet", "#dock-btn-settings")
        time.sleep(1.5)
        tab = await ev(s, "/", "document.querySelector('.nav-item[aria-current]') && document.querySelector('.nav-item[aria-current]').dataset.tab")
        check("C7 pet dock Settings opens Settings", ok and reopened(main_state()) and tab == "settings", (main_state(), tab))

        # L4: closed to tray, launch again -> shows
        await close_main_by_button(s)
        time.sleep(1.2)
        launch()
        time.sleep(5)
        ui, be = procs()
        check("L4 (B3) launch while closed to tray: shows existing window, no duplicate",
              reopened(main_state()) and len(ui) == 1, (main_state(), ui))

        # L10: minimize, then reopen from the pet; maximize/restore
        ok = await click_el(s, "/", "Jarvis", "#win-min")
        time.sleep(1.2)
        check("L10 minimize button minimizes", ok and main_state().get("minimized"), main_state())
        if pet:
            r = wt.RECT()
            u.GetWindowRect(pet, ctypes.byref(r))
            click_at((r.left + r.right) // 2, r.top + (r.bottom - r.top) * 0.72)
            time.sleep(1.5)
        check("C5 (B2) pet click restores a minimized window", reopened(main_state()), main_state())
        ok = await click_el(s, "/", "Jarvis", "#win-max")
        time.sleep(1.2)
        z1 = main_state().get("zoomed")
        await click_el(s, "/", "Jarvis", "#win-max")
        time.sleep(1.2)
        z2 = main_state().get("zoomed")
        check("L10 maximize then restore", ok and z1 and not z2, (z1, z2))

        # C8: island Workspace button (dock mode)
        await ev(s, "/", "window.applyCompanion && window.applyCompanion('dock'); 1")
        time.sleep(2.0)
        await close_main_by_button(s)
        time.sleep(1.2)
        await hover_el(s, "/dock.html", "Jarvis Dynamic Island", "#dynamic-island")
        time.sleep(1.0)
        ok = await click_el(s, "/dock.html", "Jarvis Dynamic Island", "#island-chat-btn")
        time.sleep(1.5)
        check("C8 (B2) island Workspace button reopens chat", ok and reopened(main_state()), main_state())
        mouse_away()
        await ev(s, "/", "window.applyCompanion && window.applyCompanion('pet'); 1")
        time.sleep(1.5)

        # close-to-tray off: close quits everything
        await ev(s, "/", "window.__TAURI__.tauri.invoke('set_close_to_tray', {enabled: false}).then(() => 1)")
        await close_main_by_button(s)
        gone = wait_for(lambda: procs() == ([], []) and not port_open(), 15)
        check("L5b close with 'keep running in tray' off quits UI + backend", gone, procs())

        # L6: Quit (About -> Quit Jarvis, same Rust path as tray Quit)
        launch()
        wait_for(lambda: port_open() and main_state().get("visible"), 40)
        time.sleep(4)
        await ev(s, "/", "window.showTab('settings'); window.showSettingsTab('sec-about'); 1")
        time.sleep(0.8)
        ok = await click_el(s, "/", "Jarvis", "#quit-app")
        gone = wait_for(lambda: procs() == ([], []) and not port_open(), 15)
        check("L6 (B1) Quit ends the UI and every backend process, :8765 freed", ok and gone, procs())

        # L8: UI crash -> backend follows
        launch()
        wait_for(lambda: port_open(), 40)
        time.sleep(3)
        subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process JarvisDesktopPet | Stop-Process -Force"],
                       capture_output=True)
        gone = wait_for(lambda: procs() == ([], []) and not port_open(), 15)
        check("L8 UI killed -> backend exits on its own (no orphan)", gone, procs())

        # L9: backend crash -> offline banner with countdown
        launch()
        wait_for(lambda: port_open() and main_state().get("visible"), 40)
        time.sleep(4)
        await ev(s, "/", "document.getElementById('onboarding') && (document.getElementById('onboarding').hidden = true); window.showTab('chat'); 1")
        subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process jarvis-backend | Stop-Process -Force"],
                       capture_output=True)
        time.sleep(5)
        ban = await ev(s, "/", "JSON.stringify({b: !document.getElementById('offline-banner').hidden, t: document.getElementById('offline-count').textContent})")
        check("L9 backend crash -> offline banner with countdown", ban and '"b":true' in ban, ban)
        screenshot("L9_backend_down")

    kill_all()


try:
    asyncio.run(run())
except Exception:
    import traceback

    traceback.print_exc()
    check("driver ran without exception", False)
    kill_all()

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "lifecycle_results.json"), "w", encoding="utf-8") as f:
    json.dump([{"case": c, "pass": p, "evidence": e} for c, p, e in results], f, indent=2)
print(f"== {sum(p for _, p, _ in results)}/{len(results)} PASS ==")
sys.exit(0 if all(p for _, p, _ in results) else 1)
