"""Phase 5c e2e: standalone top-edge Dynamic Island (doc 30, section 5).

Static checks on dock.html + dock_standalone.js wiring, then a CDP pass that
loads dock.html, verifies collapsed geometry, hover expand/retract, live task
headline, and the drop target feeding file ingest -> main composer prefill.

Run with Edge CDP on 9334 (app tabs open) and backend on 8765:
    .venv/Scripts/python tests/phase5_dock_check.py
exit 0 = pass
"""

import asyncio
import json
import os
import sys
import time
import urllib.request

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_pet", "src")
CDP = "http://127.0.0.1:9334"

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
    check("static: dock.html island markup", grep("dock.html",
          'id="dynamic-island"', 'id="island-dot"', 'id="island-headline"',
          'id="island-diff"', 'id="island-subtext"', 'id="island-progress"',
          'id="island-mic-btn"', 'id="island-chat-btn"', 'id="island-pet-btn"',
          'id="island-dropzone"', 'class="island-rail"', 'class="island-drawer"'))
    check("static: dock.html loads ws.js + dock_standalone.js",
          grep("dock.html", 'src="ws.js"', 'src="dock_standalone.js"'))
    check("static: old dock.js removed",
          (not os.path.exists(os.path.join(SRC, "dock.js")))
          and ('src="dock.js"' not in open(os.path.join(SRC, "index.html"),
                                           encoding="utf-8").read()))
    check("static: index has no dock island",
          "dock-island" not in open(os.path.join(SRC, "index.html"),
                                    encoding="utf-8").read())
    check("static: companion segmented toggle", grep("index.html",
          'id="companion-seg"', 'data-mode="pet"', 'data-mode="dock"'))
    check("static: dock_standalone hover + ingest + companion",
          grep("dock_standalone.js", "mouseenter", "mouseleave", "fileIngest",
               "tauri://file-drop", "jarvis:connected", "set_companion",
               "Jarvis Standing By", "agent.hook.diff", "showDiff"))
    check("static: island CSS expand + drop overlay + seg", grep("app.css",
          "#dynamic-island", "#dynamic-island.expanded", ".island-rail",
          ".island-drop-overlay", "island-blink", ".seg "))
    check("static: main.js applyCompanion", grep("main.js",
          "applyCompanion", "set_companion"))
    check("static: settings.js companion persist", grep("settings.js",
          "companion-seg", "runtime.companion", "setCompanionSeg"))
    check("static: main.rs set_companion dock window", grep_rs("src/main.rs",
          "fn set_companion", 'get_window("dock")', "position_dock",
          "onCompanionChanged", ".show()"))
    check("static: tauri.conf declares dock window", grep_rs("tauri.conf.json",
          '"label": "dock"', "dock.html", '"visible": false',
          '"alwaysOnTop": true', '"transparent": true'))

    # ---- 2. open a fresh CDP target and navigate it to dock.html ----
    dock_url = "file:///" + os.path.join(SRC, "dock.html").replace("\\", "/")
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
                check("cdp: navigated to dock.html",
                      bool(nav) and "errorText" not in (nav.get("result") or {}),
                      (nav or {}).get("result"))

                # wait for scripts
                ready = None
                t = time.time() + 12
                while time.time() < t:
                    ready = await ev(ws, """(() => {
                        const i = document.getElementById('dynamic-island');
                        return (i && window.__DOCK_READY) ? 1 : (i ? 2 : 0);
                    })()""")
                    if ready == 1:
                        break
                    await asyncio.sleep(0.4)
                check("dock.html island rendered + scripts ready", ready == 1, ready)

                cls = await ev(ws, "document.body.className")
                check("body dock-window-body", cls == "dock-window-body", cls)

                geo = await ev(ws, """(() => {
                    const r = document.getElementById('dynamic-island').getBoundingClientRect();
                    return {w: Math.round(r.width), h: Math.round(r.height)};
                })()""")
                check("island collapsed 240x36", isinstance(geo, dict) and
                      abs(geo.get("w", 0) - 240) <= 2 and abs(geo.get("h", 0) - 36) <= 2, geo)

                head = await ev(ws, "document.getElementById('island-headline').textContent")
                check("initial headline", head == "Jarvis Standing By", head)

                # backend link -> green dot + headline kept
                conn = None
                t = time.time() + 6
                while time.time() < t:
                    conn = await ev(ws, "document.getElementById('island-dot').classList.contains('on') ? 1 : 0")
                    if conn == 1:
                        break
                    await asyncio.sleep(0.4)
                check("status dot connected (green)", conn == 1, conn)

                # hover expand
                await ev(ws, "document.getElementById('dynamic-island').dispatchEvent(new MouseEvent('mouseenter'))")
                await asyncio.sleep(0.7)
                exp = await ev(ws, """(() => {
                    const el = document.getElementById('dynamic-island');
                    const r = el.getBoundingClientRect();
                    const drawer = document.querySelector('.island-drawer');
                    return {expanded: el.classList.contains('expanded'),
                            h: Math.round(r.height), w: Math.round(r.width),
                            drawer: getComputedStyle(drawer).display};
                })()""")
                check("hover expands island 460x150 + drawer", isinstance(exp, dict) and
                      exp.get("expanded") is True and exp.get("drawer") == "flex" and
                      exp.get("h", 0) >= 140 and exp.get("w", 0) >= 450, exp)

                # drawer buttons present
                btns = await ev(ws, "document.querySelectorAll('.island-drawer .drawer-btn').length")
                check("drawer has 3 control buttons", btns == 3, btns)

                # retract
                await ev(ws, "document.getElementById('dynamic-island').dispatchEvent(new MouseEvent('mouseleave'))")
                await asyncio.sleep(0.7)
                col = await ev(ws, """(() => {
                    const el = document.getElementById('dynamic-island');
                    return {expanded: el.classList.contains('expanded'),
                            h: Math.round(el.getBoundingClientRect().height)};
                })()""")
                check("retract on leave", isinstance(col, dict) and
                      col.get("expanded") is False and col.get("h", 0) <= 40, col)

                # ---- drop target -> headline + file ingest -> composer prefill ----
                # grab the main window first and clear its composer BEFORE the drop
                async with s.get(CDP + "/json") as r:
                    ts = await r.json()
                main_t = next((t for t in ts if t["type"] == "page" and t["url"].endswith("index.html")
                               and "dock.html" not in t["url"]), None)
                check("main window target present", bool(main_t),
                      [t.get("url") for t in ts if t.get("type") == "page"])
                mws = None
                if main_t:
                    mws_cm = s.ws_connect(main_t["webSocketDebuggerUrl"], timeout=30)
                    mws = await mws_cm.__aenter__()
                    await rpc(mws, "Runtime.enable")
                    await ev(mws, "(() => { const i = document.getElementById('chat-input'); i.value = ''; return true; })()")
                try:
                    over = await ev(ws, """(() => {
                        const island = document.getElementById('dynamic-island');
                        island.dispatchEvent(new MouseEvent('dragover', {bubbles: true, cancelable: true}));
                        const dz = document.getElementById('island-dropzone');
                        return {dropping: island.classList.contains('dropping'),
                                zone: dz.hidden === false};
                    })()""")
                    check("dragover shows drop overlay", isinstance(over, dict) and
                          over.get("dropping") is True and over.get("zone") is True, over)

                    await ev(ws, """(() => {
                        const island = document.getElementById('dynamic-island');
                        const dt = new DataTransfer();
                        dt.items.add(new File(["dock probe"], "zz_dock_probe.txt", {type: "text/plain"}));
                        island.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
                        return true;
                    })()""")
                    await asyncio.sleep(1.0)
                    after = await ev(ws, """(() => {
                        const island = document.getElementById('dynamic-island');
                        const dz = document.getElementById('island-dropzone');
                        return {head: document.getElementById('island-headline').textContent,
                                sub: document.getElementById('island-subtext').textContent,
                                state: island.dataset.state,
                                dropping: island.classList.contains('dropping'),
                                zone: dz.hidden};
                    })()""")
                    check("headline 'Inspecting zz_dock_probe.txt'",
                          isinstance(after, dict) and "Inspecting zz_dock_probe.txt" in (after.get("head") or ""),
                          after and after.get("head"))
                    check("drop resets overlay + busy state",
                          isinstance(after, dict) and after.get("dropping") is False
                          and after.get("zone") is True and after.get("state") == "busy", after)

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

                    reset = await ev(ws, "document.getElementById('island-diff').hidden")
                    check("diff badge hidden by default", reset is True, reset)
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
