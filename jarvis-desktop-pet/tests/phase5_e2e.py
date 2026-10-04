"""Phase 5 e2e: pet file drag-and-drop -> ingestion -> composer prefill
(spec 29 sections 5.1/5.2 roadmap items a+b, acceptance checklist item 6).

Covers: planner routing (vision_file / summarize_file), file_ops.read_text,
ws file_ingest reply + ui.file_ingest broadcast, pet dragover/drop DOM flow,
and the main-window composer prefill.

Run (backend on 8765 + Edge CDP on 9334 with app tabs open):
    .venv/Scripts/python tests/phase5_e2e.py
exit 0 = pass
"""

import asyncio
import json
import os
import sys
import tempfile
import time

import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CDP = "http://127.0.0.1:9334/json"
WS = "ws://127.0.0.1:8765/ws"
TESTFILE = os.path.join(tempfile.gettempdir(), "zz_phase5_test.txt")

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


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


async def main():
    with open(TESTFILE, "w", encoding="utf-8") as f:
        f.write("phase5 ingestion test content - safe to delete\n" * 5)

    # ---- 1. planner routing units (no LLM needed) ----
    from core.bus import create_event
    from agents.planner import PlannerAgent

    class StubBus:
        def __init__(self):
            self.published = []

        async def publish(self, ev):
            self.published.append(ev)

    async def plan(q):
        bus = StubBus()
        p = PlannerAgent(bus)
        await p.handle(create_event("planner.request", "plan", {"query": q}, correlation_id="t"))
        if not bus.published:
            return []
        return (bus.published[0].payload or {}).get("steps", [])

    s = await plan(f'Summarize this file: "{TESTFILE}" - key points, structure, and anything notable.')
    check("planner: summarize prompt -> summarize_file",
          s and s[0]["action"] == "summarize_file" and s[0]["risk"] == 0, s)
    s = await plan(f'Describe this image file: "{os.path.join(tempfile.gettempdir(), "x.png")}"')
    check("planner: image prompt -> vision_file",
          s and s[0]["action"] == "vision_file" and s[0]["risk"] == 0, s)
    s = await plan("summarize what's on my screen")
    check("planner: screen summarize still vision_describe",
          s and s[0]["action"] == "vision_describe", s)

    from skills import file_ops
    txt = file_ops.read_text(TESTFILE)
    check("file_ops.read_text returns content", "phase5 ingestion" in txt, txt[:60])
    txt = file_ops.read_text(os.path.join(tempfile.gettempdir(), "zz_missing_42.txt"))
    check("file_ops.read_text missing file", txt.startswith("File not found"), txt[:60])

    # ---- 2. ws file_ingest reply + ui.file_ingest broadcast ----
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(WS, heartbeat=30) as ws:
            await ws.send_json({"type": "file_ingest",
                                "payload": {"paths": [TESTFILE, "nope.png"]},
                                "correlation_id": "p5-1"})
            reply, bcast = None, None
            t = time.time() + 8
            while time.time() < t and not (reply and bcast):
                d = await recv(ws, t - time.time())
                if not d:
                    continue
                if d.get("type") == "file_ingest":
                    reply = d
                if d.get("topic") == "ui.file_ingest":
                    bcast = d
            items = (reply or {}).get("payload", {}).get("items") or []
            check("file_ingest reply ok", reply and reply["payload"].get("ok") is True, reply)
            check("kinds classified", len(items) == 2 and
                  items[0]["kind"] == "document" and items[0]["exists"] is True and
                  items[1]["kind"] == "image" and items[1]["exists"] is False,
                  items)
            check("ui.file_ingest broadcast", bcast and
                  len(((bcast.get("payload") or {}).get("items") or [])) == 2,
                  (bcast or {}).get("payload"))

            # ---- 3. CDP: pet dragover/drop -> bubble + composer prefill ----
            async with s.get(CDP) as r:
                ts = await r.json()
            main_t = next((t for t in ts if t["type"] == "page" and t["url"].endswith("index.html")), None)
            pet_t = next((t for t in ts if t["type"] == "page" and "pet.html" in t["url"]), None)
            check("cdp targets present", bool(main_t) and bool(pet_t),
                  [t.get("url") for t in ts if t.get("type") == "page"])
            if not (main_t and pet_t):
                return

            async with s.ws_connect(main_t["webSocketDebuggerUrl"], timeout=30) as mws:
                await rpc(mws, "Runtime.enable")
                await rpc(mws, "Page.enable")
                await rpc(mws, "Page.reload")
                await asyncio.sleep(2.5)
                got = await ev(mws, "document.title")
                check("main page reloaded", got == "Jarvis", got)

                async with s.ws_connect(pet_t["webSocketDebuggerUrl"], timeout=30) as pws:
                    await rpc(pws, "Runtime.enable")
                    await rpc(pws, "Page.enable")
                    await rpc(pws, "Page.reload")
                    await asyncio.sleep(2.5)

                    mood = await ev(pws, """(() => {
                        const dt = new DataTransfer();
                        document.dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true}));
                        return document.getElementById('pet').dataset.mood;
                    })()""")
                    check("dragover -> ingesting mood", mood == "ingesting", mood)

                    await ev(pws, """(() => {
                        const dt = new DataTransfer();
                        dt.items.add(new File(["phase5 test content"], "zz_phase5_test.txt", {type: "text/plain"}));
                        document.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
                        return true;
                    })()""")
                    await asyncio.sleep(1.0)
                    bub = await ev(pws, "document.getElementById('bubble').textContent")
                    check("pet bubble 'Inspecting ...'", "Inspecting zz_phase5_test.txt" in str(bub), bub)
                    mood = await ev(pws, "document.getElementById('pet').dataset.mood")
                    check("drop keeps ingesting mood", mood == "ingesting", mood)

                    prefill = None
                    t = time.time() + 8
                    while time.time() < t:
                        prefill = await ev(mws, "document.getElementById('chat-input').value")
                        if prefill and "zz_phase5_test.txt" in str(prefill):
                            break
                        await asyncio.sleep(0.5)
                    check("composer prefilled with summary prompt",
                          bool(prefill) and prefill.startswith("Summarize this file")
                          and "zz_phase5_test.txt" in prefill, prefill)

    if os.path.exists(TESTFILE):
        os.remove(TESTFILE)


try:
    asyncio.run(main())
except Exception as e:
    import traceback
    traceback.print_exc()
    check("test ran without exception", False, repr(e))

print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
