"""Mini World agent runtime: caps, run, timeouts, stop, loop guard (doc 37, task 1.4).

Run: .venv/Scripts/python tests/world_runtime_test.py
exit 0 = pass
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.world.runtime import (  # noqa: E402
    DEFAULT_ROOMS,
    SPARE_ROOMS,
    AgentRuntime,
    CapError,
    LoopError,
    LoopGuard,
)
from core.world.state import AgentInfo, TaskInfo, WorldState  # noqa: E402

results = []
CAPS = {"max_active_temp": 6, "max_temp_per_job": 3}


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


async def main():
    st = WorldState()
    rt = AgentRuntime(st, CAPS)
    rt.register_default(AgentInfo(id="rhea", name="Rhea", role="researcher", kind="default", room=DEFAULT_ROOMS["research"]))

    ids = [rt.spawn_temp("writer", "j1") for _ in range(3)]
    check("3 temps for one job", len(set(ids)) == 3 and all(st.agents[i].kind == "temp" for i in ids))
    check("4th temp for same job -> CapError", raises(CapError, lambda: rt.spawn_temp("writer", "j1")))
    rt.spawn_temp("coder", "j2"); rt.spawn_temp("coder", "j2"); rt.spawn_temp("coder", "j3")
    check("7th temp overall -> CapError", raises(CapError, lambda: rt.spawn_temp("coder", "j3")))
    rooms = [a.room for a in st.agents.values() if a.kind == "temp"]
    check("temps get distinct spare rooms", len(set(rooms)) == len(rooms) and all(r in SPARE_ROOMS for r in rooms), rooms)
    check("dismiss default -> ValueError", raises(ValueError, lambda: rt.dismiss("rhea")))
    rt.dismiss(ids[0])
    check("dismiss removes temp", ids[0] not in st.agents)
    check("dismiss frees a cap slot", bool(rt.spawn_temp("writer", "j1")))

    def task(tid):
        st.add_task(TaskInfo(id=tid, job_id="j9", role="researcher", goal="g"))
        return tid

    async def ok(t):
        return "ok"

    async def boom(t):
        raise RuntimeError("boom")

    async def slow(t):
        await asyncio.sleep(2)
        return "late"

    r = await rt.run("rhea", task("a"), ok, timeout_s=1)
    check("run ok -> done", st.tasks["a"].state == "done" and st.tasks["a"].result == "ok" and r == "ok")
    check("agent idle after run", st.agents["rhea"].state == "idle" and st.agents["rhea"].task_id is None)
    check("task records its agent", st.tasks["a"].agent_id == "rhea")
    await rt.run("rhea", task("b"), boom, timeout_s=1)
    check("raise -> failed with error", st.tasks["b"].state == "failed" and st.tasks["b"].error == "boom", st.tasks["b"])
    await rt.run("rhea", task("c"), slow, timeout_s=0.1)
    check("timeout -> failed", st.tasks["c"].state == "failed" and st.tasks["c"].error == "timeout after 0.1s", st.tasks["c"].error)
    check("agent idle after failure", st.agents["rhea"].state == "idle")

    rt.register_default(AgentInfo(id="otto", name="Otto", role="operator", kind="default", room=DEFAULT_ROOMS["ops"]))
    runs = [asyncio.create_task(rt.run("rhea", task("d"), slow, 5)), asyncio.create_task(rt.run("otto", task("e"), slow, 5))]
    await asyncio.sleep(0.05)
    n = rt.stop(all=True)
    await asyncio.gather(*runs)
    check("stop(all) count", n == 2, n)
    check("stopped tasks", st.tasks["d"].state == "stopped" and st.tasks["e"].state == "stopped")
    await asyncio.sleep(2.1)
    check("stopped never turn done", st.tasks["d"].state == "stopped" and st.tasks["e"].result == "")

    g = LoopGuard()
    g.check("x", "web_search", {"q": "a"}); g.check("x", "web_search", {"q": "a"})
    check("3rd identical call -> LoopError", raises(LoopError, lambda: g.check("x", "web_search", {"q": "a"})))
    g2 = LoopGuard()
    g2.check("x", "s", {"q": 1}); g2.check("x", "s", {"q": 1}); g2.check("x", "s", {"q": 2}); g2.check("x", "s", {"q": 1})
    check("different call resets count", raises(LoopError, lambda: g2.check("x", "s", {"q": 1})) is False)

    check("19 spare rooms, unique", len(SPARE_ROOMS) == 19 and len(set(SPARE_ROOMS)) == 19)
    check("8 default rooms, disjoint from spare", len(set(DEFAULT_ROOMS.values())) == 8 and not set(DEFAULT_ROOMS.values()) & set(SPARE_ROOMS))
    check("studio (f2r1c3) is the first spare room", SPARE_ROOMS[0] == "f2r1c3")


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
