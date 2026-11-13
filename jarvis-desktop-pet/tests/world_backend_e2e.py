"""Mini World wired into the real backend (doc 37, task 3.4).

Starts backend/main.py twice on a spare port: once with PULSEAI_WORLD=1
(the Director takes the request) and once without (the old pipeline, no
world events). No model is needed: "list files in ." is a rule request.

Run: .venv/Scripts/python tests/world_backend_e2e.py
exit 0 = pass
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
PORT = 8799
WS = f"ws://127.0.0.1:{PORT}/ws"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra)[:300] if extra != "" else ""))


def start_backend(world: bool) -> subprocess.Popen:
    env = dict(os.environ, PULSEAI_WS_PORT=str(PORT))
    env.pop("PULSEAI_WORLD", None)
    if world:
        env["PULSEAI_WORLD"] = "1"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "backend" / "main.py")], cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


async def connect(timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            s = aiohttp.ClientSession()
            ws = await s.ws_connect(WS)
            return s, ws
        except Exception:
            await s.close()
            await asyncio.sleep(1)
    raise RuntimeError("backend did not come up")


async def collect(ws, until, timeout=20):
    got = []
    end = time.time() + timeout
    while time.time() < end:
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=max(0.1, end - time.time()))
        except asyncio.TimeoutError:
            break
        if msg.type != aiohttp.WSMsgType.TEXT:
            continue
        data = json.loads(msg.data)
        got.append(data)
        if until(data, got):
            break
    return got


async def world_on():
    s, ws = await connect()
    try:
        await ws.send_str(json.dumps({"type": "text_input", "payload": {"text": "list files in ."}, "correlation_id": "e2e1"}))
        got = await collect(ws, lambda d, g: any(x.get("topic") == "world.job.closed" for x in g) and any(x.get("topic") == "ui.chat" and x["payload"].get("role") == "assistant" for x in g))
        topics = [d.get("topic") for d in got]
        closed = next((d for d in got if d.get("topic") == "world.job.closed"), None)
        check("world on: job opened", "world.job.opened" in topics, topics[:12])
        check("world on: task events", "world.task.created" in topics and "world.task.updated" in topics)
        check("world on: agent events", "world.agent.updated" in topics)
        check("world on: job closed done", closed and closed["payload"]["job"]["status"] == "done", closed)
        check("world on: correlation id kept", closed and closed.get("correlation_id") == "e2e1")
        check("world on: answer in chat", any(d.get("topic") == "ui.chat" and d["payload"].get("role") == "assistant" for d in got))
        check("world on: old pipeline idle (no tool.result)", "tool.result" not in topics)

        await ws.send_str(json.dumps({"type": "world_snapshot", "payload": {}, "correlation_id": "e2e2"}))
        got = await collect(ws, lambda d, g: d.get("topic") == "world.snapshot", 10)
        snap = next((d for d in got if d.get("topic") == "world.snapshot"), None)
        names = sorted(a["name"] for a in snap["payload"]["agents"].values()) if snap else []
        check("world on: snapshot has the 8 regulars", names == ["Ada", "Bodie", "Otto", "Pip", "Remy", "Rhea", "Thinker", "Vee"], names)
        check("world on: snapshot seq > 0", snap and snap["payload"]["seq"] > 0)

        await ws.send_str(json.dumps({"type": "world_stop", "payload": {}, "correlation_id": "e2e3"}))
        got = await collect(ws, lambda d, g: d.get("topic") == "ui.chat" and "Stopped" in str(d["payload"].get("text")), 10)
        check("world on: stop answered", any("Stopped 0" in str(d.get("payload", {}).get("text")) for d in got))
    finally:
        await ws.close()
        await s.close()


async def world_off():
    s, ws = await connect()
    try:
        await ws.send_str(json.dumps({"type": "text_input", "payload": {"text": "list files in ."}, "correlation_id": "e2e4"}))
        got = await collect(ws, lambda d, g: d.get("topic") == "ui.chat" and d["payload"].get("role") == "assistant", 60)
        topics = [d.get("topic") for d in got]
        check("world off: old pipeline answers", any(d.get("topic") == "ui.chat" and d["payload"].get("role") == "assistant" for d in got), [t for t in topics if t != "ui.mic_level"][:12])
        check("world off: no world events", not any(str(t).startswith("world.") for t in topics))
    finally:
        await ws.close()
        await s.close()


def run(world: bool, fn):
    p = start_backend(world)
    try:
        asyncio.run(fn())
    finally:
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()


run(True, world_on)
run(False, world_off)
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
