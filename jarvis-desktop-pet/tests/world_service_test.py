"""Mini World service + approval bridge on a real MessageBus (doc 37, tasks 3.1-3.2).

Run: .venv/Scripts/python tests/world_service_test.py
exit 0 = pass
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import TOPIC_ALL, MessageBus, create_event  # noqa: E402
from core.world.approvals import ApprovalBridge  # noqa: E402
from core.world.service import WorldService, world_enabled  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra)[:300] if extra != "" else ""))


async def main():
    bus = MessageBus()
    seen = []

    async def collect(ev):
        seen.append(ev)

    bus.subscribe(TOPIC_ALL, collect)

    # --- approval bridge ---
    ab = ApprovalBridge(bus, timeout_s=0.3)
    bus.start()

    async def answer(allow, delay=0.05, dup=False):
        await asyncio.sleep(delay)
        ap = [e for e in seen if e.topic == "ui.approval"][-1]
        await bus.publish(create_event("ui.approval.response", "approval_response", {"allow": allow}, correlation_id=ap.correlation_id))
        if dup:
            await bus.publish(create_event("ui.approval.response", "approval_response", {"allow": not allow}, correlation_id=ap.correlation_id))

    t = asyncio.create_task(answer(True, dup=True))
    ok = await ab.ask({"action": "run_shell", "cmd": "dir"}, 8, "j1")
    await t
    ap = [e for e in seen if e.topic == "ui.approval"][-1]
    check("approval card raised with risk + message", ap.payload["risk"] == 8 and "run_shell" in ap.payload["message"] and ap.correlation_id.startswith("world-"))
    check("allow -> True, duplicate ignored", ok is True and ab.pending() == 0)
    t = asyncio.create_task(answer(False))
    check("deny -> False", await ab.ask({"action": "delete_file"}, 9) is False)
    await t
    await bus.publish(create_event("ui.approval.response", "approval_response", {"allow": True}, correlation_id="someone-else"))
    check("timeout -> False", await ab.ask({"action": "click"}, 7) is False)
    await asyncio.sleep(0.05)
    check("timeout publishes approval_cancelled", any(e.topic == "ui.approval_cancelled" and e.payload.get("reason") == "timeout" for e in seen))
    check("timeout from config", ApprovalBridge.timeout_from({"permissions": {"approvals": {"timeout_ms": 12000}}}) == 12.0 and ApprovalBridge.timeout_from({}) == 45.0)

    # --- flag ---
    check("flag off by default", world_enabled({"config": {"world": {"enabled": False}}}) is False and world_enabled({}) is False)
    check("flag on via config", world_enabled({"config": {"world": {"enabled": True}}}) is True)
    os.environ["PULSEAI_WORLD"] = "1"
    check("flag on via env", world_enabled({}) is True)
    del os.environ["PULSEAI_WORLD"]

    # --- service ---
    executed = []

    async def execute(step):
        executed.append(step)
        if step["action"] == "list_dir":
            return "a.txt\nb.txt"
        if step["action"] == "run_shell":
            return "shell ran"
        return "ok"

    async def chat(messages, tier):
        return '{"final": "x"}'

    async def ans(q, needed):
        return "Paris"

    svc = WorldService(bus, {"config": {"world": {"caps": {"task_timeout_s": 3}}}, "permissions": {"approvals": {"timeout_ms": 5000}}}, chat=chat, execute=execute, answer=ans)
    svc.start()
    seen.clear()
    job = await (await svc.handle_input("list files in .", "c1"))
    await asyncio.sleep(0.1)
    topics = [e.topic for e in seen]
    check("user echo first", seen[0].topic == "ui.chat" and seen[0].payload == {"role": "user", "text": "list files in ."}, seen[0].payload)
    check("job done with result", job.status == "done" and "a.txt" in job.answer, job.answer)
    check("job id = cid", job.id == "c1")
    check("world events published", "world.job.opened" in topics and "world.task.updated" in topics and "world.job.closed" in topics)
    check("voice.say + memory.store", "voice.say" in topics and "memory.store" in topics)

    # risky step through the real approval card
    seen.clear()
    run = await svc.handle_input("run: dir", "c2")
    await asyncio.sleep(0.15)
    ap = [e for e in seen if e.topic == "ui.approval"]
    check("risky step raises a card", len(ap) == 1 and ap[0].payload["action"]["action"] == "run_shell", [e.topic for e in seen])
    await bus.publish(create_event("ui.approval.response", "approval_response", {"allow": True}, correlation_id=ap[0].correlation_id))
    job = await run
    check("approved -> ran", job.status == "done" and job.answer == "shell ran", job.answer)
    seen.clear()
    run = await svc.handle_input("run: dir", "c3")
    await asyncio.sleep(0.15)
    ap = [e for e in seen if e.topic == "ui.approval"]
    await bus.publish(create_event("ui.approval.response", "approval_response", {"allow": False}, correlation_id=ap[0].correlation_id))
    job = await run
    check("denied -> nothing ran, job partial", job.status == "partial" and sum(1 for s in executed if s["action"] == "run_shell") == 1, (job.status, job.answer))
    check("denied task error says denied", svc.world.state.tasks["c3.t1"].error == "denied: run_shell", svc.world.state.tasks["c3.t1"].error)

    # commands from the UI
    seen.clear()
    await bus.publish(create_event("world.cmd.snapshot", "snapshot", {}, correlation_id="s1"))
    await asyncio.sleep(0.1)
    snap = [e for e in seen if e.topic == "world.snapshot"]
    check("snapshot command", snap and len(snap[0].payload["agents"]) == 8 and snap[0].payload["seq"] > 0)
    await bus.publish(create_event("world.cmd.say", "say", {"text": "what is the capital of France"}, correlation_id="c4"))
    await asyncio.sleep(0.2)
    check("say command runs a job", any(e.topic == "ui.chat" and e.payload.get("text") == "Paris" for e in seen))

    seen.clear()
    run = await svc.handle_input("run: dir", "c5")
    await asyncio.sleep(0.15)
    await bus.publish(create_event("world.cmd.stop", "stop", {}, correlation_id="x"))
    job = await run
    await asyncio.sleep(0.1)
    check("stop command stops a job waiting on approval", job.status == "stopped", job.status)
    check("stop reported in chat", any(e.topic == "ui.chat" and "Stopped 1" in str(e.payload.get("text")) for e in seen))
    check("no open jobs left", not svc.world.director._open)
    check("stopped approval card is withdrawn", any(e.topic == "ui.approval_cancelled" and e.payload.get("reason") == "stopped" for e in seen))


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
