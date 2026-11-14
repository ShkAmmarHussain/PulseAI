"""Mini World skills: safety check, sandbox, store, review flow, use by agents (doc 37, sprint 6).

Run: .venv/Scripts/python tests/world_skills_test.py
exit 0 = pass
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import TOPIC_ALL, MessageBus, create_event  # noqa: E402
from core.world.agents_store import AgentStore  # noqa: E402
from core.world.service import WorldService  # noqa: E402
from core.world.skills_lab import SkillStore, check_code, risk_of, run_sandboxed  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra)[:300] if extra != "" else ""))


GOOD = """
import math

def run(radius="1"):
    return f"{math.pi * float(radius) ** 2:.2f}"
"""


async def main():
    # --- static check ---
    check("good code passes", check_code(GOOD, []) == [], check_code(GOOD, []))
    bad = {
        "subprocess": "import subprocess\ndef run():\n    return subprocess.run('dir')",
        "eval": "def run(x=''):\n    return eval(x)",
        "os.system": "import os\ndef run():\n    os.system('del x')\n    return ''",
        "socket": "import socket\ndef run():\n    return ''",
        "dunder escape": "def run():\n    return ().__class__.__bases__[0].__subclasses__()",
        "getattr": "def run():\n    return getattr(__builtins__, 'open')",
        "__import__": "def run():\n    return __import__('os').listdir('.')",
    }
    for label, code in bad.items():
        check(f"refused: {label}", check_code(code, ["files", "network"]) != [], check_code(code, ["files", "network"]))
    check("open() needs files", any("files permission" in e for e in check_code("def run():\n    return open('a').read()", [])))
    check("open() allowed with files", check_code("def run():\n    return open('a').read()", ["files"]) == [])
    check("urllib.request needs network", any("network" in e for e in check_code("import urllib.request\ndef run():\n    return ''", [])))
    check("must define run", any("run(" in e for e in check_code("x = 1", [])))
    check("syntax error reported", check_code("def run(:", [])[0].startswith("syntax error"))
    check("risk levels", (risk_of([]), risk_of(["network"]), risk_of(["files"]), risk_of(["files", "network"])) == (1, 3, 5, 7))

    # --- sandbox ---
    check("sandbox runs the skill", run_sandboxed(GOOD, {"radius": "2"}) == "12.57")
    check("sandbox drops params run() does not take", run_sandboxed(GOOD, {"radius": "2", "result": "x"}) == "12.57")
    try:
        run_sandboxed("import time\ndef run():\n    time.sleep(5)\n    return 'x'", {}, timeout_s=1)
        check("sandbox timeout", False)
    except RuntimeError as e:
        check("sandbox timeout", "timed out" in str(e), str(e))
    try:
        run_sandboxed("def run():\n    raise ValueError('nope')", {})
        check("sandbox error surfaces", False)
    except RuntimeError as e:
        check("sandbox error surfaces", "nope" in str(e), str(e))
    secret_env = run_sandboxed("import os\ndef run():\n    return str(sorted(os.environ))", {})
    check("sandbox gets a minimal environment", "LM_API_TOKEN" not in secret_env and "APPDATA" not in secret_env, secret_env[:120])

    # --- service review flow ---
    tmp = Path(tempfile.mkdtemp())
    bus = MessageBus()
    seen = []

    async def collect(ev):
        seen.append(ev)

    bus.subscribe(TOPIC_ALL, collect)
    draft_reply = {"name": "Circle Area", "description": "Area of a circle", "params": {"radius": "radius"}, "permissions": [], "code": GOOD, "example": {"radius": "1"}}
    worker_turn = [0]

    async def chat(messages, tier):
        sysmsg = messages[0]["content"]
        if sysmsg.startswith("You write one small, safe Python skill"):
            return json.dumps(draft_reply)
        if sysmsg.startswith("You plan work"):
            return json.dumps({"tasks": [{"id": "t1", "role": "researcher", "goal": "area of a circle with radius 3", "needs": []}]})
        worker_turn[0] += 1
        if worker_turn[0] == 1:
            return json.dumps({"action": "skill.circle_area", "radius": "3"})
        return json.dumps({"final": "done: " + messages[-1]["content"]})

    async def execute(step):
        if step["action"].startswith("skill."):
            from core.world.skills_lab import run_sandboxed as rs

            return rs(svc.skills.code(step["action"][6:]), {k: v for k, v in step.items() if k not in ("action", "risk")})
        return "ok"

    svc = WorldService(bus, {"config": {"world": {"caps": {"task_timeout_s": 20}}}}, chat=chat, execute=execute,
                       store=AgentStore(tmp / "a.json"), skills=SkillStore(tmp / "skills"))
    svc.start()
    bus.start()

    async def cmd(**p):
        await bus.publish(create_event("world.cmd.skill", "skill", p, correlation_id="c"))
        await asyncio.sleep(1.5)

    await cmd(op="draft", description="Work out the area of a circle")
    meta = svc.skills.get("circle_area")
    check("draft stored under a clean name", meta and meta["status"] == "draft" and meta["version"] == 1, meta)
    check("draft passed check + test", meta and meta["check"] == [] and meta["test_output"] == "3.14", meta and (meta["check"], meta["test_output"]))
    lists = [e for e in seen if e.topic == "world.skills"]
    check("skills list published with code", lists and lists[-1].payload["skills"][0]["code"].strip().startswith("import math"))
    check("draft is not usable yet", "circle_area" not in svc.skills.enabled())

    long = "What is the area of a circle with a radius of three centimetres, worked out with the circle skill please now"
    job = await svc.world.director.handle(long)
    check("agent cannot use a draft skill", "28.27" not in job.answer, job.answer)

    await cmd(op="enable", name="circle_area")
    check("enabled", svc.skills.get("circle_area")["status"] == "enabled")
    worker_turn[0] = 0
    job = await svc.world.director.handle(long)
    check("agent used the enabled skill in the sandbox", "28.27" in job.answer, job.answer)

    await cmd(op="test", name="circle_area", params={"radius": "10"})
    t = [e for e in seen if e.topic == "world.skill.test"]
    check("manual test run", t and t[-1].payload["output"] == "314.16")

    # a bad draft can never be enabled
    draft_reply.update(name="sneaky", code="import subprocess\ndef run():\n    return subprocess.check_output('whoami')")
    await cmd(op="draft", description="who am i")
    sneaky = svc.skills.get("sneaky")
    check("bad draft kept as draft with problems", sneaky and sneaky["check"] and sneaky["status"] == "draft")
    await cmd(op="enable", name="sneaky")
    check("bad draft cannot be enabled", svc.skills.get("sneaky")["status"] == "draft" and any("cannot be enabled" in str(e.payload.get("text")) for e in seen if e.topic == "ui.chat"))

    # versions + disable + delete
    draft_reply.update(name="circle_area", code=GOOD.replace(":.2f", ":.1f"))
    await cmd(op="draft", description="circle area v2")
    check("redraft makes version 2 as a draft", svc.skills.get("circle_area")["version"] == 2 and svc.skills.get("circle_area")["status"] == "draft")
    check("v1 code kept", ":.2f" in svc.skills.code("circle_area", 1))
    await cmd(op="disable", name="circle_area")
    check("disabled", svc.skills.get("circle_area")["status"] == "disabled" and "circle_area" not in svc.skills.enabled())
    await cmd(op="delete", name="circle_area")
    check("deleted + archived", svc.skills.get("circle_area") is None and any((tmp / "skills" / ".archive").iterdir()))
    await cmd(op="enable", name="nope")
    check("unknown skill handled", any("does not exist" in str(e.payload.get("text")) for e in seen if e.topic == "ui.chat"))


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
