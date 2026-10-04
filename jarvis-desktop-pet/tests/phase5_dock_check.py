"""Phase 5c e2e: Top-Edge Dock (spec 29 section 5.1).

Static checks on the dock markup/wiring + a CDP pass that loads
index.html?mode=dock, verifies the island layout, hover expand/retract,
and the dock drop target feeding the composer prefill (section 5.2).

Run with Edge CDP on 9334 (app tabs open) and backend on 8765:
    .venv/Scripts/python tests/phase5_dock_check.py
exit 0 = pass
"""

import asyncio
import json
import os
import sys
import time
import urllib.parse
import urllib.request

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_pet", "src")
CDP = "http://127.0.0.1:9334"
WS = "ws://127.0.0.1:8765/ws"

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def grep(rel, *needles):
    with open(os.path.join(SRC, rel), "r", encoding="utf-8") as f:
        text = f.read()
    return all(n in text for n in needles)


def grep_rs(rel, *needles):
    path = os.path.join(ROOT, "ui_pet", "src-tauri", rel)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return all(n in text for n in needles)


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


async def rpc(ws, method, params=None, rid=[0], timeout=15):
    rid[0] += 1
    i = rid[0]
    await ws.send_json({"id": i, "method": method, "params": params or {}})
    t = time.time() + timeout
    while time.time() < t:
        d = await recv(ws, t - time.time())
        if not d:
            continue
        if d.get("id") == i:
            return d
    return None


async def ev(ws, expr, timeout=20):
    r = await rpc(ws, "Runtime.evaluate",
                  {"expression": expr, "returnByValue": True, "awaitPromise": True},
                  timeout=timeout)
    if r and "result" in r and "result" in r["result"]:
        res = r["result"]["result"]
        if res.get("value") is not None:
            return res.get("value")
        if "exceptionDetails" in r["result"]:
            return {"exc": str(r["result"]["exceptionDetails"])[:300]}
    return None


def http_json(url, method="GET", data=None):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(data).encode() if data else None)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


async def main():
    # ---- 1. static wiring ----
    check("static: dock island markup", grep("index.html", 'id="dock-island"',
          'id="dock-dot"', 'id="dock-status"', 'id="dock-task"',
          'id="dock-mic"', 'id="dock-chat"', 'id="dock-settings"', 'id="dock-toast"'))
    check("static: companion segmented toggle", grep("index.html",
          'id="companion-seg"', 'data-mode="pet"', 'data-mode="dock"'))
    check("static: dock.js loaded by index.html", grep("index.html", 'src="dock.js"'))
    check("static: dock.js hover + earcon + ingest", grep("dock.js",
          "mode=dock", "mouseenter", "mouseleave", "snd_dock_peek",
          "fileIngest", "tauri://file-drop", "jarvis:connected"))
    check("static: dock CSS island + dock-mode + seg", grep("app.css",
          "#dock-island", "body.dock-mode", "#dock-island.expanded", ".seg "))
    check("static: main.js applyCompanion", grep("main.js",
          "applyCompanion", "set_companion"))
    check("static: settings.js companion persist", grep("settings.js",
          "companion-seg", "runtime.companion", "setCompanionSeg"))
    check("static: main.rs set_companion window", grep_rs("src/main.rs",
          "fn set_companion", "WindowBuilder::new", "index.html?mode=dock",
          "position_dock", '"dock"'))

    # ---- 2. open a fresh CDP target and navigate it to the dock page ----
    dock_url = "file:///" + os.path.join(SRC, "index.html").replace("\\", "/") + "?mode=dock"
    info = http_json(CDP + "/json/new", method="PUT")
    dock_id = info.get("id")
    ws_url = info.get("webSocketDebuggerUrl")
    check("cdp: dock target opened", bool(dock_id) and bool(ws_url), info.get("title"))

    async with aiohttp.ClientSession() as s:
        try:
            async with s.ws_connect(ws_url, timeout=30) as ws:
                await rpc(ws, "Runtime.enable")
                await rpc(ws, "Page.enable")
                nav = await rpc(ws, "Page.navigate", {"url": dock_url})
                check("cdp: navigated to ?mode=dock",
                      bool(nav) and "errorText" not in (nav.get("result") or {}),
                      (nav or {}).get("result"))

                # wait for scripts to run
                mode = None
                t = time.time() + 12
                while time.time() < t:
                    mode = await ev(ws, "document.body.classList.contains('dock-mode') ? 1 : 0")
                    if mode == 1:
                        break
                    await asyncio.sleep(0.5)
                check("dock-mode class applied", mode == 1, mode)

                geo = await ev(ws, """(() => {
                    const r = document.getElementById('dock-island').getBoundingClientRect();
                    return {w: Math.round(r.width), h: Math.round(r.height)};
                })()""")
                check("island collapsed 220x38", isinstance(geo, dict) and
                      abs(geo.get("w", 0) - 220) <= 2 and abs(geo.get("h", 0) - 38) <= 2, geo)

                app_disp = await ev(ws, "getComputedStyle(document.getElementById('app')).display")
                check("main app hidden in dock mode", app_disp == "none", app_disp)

                conn = None
                t = time.time() + 6
                while time.time() < t:
                    conn = await ev(ws, "document.getElementById('dock-dot').classList.contains('on') ? 1 : 0")
                    if conn == 1:
                        break
                    await asyncio.sleep(0.5)
                check("status dot connected (green)", conn == 1, conn)

                await ev(ws, "document.getElementById('dock-island').dispatchEvent(new MouseEvent('mouseenter'))")
                await asyncio.sleep(0.7)
                exp = await ev(ws, """(() => {
                    const el = document.getElementById('dock-island');
                    const r = el.getBoundingClientRect();
                    const panel = document.querySelector('.dock-panel');
                    return {expanded: el.classList.contains('expanded'),
                            h: Math.round(r.height),
                            panel: getComputedStyle(panel).display};
                })()""")
                check("hover expands island to 120px pill", isinstance(exp, dict) and
                      exp.get("expanded") is True and exp.get("panel") == "flex" and
                      exp.get("h", 0) >= 110, exp)

                await ev(ws, "document.getElementById('dock-island').dispatchEvent(new MouseEvent('mouseleave'))")
                await asyncio.sleep(0.7)
                col = await ev(ws, """(() => {
                    const el = document.getElementById('dock-island');
                    return {expanded: el.classList.contains('expanded'),
                            h: Math.round(el.getBoundingClientRect().height)};
                })()""")
                check("retract on leave", isinstance(col, dict) and
                      col.get("expanded") is False and col.get("h", 0) <= 46, col)

                # ---- drop target -> toast + composer prefill (section 5.2) ----
                # grab the main window first and clear its composer BEFORE the
                # drop, otherwise the broadcast lands before we wipe the field
                async with s.get(CDP + "/json") as r:
                    ts = await r.json()
                main_t = next((t for t in ts if t["type"] == "page" and t["url"].endswith("index.html")
                               and "mode=dock" not in t["url"]), None)
                check("main window target present", bool(main_t),
                      [t.get("url") for t in ts if t.get("type") == "page"])
                mws = None
                if main_t:
                    mws_cm = s.ws_connect(main_t["webSocketDebuggerUrl"], timeout=30)
                    mws = await mws_cm.__aenter__()
                    await rpc(mws, "Runtime.enable")
                    await ev(mws, "(() => { const i = document.getElementById('chat-input'); i.value = ''; return true; })()")
                try:
                    await ev(ws, """(() => {
                        const island = document.getElementById('dock-island');
                        island.dispatchEvent(new MouseEvent('dragover', {bubbles: true, cancelable: true}));
                        return island.classList.contains('dropping');
                    })()""")
                    await ev(ws, """(() => {
                        const island = document.getElementById('dock-island');
                        const dt = new DataTransfer();
                        dt.items.add(new File(["dock probe"], "zz_dock_probe.txt", {type: "text/plain"}));
                        island.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
                        return true;
                    })()""")
                    await asyncio.sleep(1.0)
                    toast = await ev(ws, "document.getElementById('dock-toast').hidden ? '' : document.getElementById('dock-toast').textContent")
                    check("dock toast 'Inspecting zz_dock_probe.txt'",
                          bool(toast) and "Inspecting zz_dock_probe.txt" in toast, toast)
                    task = await ev(ws, "document.getElementById('dock-task').textContent")
                    check("dock task pill shows inspection", task and "zz_dock_probe.txt" in task, task)

                    # composer prefill lands in the main window (existing tab)
                    prefill = None
                    if mws is not None:
                        t = time.time() + 8
                        while time.time() < t:
                            prefill = await ev(mws, "document.getElementById('chat-input').value")
                            if prefill and "zz_dock_probe.txt" in str(prefill):
                                break
                            await asyncio.sleep(0.5)
                    check("main composer prefilled from dock drop",
                          bool(prefill) and prefill.startswith("Summarize this file")
                          and "zz_dock_probe.txt" in prefill, prefill)
                finally:
                    if mws is not None:
                        await mws_cm.__aexit__(None, None, None)
        finally:
            try:
                http_json(CDP + "/json/close/" + dock_id, method="GET")
            except Exception:
                pass


try:
    asyncio.run(main())
except Exception:
    import traceback
    traceback.print_exc()
    check("test ran without exception", False, "exception")

print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
