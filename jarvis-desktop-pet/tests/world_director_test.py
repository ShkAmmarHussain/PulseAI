"""Mini World Director: deterministic job state machine (doc 37, tasks 1.5 + 1.6).

Run: .venv/Scripts/python tests/world_director_test.py
exit 0 = pass
"""

import ast
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.bus import TOPIC_ALL, MessageBus  # noqa: E402
from core.world.brain import Brain  # noqa: E402
from core.world.director import Director  # noqa: E402
from core.world.runtime import DEFAULT_ROOMS, AgentRuntime  # noqa: E402
from core.world.state import AgentInfo, WorldState  # noqa: E402

results = []
CAPS = {"max_active_temp": 6, "max_temp_per_job": 3, "max_tasks": 8, "max_new_agents": 3, "task_timeout_s": 5}


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def T(i, role="researcher", needs=(), goal=None):
    return {"id": i, "role": role, "goal": goal or f"goal {i}", "needs": list(needs)}


def doc_plan(tag=""):
    return {
        "intent": "compare",
        "tasks": [T("t1", goal="A" + tag), T("t2", goal="B" + tag), T("t3", "writer", ["t1", "t2"], "table" + tag), T("t4", "operator", ["t3"], "save" + tag)],
        "new_agents": [{"role": "writer", "why": "no writer"}],
    }


class World:
    def __init__(self, plan_fn, fail_on=None, delay=0.05):
        self.bus = MessageBus()
        self.events = []
        self.calls = []
        self.thinker_calls = 0
        self.state = WorldState()
        self.runtime = AgentRuntime(self.state, CAPS)
        for aid, role, room in (("pip", "director", "director"), ("rhea", "researcher", "research"), ("otto", "operator", "ops")):
            self.runtime.register_default(AgentInfo(id=aid, name=aid.title(), role=role, kind="default", room=DEFAULT_ROOMS[room]))
        self.brain = Brain(concurrency=1)
        self.plan_fn, self.fail_on, self.delay = plan_fn, fail_on or set(), delay

        async def thinker(text):
            self.thinker_calls += 1
            await asyncio.sleep(self.delay)
            return self.plan_fn(text)

        def worker(role):
            async def w(task, needed):
                self.calls.append((task.id.split(".")[-1], role, dict(needed)))
                await asyncio.sleep(self.delay)
                if task.id.split(".")[-1] in self.fail_on:
                    raise RuntimeError("worker broke")
                return task.goal
            return w

        async def reporter(text, res):
            await asyncio.sleep(self.delay)
            return "answer: " + ", ".join(res[k] for k in sorted(res))

        self.director = Director(
            self.bus, self.state, self.runtime, self.brain,
            thinker=thinker, workers={r: worker(r) for r in ("researcher", "writer", "operator")},
            reporter=reporter, caps=CAPS,
        )

        async def collect(ev):
            self.events.append(ev)

        self.bus.subscribe(TOPIC_ALL, collect)
        self.bus.start()

    def task(self, job, tid):
        return self.state.tasks[f"{job.id}.{tid}"]

    def temps(self):
        return [a for a in self.state.agents.values() if a.kind == "temp"]


async def main():
    # happy path
    w = World(lambda text: doc_plan())
    job = await w.director.handle("compare two laptops")
    await asyncio.sleep(0.05)
    order = [c[0] for c in w.calls]
    check("happy: job done", job.status == "done", job.status)
    check("happy: valid order", order.index("t3") > max(order.index("t1"), order.index("t2")) and order[-1] == "t4", order)
    t3 = next(c for c in w.calls if c[0] == "t3")
    check("happy: t3 got t1+t2 results", t3[2] == {"t1": "A", "t2": "B"}, t3[2])
    check("happy: temp writer used and dismissed", w.task(job, "t3").agent_id.startswith("temp-writer") and not w.temps())
    chats = [e for e in w.events if e.topic == "ui.chat"]
    check("happy: answer on ui.chat", chats and chats[-1].payload["text"] == "answer: A, B, table, save", [c.payload for c in chats])
    seqs = [e.payload["seq"] for e in w.events if e.topic.startswith("world.")]
    check("happy: world events strictly increasing seq", seqs and all(b > a for a, b in zip(seqs, seqs[1:])), seqs[:5])
    check("happy: world events carry job id", all(e.correlation_id == job.id for e in w.events if e.topic.startswith(("world.job", "world.task"))))

    # invalid plan twice
    w = World(lambda text: {"tasks": [T("t1", "astronaut")]})
    job = await w.director.handle("go to the moon")
    check("invalid: job failed", job.status == "failed")
    check("invalid: answer explains", job.answer.startswith("I could not plan that:"), job.answer)
    check("invalid: thinker called twice", w.thinker_calls == 2, w.thinker_calls)

    # invalid then valid (retry works)
    tries = []
    w = World(lambda text: tries.append(text) or ({"tasks": [T("t1", "astronaut")]} if len(tries) == 1 else {"tasks": [T("t1")]}))
    job = await w.director.handle("retry me")
    check("retry: second plan runs", job.status == "done" and "unknown role: astronaut" in tries[1], tries)

    # failing worker -> dependents skipped, job partial
    w = World(lambda text: doc_plan(), fail_on={"t1"})
    job = await w.director.handle("compare")
    st = {t: w.task(job, t).state for t in ("t1", "t2", "t3", "t4")}
    check("fail: states", st == {"t1": "failed", "t2": "done", "t3": "skipped", "t4": "skipped"}, st)
    check("fail: job partial", job.status == "partial", job.status)
    check("fail: temps dismissed", not w.temps())

    # stop all mid-job
    w = World(lambda text: doc_plan(), delay=0.05)
    run = asyncio.create_task(w.director.handle("compare"))
    await asyncio.sleep(0.12)
    calls_at_stop = len(w.calls)
    await w.director.stop_all()
    job = await run
    await asyncio.sleep(0.2)
    check("stop: job stopped", job.status == "stopped", job.status)
    check("stop: no worker after stop", len(w.calls) == calls_at_stop, (calls_at_stop, w.calls))
    check("stop: no temps left", not w.temps())
    check("stop: brain queue empty", w.brain.waiting() == 0)
    check("stop: nothing left queued/working", all(t.state in ("done", "stopped", "skipped") for t in w.state.tasks.values()), [t.state for t in w.state.tasks.values()])

    # two jobs at once
    w = World(lambda text: doc_plan(tag="-" + text))
    a, b = await asyncio.gather(w.director.handle("x", priority=0), w.director.handle("y", priority=1))
    check("two jobs: both done", a.status == "done" and b.status == "done", (a.status, b.status))
    check("two jobs: answers do not mix", "-y" not in a.answer and "-x" not in b.answer and "-x" in a.answer, (a.answer, b.answer))

    # the Director never touches a model directly
    tree = ast.parse((ROOT / "core/world/director.py").read_text(encoding="utf-8"))
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    check("director imports no LLM module", not any(m and ("llm" in m or "openai" in m) for m in mods), mods)

    # config flag (task 1.6)
    from core.config import load_config
    world = load_config()["config"].get("world") or {}
    check("config: world.enabled is on (sprint 8)", world.get("enabled") is True, world)
    check("config: caps", world.get("caps") == {"max_active_temp": 6, "max_temp_per_job": 3, "max_tasks": 8, "task_timeout_s": 300}, world.get("caps"))
    import core.world as cw
    check("package exports", all(hasattr(cw, n) for n in ("WorldState", "Brain", "AgentRuntime", "Director", "validate_plan")))


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
