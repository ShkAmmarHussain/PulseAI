"""Shared helpers for the docs/35 QA drivers: launch the INSTALLED build,
physical mouse/keyboard input, Win32 window + process checks, read-only CDP."""

import asyncio
import ctypes
import json
import os
import shutil
import subprocess
import time
from ctypes import wintypes as wt

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(os.path.dirname(ROOT), "test_install")
EXE = os.path.join(INSTALL, "JarvisDesktopPet.exe")
OUT = os.path.join(ROOT, "artifacts", "qa35")
CDP = "http://127.0.0.1:9335/json"
PS1 = os.path.join(ROOT, "scripts", "inspect_ui.ps1")
APPDATA_DIR = os.path.join(os.environ.get("APPDATA", ""), "JarvisDesktopPet")

u = ctypes.windll.user32
u.SetProcessDPIAware()
results = []


def check(case, ok, extra=""):
    results.append((case, bool(ok), str(extra)[:300]))
    print(("PASS " if ok else "FAIL ") + case + (" | " + str(extra)[:300] if extra != "" else ""), flush=True)


def na(case, why):
    results.append((case, None, why))
    print("N/A  " + case + " | " + why, flush=True)


# ---- user data safety: the installed backend uses %APPDATA%\JarvisDesktopPet
def backup_user_data(tag="qa35"):
    dst = os.path.join(os.environ["TEMP"], "jarvis_userdata_" + tag)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    for sub in ("config", "data"):
        src = os.path.join(APPDATA_DIR, sub)
        if os.path.exists(src):
            shutil.copytree(src, os.path.join(dst, sub))
    return dst


def restore_user_data(src):
    for sub in ("config", "data"):
        b = os.path.join(src, sub)
        live = os.path.join(APPDATA_DIR, sub)
        if os.path.exists(b):
            if os.path.exists(live):
                shutil.rmtree(live)
            shutil.copytree(b, live)


# ---- processes
def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout


def procs():
    out = ps("Get-Process JarvisDesktopPet,jarvis-backend -ErrorAction SilentlyContinue | "
             "ForEach-Object { $_.ProcessName + ':' + $_.Id }").split()
    return [p for p in out if p.startswith("JarvisDesktopPet")], [p for p in out if p.startswith("jarvis-backend")]


def port_open(port=8765):
    out = ps("(Get-NetTCPConnection -State Listen -LocalPort %d -ErrorAction SilentlyContinue | Measure-Object).Count" % port).strip()
    return out not in ("", "0")


def wait_for(pred, seconds, step=0.5):
    t = time.time() + seconds
    while time.time() < t:
        try:
            if pred():
                return True
        except Exception:
            pass
        time.sleep(step)
    return pred()


def kill_all():
    ps("Get-Process JarvisDesktopPet,jarvis-backend -ErrorAction SilentlyContinue | Stop-Process -Force")
    wait_for(lambda: procs() == ([], []) and not port_open(), 15)


def launch(extra_args=None):
    env = dict(os.environ)
    env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--remote-debugging-port=9335 --allow-file-access-from-files"
    subprocess.Popen([EXE] + (extra_args or []), cwd=INSTALL, env=env, creationflags=0x00000008)


# ---- windows
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


def visible(title):
    h = find_window(title)
    return bool(h and u.IsWindowVisible(h))


def main_state():
    h = find_window("Jarvis")
    if not h:
        return {"exists": False}
    return {"exists": True, "visible": bool(u.IsWindowVisible(h)), "minimized": bool(u.IsIconic(h)),
            "foreground": u.GetForegroundWindow() == h, "zoomed": bool(u.IsZoomed(h))}


def raise_main():
    h = find_window("Jarvis")
    if h:
        u.ShowWindow(h, 9)
        u.SetWindowPos(h, -1, 0, 0, 0, 0, 0x43)
        u.SetWindowPos(h, -2, 0, 0, 0, 0, 0x43)
        u.SetForegroundWindow(h)
        time.sleep(0.4)


def resize_main(w, h_):
    h = find_window("Jarvis")
    if h:
        u.ShowWindow(h, 9)
        r = wt.RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        u.SetWindowPos(h, 0, r.left, r.top, w, h_, 0x0004 | 0x0040)
        time.sleep(0.8)


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
    time.sleep(0.25)


def mouse_away():
    u.SetCursorPos(8, u.GetSystemMetrics(1) - 8)


# ---- keyboard (SendInput)
class _KI(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _IN(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KI), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def _send(vk=0, scan=0, flags=0):
    i = _IN(type=1)
    i.ki = _KI(vk, scan, flags, 0, None)
    u.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))


def type_text(text):
    for ch in text:
        _send(scan=ord(ch), flags=0x0004)
        _send(scan=ord(ch), flags=0x0004 | 0x0002)
        time.sleep(0.01)
    time.sleep(0.15)


VK = {"enter": 0x0D, "esc": 0x1B, "tab": 0x09, "shift": 0x10, "ctrl": 0x11, "alt": 0x12, "backspace": 0x08,
      "a": 0x41, "j": 0x4A, "d": 0x44, "y": 0x59, "n": 0x4E}


def key(*names):
    for n in names:
        _send(vk=VK[n])
    for n in reversed(names):
        _send(vk=VK[n], flags=0x0002)
    time.sleep(0.25)


# ---- screenshots
def screenshot(case, state="main_app_expanded"):
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1,
                    "-State", state, "-OutputDir", OUT], capture_output=True, text=True, timeout=30)
    src = os.path.join(OUT, state + ".png")
    dst = os.path.join(OUT, case + ".png")
    if os.path.exists(src):
        os.replace(src, dst)
    return dst


# ---- cdp (reads + rects only; actions are physical)
async def page(s, suffix):
    try:
        async with s.get(CDP, timeout=aiohttp.ClientTimeout(total=3)) as r:
            ts = await r.json()
    except Exception:
        return None
    for t in ts:
        url = t.get("url", "")
        if t.get("type") != "page":
            continue
        if suffix == "/" and url.rstrip("/").endswith("tauri.localhost"):
            return t
        if suffix != "/" and url.endswith(suffix):
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
            m = await asyncio.wait_for(ws.receive(), 15)
            d = json.loads(m.data)
            if d.get("id") == 1:
                return ((d.get("result") or {}).get("result") or {}).get("value")


async def rect(s, suffix, selector):
    # like a user: bring the control into view first (sticky bars can cover the edges)
    return await ev(s, suffix, "(() => { const e = document.querySelector(%s); if (!e) return null;"
                               " e.scrollIntoView({block: 'center', inline: 'center'});"
                               " const r = e.getBoundingClientRect(); if (!r.width) return null;"
                               " return {x: r.x + r.width / 2, y: r.y + r.height / 2, dpr: devicePixelRatio}; })()"
                    % json.dumps(selector))


async def click_el(s, suffix, title, selector):
    h = find_window(title)
    r = await rect(s, suffix, selector)
    if not h or not r:
        return False
    ox, oy = client_origin(h)
    click_at(ox + r["x"] * r["dpr"], oy + r["y"] * r["dpr"])
    return True


async def hover_el(s, suffix, title, selector):
    h = find_window(title)
    r = await rect(s, suffix, selector)
    if not h or not r:
        return False
    ox, oy = client_origin(h)
    u.SetCursorPos(int(ox + r["x"] * r["dpr"]), int(oy + r["y"] * r["dpr"]))
    time.sleep(0.4)
    return True


def save_results(name):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump([{"case": c, "pass": p, "evidence": e} for c, p, e in results], f, indent=2)
