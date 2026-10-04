"""Phase 5d-i e2e: next-gen pet renderer (spec 29 section 5.5 + roadmap 472-477).

Static wiring checks + CDP probes against pet.html verifying:
- superellipse (n=4.2) geometry flags and spherical eye projection
- RK4 poke squash / taffy stretch physics via Pet3D
- ingestion particle stream
- colorway switching
- core-color state machine (eco-sleep ember)
- adaptive 60/10 FPS throttling

Run with Edge CDP on 9334 (pet tab open):
    .venv/Scripts/python tests/phase5_visual_check.py
exit 0 = pass
"""

import asyncio
import json
import os
import sys
import time

import aiohttp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_pet", "src")
CDP = "http://127.0.0.1:9334/json"

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def grep(rel, *needles):
    with open(os.path.join(SRC, rel), "r", encoding="utf-8") as f:
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
            return {"exc": str(r["result"]["exceptionDetails"])[:400]}
    return None


async def main():
    # ---- static ----
    check("static: superellipse geometry + n=4.2", grep("pet3d.js",
          "superellipsoid", "SUPER_N = 4.2", "computeVertexNormals"))
    check("static: dual-pass silicone material", grep("pet3d.js",
          "MeshPhysicalMaterial", "sheen", "innerCore", "AdditiveBlending"))
    check("static: spherical eye projection + saccades", grep("pet3d.js",
          "faceSurf", "faceNormal", "setFromUnitVectors", "sac.x", "Spring(38"))
    check("static: micro-blink 2.5-6s + double blink + half lids", grep("pet3d.js",
          "2.5 + Math.random() * 3.5", "Math.random() < 0.22", "halfLid"))
    check("static: springs + volume conservation wired", grep("pet3d.js",
          "volumeScales", "new Spring(18.5, 0.65, 1)", "Taffy", "poke(", "stretch("))
    check("static: ingestion particles", grep("pet3d.js", "THREE.Points", "ingest.active"))
    check("static: colorways", grep("pet3d.js",
          "COLORWAYS", "obsidian", "porcelain", "cyberpunk", "titanium"))
    check("static: adaptive fps throttle", grep("pet3d.js",
          "renderBudget", "document.hidden", "1000 / 60", "1000 / 10"))
    check("static: spring module import", grep("pet3d.js", "./pet_springs.js"))
    check("static: settings colorway select", grep("index.html", 'id="pet-colorway"',
          'value="titanium"') and grep("settings.js", "pet_colorway"))
    check("static: pet.js poke/stretch/executing wiring", grep("pet.js",
          "Pet3D.poke", "Pet3D.stretch", "agent.hook.session", "applyColorway"))

    # ---- CDP against pet.html ----
    async with aiohttp.ClientSession() as s:
        async with s.get(CDP) as r:
            ts = await r.json()
        pet_t = next((t for t in ts if t["type"] == "page" and "pet.html" in t["url"]), None)
        check("cdp: pet target present", bool(pet_t),
              [t.get("url") for t in ts if t.get("type") == "page"])
        if not pet_t:
            return

        async with s.ws_connect(pet_t["webSocketDebuggerUrl"], timeout=30) as ws:
            await rpc(ws, "Runtime.enable")
            await rpc(ws, "Page.enable")
            await rpc(ws, "Page.reload")

            d = None
            t = time.time() + 15
            while time.time() < t:
                d = await ev(ws, "(window.Pet3D && window.Pet3D.debug) ? window.Pet3D.debug() : null")
                if isinstance(d, dict) and "geometry" in d:
                    break
                await asyncio.sleep(0.5)
            check("Pet3D.debug available", isinstance(d, dict), d)

            if not isinstance(d, dict) or "geometry" not in d:
                return

            check("superellipse geometry flagged", d.get("geometry") == "superellipse"
                  and abs(d.get("n", 0) - 4.2) < 0.01, d.get("geometry"))
            el, er = d.get("eyeL"), d.get("eyeR")
            check("eyes projected onto face surface",
                  isinstance(el, list) and isinstance(er, list)
                  and el[0] < 0 < er[0] and el[2] > 0.9 and er[2] > 0.9
                  and abs(el[1] - er[1]) < 0.05,
                  {"L": el, "R": er})

            # colorway switch
            await ev(ws, "window.Pet3D.applyColorway('porcelain')")
            cw = await ev(ws, "window.Pet3D.debug().colorway")
            check("colorway -> porcelain", cw == "porcelain", cw)
            await ev(ws, "window.Pet3D.applyColorway('obsidian')")
            cw = await ev(ws, "window.Pet3D.debug().colorway")
            check("colorway restored", cw == "obsidian", cw)

            # poke squash impulse -> RK4 rebound (section 5.5.4)
            await ev(ws, "window.Pet3D.setMood('idle')")
            await asyncio.sleep(1.8)
            base = await ev(ws, "window.Pet3D.debug().squash")
            await ev(ws, "window.Pet3D.poke(0.4, 0.6)")
            await asyncio.sleep(0.12)
            mid = await ev(ws, "window.Pet3D.debug().squash")
            check("poke applies squash impulse", isinstance(mid, (int, float)) and
                  isinstance(base, (int, float)) and abs(mid - base) > 0.01,
                  {"base": base, "after": mid})
            await asyncio.sleep(1.8)
            settled = await ev(ws, "window.Pet3D.debug().squash")
            check("squash settles to rest", isinstance(settled, (int, float)) and
                  abs(settled - 1) < 0.01, settled)

            # taffy stretch + snap-back
            await ev(ws, "window.Pet3D.stretch(45, -25)")
            await asyncio.sleep(0.25)
            sty = await ev(ws, "window.Pet3D.debug().taffy")
            check("taffy follows drag velocity", isinstance(sty, list) and
                  max(abs(sty[0]), abs(sty[1])) > 0.01, sty)
            await ev(ws, "window.Pet3D.stretchEnd()")
            await asyncio.sleep(1.8)
            sty2 = await ev(ws, "window.Pet3D.debug().taffy")
            check("taffy snaps back to rest", isinstance(sty2, list) and
                  max(abs(sty2[0]), abs(sty2[1])) < 0.01, sty2)

            # ingestion particles (section 5.5.6)
            await ev(ws, "window.Pet3D.ingestHover([60, 40])")
            await asyncio.sleep(1.0)
            pp = await ev(ws, "window.Pet3D.debug().particles")
            check("particles visible during ingest hover", isinstance(pp, (int, float)) and pp > 0.4, pp)
            await ev(ws, "window.Pet3D.ingestDrop()")
            cf = await ev(ws, "window.Pet3D.debug().coreFlash")
            check("gulp triggers core flash", isinstance(cf, (int, float)) and cf > 0.3, cf)
            await ev(ws, "window.Pet3D.ingestEnd()")
            await asyncio.sleep(1.2)
            pp2 = await ev(ws, "window.Pet3D.debug().particles")
            check("particles retract after drop", isinstance(pp2, (int, float)) and pp2 < 0.1, pp2)

            # eco-sleep core ember (section 5.5.2 / 5.5.5)
            await ev(ws, "window.Pet3D.setMood('sleep')")
            await asyncio.sleep(1.2)
            sl = await ev(ws, "window.Pet3D.debug()")
            check("sleep: amber core + dim glow",
                  isinstance(sl, dict) and sl.get("core") == "#f59e0b"
                  and sl.get("glowMul", 1) < 0.5, sl)
            await ev(ws, "window.Pet3D.setMood('thinking')")
            await asyncio.sleep(1.2)
            th = await ev(ws, "window.Pet3D.debug()")
            check("thinking: violet core",
                  isinstance(th, dict) and th.get("core") == "#a855f7", th)

            # ---- adaptive fps: 10 FPS idle vs 60 FPS active (section 5.5.8) ----
            await ev(ws, "window.Pet3D.setMood('idle')")
            await asyncio.sleep(2.2)                       # let springs/blink settle
            r0 = await ev(ws, "window.Pet3D.debug().renders")
            i0 = await ev(ws, "window.Pet3D.debug().fpsInterval")
            await asyncio.sleep(2.0)
            r1 = await ev(ws, "window.Pet3D.debug().renders")
            idle_rate = (r1 - r0) / 2.0 if isinstance(r0, int) and isinstance(r1, int) else -1
            check("idle throttles to ~10 FPS", i0 == 100 and 4 <= idle_rate <= 25,
                  {"interval": i0, "rate": round(idle_rate, 1)})
            await ev(ws, "window.Pet3D.setMood('thinking')")
            await asyncio.sleep(0.3)
            r2 = await ev(ws, "window.Pet3D.debug().renders")
            i2 = await ev(ws, "window.Pet3D.debug().fpsInterval")
            await asyncio.sleep(1.2)
            r3 = await ev(ws, "window.Pet3D.debug().renders")
            act_rate = (r3 - r2) / 1.2 if isinstance(r2, int) and isinstance(r3, int) else -1
            check("active runs at 60 FPS", i2 in (16, 17) and act_rate >= 35,
                  {"interval": i2, "rate": round(act_rate, 1)})
            await ev(ws, "window.Pet3D.setMood('idle')")


try:
    asyncio.run(main())
except Exception:
    import traceback
    traceback.print_exc()
    check("test ran without exception", False, "exception")

print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
