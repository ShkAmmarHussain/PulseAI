"""Mini World end to end with fakes: build_world + Director + Thinker + workers (doc 37, task 2.4).

Run: .venv/Scripts/python tests/world_team_test.py
exit 0 = pass
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.bus import TOPIC_ALL, MessageBus  # noqa: E402
from core.world.runtime import DEFAULT_ROOMS  # noqa: E402
from core.world.team import build_world  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


class Chat:
    """Scripted model: plans for the Thinker, finals for workers, a summary for the Reporter."""

    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    async def __call__(self, messages, tier):
        system = messages[0]["content"]
        self.calls.append((tier, system[:40]))
        if system.startswith("You plan work"):
            return json.dumps(self.plan)
        if system.startswith("Write the reply"):
            return "Compared both laptops and saved the table."
        if "writer agent" in system:
            return json.dumps({"final": "| laptop | ram |"})
        return json.dumps({"final": "worker result"})


async def main():
    bus = MessageBus()
    events = []

    async def collect(ev):
        events.append(ev)

    bus.subscribe(TOPIC_ALL, collect)
    bus.start()
    executed, approvals = [], []

    async def execute(step):
        executed.append(step["action"])
        return "Web results: pulse oximeters measure SpO2" if step["action"] == "web_search" else f"done {step['action']}"

    async def approve(step, risk):
        approvals.append((step["action"], risk))
        return True

    async def answer(q, needed):
        return f"Paris ({q})"

    plan = {
        "intent": "compare",
        "tasks": [
            {"id": "t1", "role": "researcher", "goal": "specs A", "needs": []},
            {"id": "t2", "role": "writer", "goal": "table", "needs": ["t1"]},
            {"id": "t3", "role": "operator", "goal": "save", "needs": ["t2"]},
        ],
        "new_agents": [{"role": "writer", "why": "tables"}],
    }
    chat = Chat(plan)
    cfg = {"config": {"world": {"brain_concurrency": 1, "caps": {"task_timeout_s": 5}}}}
    w = build_world(cfg, bus, chat=chat, execute=execute, approve=approve, answer=answer)

    team = {a.id: a for a in w.state.agents.values()}
    check("8 default agents", len(team) == 8 and set(team) == {"pip", "thinker", "bodie", "rhea", "otto", "vee", "ada", "remy"})
    check("default rooms", team["pip"].room == DEFAULT_ROOMS["director"] and team["remy"].room == DEFAULT_ROOMS["lobby"])
    check("caps merged", w.director.timeout_s == 5 and w.runtime.max_active_temp == 6)

    job = await w.director.handle("search the web for pulse oximeters")
    check("rule job: done", job.status == "done", job.status)
    check("rule job: answer is the search result", job.answer.startswith("Web results"), job.answer)
    check("rule job: zero model calls", chat.calls == [], chat.calls)
    check("rule job: ran by Rhea", w.state.tasks[f"{job.id}.t1"].agent_id == "rhea")

    job = await w.director.handle("what is the capital of France")
    check("question: archivist answers, no model call in the world layer", job.answer == "Paris (what is the capital of France)" and chat.calls == [], job.answer)

    job = await w.director.handle("open notepad")
    check("open notepad: operator ran launch_app", job.status == "done" and executed[-1] == "launch_app" and approvals == [])

    long = "Find the specs of the X1 Carbon laptop, write a comparison table and then save it into my documents folder please"
    job = await w.director.handle(long)
    st = {t: w.state.tasks[f"{job.id}.{t}"].state for t in ("t1", "t2", "t3")}
    check("complex: all tasks done", st == {"t1": "done", "t2": "done", "t3": "done"}, (st, [w.state.tasks[f"{job.id}.{t}"].error for t in st]))
    check("complex: writer was a temp agent", w.state.tasks[f"{job.id}.t2"].agent_id.startswith("temp-writer"))
    check("complex: temp dismissed", not [a for a in w.state.agents.values() if a.kind == "temp"])
    check("complex: reporter summary", job.answer == "Compared both laptops and saved the table.", job.answer)
    tiers = [c[0] for c in chat.calls]
    check("complex: tiers heavy plan, heavy temp, fast report", tiers[0] == "heavy" and "fast" in tiers and tiers.count("heavy") >= 2, tiers)
    await asyncio.sleep(0.05)
    shown = [e.payload["agent"]["id"] for e in events if e.topic == "world.agent.updated" and e.payload["agent"]["state"] == "working"]
    check("thinker, reporter and pip are shown working", {"thinker", "remy", "pip"} <= set(shown), set(shown))
    check("all idle after the job", all(a.state == "idle" for a in w.state.agents.values()))
    check("events reached the bus", any(e.topic == "world.job.closed" for e in events) and any(e.topic == "ui.chat" for e in events))

    # a bad plan from the model fails visibly after one retry
    chat.plan = {"tasks": [{"id": "t1", "role": "reporter", "goal": "x", "needs": ["t9"]}]}
    job = await w.director.handle(long)
    check("bad plan: failed with reason", job.status == "failed" and job.answer.startswith("I could not plan that"), job.answer)


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
