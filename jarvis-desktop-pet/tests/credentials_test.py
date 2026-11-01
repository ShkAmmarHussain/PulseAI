"""Credential Manager key store + diagnostics bundle (spec 34 sections 7.5 / 7.6).

Part 1 (offline): write/read/delete a throwaway generic credential, migrate an
inline key out of a config dict, resolve it through llm.get_api_key, Forget
clears it; diagnostics redaction never leaks a key. Every credential this test
writes is deleted again.
Part 2 (backend on :8765): diagnostics.export returns a zip with about.json,
rm_state.json, redacted config and no plaintext key.

Run: .venv/Scripts/python tests/credentials_test.py      exit 0 = pass
"""

import asyncio
import json
import sys
import time
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiohttp  # noqa: E402

from backend import diagnostics  # noqa: E402
from core import credentials, llm  # noqa: E402

WS = "ws://127.0.0.1:8765/ws"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""), flush=True)


FAKE = "sk-test-" + uuid.uuid4().hex


def offline():
    check("credential store available (Windows)", credentials.available())
    name = "test." + uuid.uuid4().hex[:8]
    try:
        check("write credential", credentials.write(name, FAKE))
        check("read it back", credentials.read(name) == FAKE)
        check("unicode round trip", credentials.write(name, "kéy-✓") and credentials.read(name) == "kéy-✓")
    finally:
        credentials.delete(name)
    check("deleted credential reads empty", credentials.read(name) == "")

    # migration of an inline key, using a throwaway provider slot name
    real_ref_for = credentials.ref_for
    real_providers = credentials.PROVIDERS
    slot = "zz" + uuid.uuid4().hex[:6]
    credentials.PROVIDERS = (slot,)
    try:
        cfg = {"llm": {"provider": slot, slot: {"api_key": FAKE}}}
        changed = credentials.store_config_keys(cfg)
        sec = cfg["llm"][slot]
        check("inline key migrated", changed and sec["api_key"] == "" and sec.get("api_key_ref") == real_ref_for(slot), sec)
        check("config holds no plaintext key", FAKE not in json.dumps(cfg))
        check("resolve() reads the key through the ref", credentials.resolve(sec) == FAKE)
        credentials.annotate_saved(cfg)
        check("annotate_saved flags a stored key", cfg["llm"][slot].get("api_key_saved") is True)
        credentials.store_config_keys(cfg)
        check("api_key_saved is never persisted", "api_key_saved" not in cfg["llm"][slot])
        # empty field keeps the stored key
        cfg["llm"][slot]["api_key"] = ""
        credentials.store_config_keys(cfg)
        check("empty field keeps the stored key", credentials.resolve(cfg["llm"][slot]) == FAKE)
        # Forget clears it
        cfg["llm"][slot]["api_key_clear"] = True
        credentials.store_config_keys(cfg)
        check("Forget key removes credential and ref",
              "api_key_ref" not in cfg["llm"][slot] and credentials.read("llm." + slot) == "", cfg["llm"][slot])
    finally:
        credentials.delete("llm." + slot)
        credentials.PROVIDERS = real_providers

    # llm.get_api_key resolves real provider refs
    name = "llm.openai"
    before = credentials.read(name)
    if before:
        check("llm.get_api_key resolves a saved openai key", llm.get_api_key(
            {"config": {"llm": {"openai": {"api_key": "", "api_key_ref": credentials.ref_for("openai")}}}}, "openai") == before)
    else:
        check("llm.get_api_key inline key still wins",
              llm.get_api_key({"config": {"llm": {"openai": {"api_key": FAKE}}}}, "openai") == FAKE)

    red = diagnostics.redact({"llm": {"openai": {"api_key": FAKE, "api_key_ref": "wincred:x"}}, "lm_studio": {"api_key": "dummy", "base_url": "u"}})
    check("diagnostics redact hides key fields", FAKE not in json.dumps(red) and red["lm_studio"]["base_url"] == "u", red)
    scrubbed = diagnostics.scrub_text("calling with " + FAKE + " now")
    check("diagnostics log scrub masks key-shaped strings", FAKE not in scrubbed, scrubbed)


async def online():
    try:
        async with aiohttp.ClientSession() as s, s.ws_connect(WS) as ws:
            await ws.send_json({"type": "diagnostics.export", "payload": {"app_version": "0.0.0-test"}, "correlation_id": "diag-1"})
            reply = None
            t = time.time() + 30
            while time.time() < t:
                m = await asyncio.wait_for(ws.receive(), timeout=30)
                d = json.loads(m.data)
                if d.get("type") == "diagnostics.export":
                    reply = d.get("payload") or {}
                    break
    except Exception as e:
        check("backend reachable for diagnostics.export", False, e)
        return
    check("diagnostics.export ok", bool(reply and reply.get("ok")), reply)
    if not (reply and reply.get("ok")):
        return
    p = Path(reply["path"])
    try:
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            check("bundle has about.json + rm_state.json + config", {"about.json", "rm_state.json", "config/config.yaml"} <= set(names), names)
            about = json.loads(z.read("about.json"))
            check("about.json carries the app version", about.get("app_version") == "0.0.0-test", about)
            blob = b"".join(z.read(n) for n in names)
            check("bundle has no key-shaped secrets", b"sk-ant-" not in blob and b"sk-proj-" not in blob)
    finally:
        p.unlink(missing_ok=True)


offline()
asyncio.run(online())
print(f"== {sum(results)}/{len(results)} PASS ==")
sys.exit(0 if all(results) else 1)
