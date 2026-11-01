"""Pet performance gate (spec 34 section 7.4), against the REAL app.

- 3D idle renders at ~10 FPS (fpsInterval 100) once the pet settles
- 2D eye loop stops when the eyes stop moving (no idle frames)
- a hidden pet window renders nothing (3D frame counter stays flat)

Needs the backend on :8765 and the app launched with
WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335.
Run: .venv/Scripts/python tests/perf_check.py      exit 0 = pass
"""

import asyncio
import json
import sys
import time

import aiohttp

REAL_CDP = "http://127.0.0.1:9335/json"
WS = "ws://127.0.0.1:8765/ws"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""), flush=True)


async def cdp_eval(ws, expr, rid=[0]):
    rid[0] += 1
    i = rid[0]
    await ws.send_json({"id": i, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
    t = time.time() + 15
    while time.time() < t:
        m = await asyncio.wait_for(ws.receive(), timeout=15)
        if m.type != aiohttp.WSMsgType.TEXT:
            continue
        d = json.loads(m.data)
        if d.get("id") == i:
            return ((d.get("result") or {}).get("result") or {}).get("value")
    return None


async def main():
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(REAL_CDP, timeout=aiohttp.ClientTimeout(total=3)) as r:
                ts = await r.json()
        except Exception as e:
            check("real app CDP :9335 reachable", False, e)
            return
        pet = next((t for t in ts if t.get("type") == "page" and t.get("url", "").endswith("/pet.html")), None)
        check("real pet window target", pet is not None)
        if not pet:
            return
        async with s.ws_connect(WS) as bws, s.ws_connect(pet["webSocketDebuggerUrl"]) as pws:
            await bws.send_json({"type": "set_pet", "payload": {"enabled": True}})
            await asyncio.sleep(2.0)

            # 3D idle budget (the renderer runs in both modes; 2D just hides it)
            has3d = await cdp_eval(pws, "!!(window.Pet3D && window.Pet3D.debug)")
            if has3d:
                await asyncio.sleep(3.0)  # let the idle throttle kick in
                d0 = await cdp_eval(pws, "window.Pet3D.debug()")
                await asyncio.sleep(2.0)
                d1 = await cdp_eval(pws, "window.Pet3D.debug()")
                rate = (d1["renders"] - d0["renders"]) / 2.0
                check("3D idle at ~10 FPS", d1["fpsInterval"] == 100 and rate <= 14, (d1["fpsInterval"], rate))
            else:
                check("Pet3D present", False, "no Pet3D.debug")

            e0 = await cdp_eval(pws, "window.Pet2D && window.Pet2D.debug ? window.Pet2D.debug() : null")
            await asyncio.sleep(1.5)
            e1 = await cdp_eval(pws, "window.Pet2D && window.Pet2D.debug ? window.Pet2D.debug() : null")
            check("2D eye loop idle (no frames while eyes are still)",
                  isinstance(e1, dict) and e1.get("eyeLoop") is False and e1["eyeFrames"] == e0["eyeFrames"],
                  (e0, e1))

            # hide the pet window: rendering stops
            await bws.send_json({"type": "set_pet", "payload": {"enabled": False}})
            await asyncio.sleep(2.0)
            hidden = await cdp_eval(pws, "document.hidden || window.__petHidden === true")
            h0 = await cdp_eval(pws, "window.Pet3D.debug().renders") if has3d else 0
            await asyncio.sleep(3.0)
            h1 = await cdp_eval(pws, "window.Pet3D.debug().renders") if has3d else 0
            check("hidden pet window knows it is hidden", hidden is True, hidden)
            check("hidden pet renders nothing", h1 - h0 <= 1, h1 - h0)

            await bws.send_json({"type": "set_pet", "payload": {"enabled": True}})
            await asyncio.sleep(1.5)


try:
    asyncio.run(main())
except Exception:
    import traceback

    traceback.print_exc()
    check("test ran without exception", False)

print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
