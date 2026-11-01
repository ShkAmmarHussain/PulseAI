"""Memory inline edit (spec 34 section 4): store-level update_fact + WS memory.update.

Part 1 runs offline against a temp memory file. Part 2 needs the backend on
:8765 and round-trips add -> update -> delete over the WS (the fact it makes
is removed again).

Run: .venv/Scripts/python tests/memory_update_test.py
exit 0 = pass
"""

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiohttp  # noqa: E402

from core import memory_store as store  # noqa: E402

WS = "ws://127.0.0.1:8765/ws"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""), flush=True)


def offline():
    real_file, real_dir = store.MEMORY_FILE, store.DATA_DIR
    with tempfile.TemporaryDirectory() as td:
        store.DATA_DIR = Path(td)
        store.MEMORY_FILE = Path(td) / "memory.json"
        try:
            f = store.add_fact("my editor is vim", "preferences")
            u = store.update_fact(f["id"], content="my editor is VS Code")
            check("update returns the edited fact", u and u["content"] == "my editor is VS Code", u)
            check("id and created_at kept", u["id"] == f["id"] and u["created_at"] == f["created_at"])
            check("updated_at stamped", bool(u.get("updated_at")))
            saved = json.loads(store.MEMORY_FILE.read_text(encoding="utf-8"))["facts"][0]
            check("edit persisted to disk", saved["content"] == "my editor is VS Code", saved)
            c = store.update_fact(f["id"], category="workflows")
            check("category change applied", c["category"] == "workflows", c)
            bad = store.update_fact(f["id"], category="nonsense")
            check("unknown category ignored", bad["category"] == "workflows", bad)
            check("unknown id returns None", store.update_fact("mem_nope") is None)
            try:
                store.update_fact(f["id"], content="   ")
                check("empty content rejected", False)
            except ValueError:
                check("empty content rejected", True)
            check("content unchanged after rejected edit",
                  store.list_facts()[0]["content"] == "my editor is VS Code")
        finally:
            store.MEMORY_FILE, store.DATA_DIR = real_file, real_dir


async def recv_type(ws, typ, timeout=8):
    t = time.time() + timeout
    while time.time() < t:
        try:
            m = await asyncio.wait_for(ws.receive(), timeout=max(0.1, t - time.time()))
        except asyncio.TimeoutError:
            break
        if m.type != aiohttp.WSMsgType.TEXT:
            continue
        d = json.loads(m.data)
        if d.get("type") == typ:
            return d
    return None


async def online():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(WS, timeout=5) as ws:
                text = "zz memory update probe %d" % int(time.time())
                await ws.send_json({"type": "memory.add", "payload": {"content": text, "category": "facts"}})
                add = await recv_type(ws, "memory.add")
                fid = (((add or {}).get("payload") or {}).get("fact") or {}).get("id")
                check("ws: probe fact added", bool(fid), add and add.get("payload", {}).get("ok"))
                if not fid:
                    return
                await ws.send_json({"type": "memory.update", "payload": {"id": fid, "content": text + " edited"}})
                up = await recv_type(ws, "memory.update")
                p = (up or {}).get("payload") or {}
                check("ws: memory.update ok", p.get("ok") is True, p.get("error"))
                facts = p.get("facts") or []
                hit = next((f for f in facts if f.get("id") == fid), None)
                check("ws: full state carries the edit", hit and hit.get("content") == text + " edited", hit)
                await ws.send_json({"type": "memory.update", "payload": {"id": "mem_missing"}})
                miss = await recv_type(ws, "memory.update")
                check("ws: unknown id -> ok false", ((miss or {}).get("payload") or {}).get("ok") is False)
                await ws.send_json({"type": "memory.delete", "payload": {"id": fid}})
                dl = await recv_type(ws, "memory.delete")
                check("ws: probe fact cleaned up", ((dl or {}).get("payload") or {}).get("ok") is True)
    except Exception as e:
        check("ws: backend reachable on :8765", False, e)


offline()
asyncio.run(online())
print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
