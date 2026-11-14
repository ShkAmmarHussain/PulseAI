"""Mini World: create, keep, edit, delete and restore agents (doc 37, sprint 5).

Run: .venv/Scripts/python tests/world_agents_test.py
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
from core.world.runtime import DEFAULT_ROOMS, SPARE_ROOMS  # noqa: E402
from core.world.service import WorldService, slug_role  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra)[:300] if extra != "" else ""))


async def main():
    tmp = Path(tempfile.mkdtemp()) / "world_agents.json"
    bus = MessageBus()
    seen = []

    async def collect(ev):
        seen.append(ev)

    bus.subscribe(TOPIC_ALL, collect)
    prompts = []

    async def chat(messages, tier):
        prompts.append(messages[0]["content"])
        if messages[0]["content"].startswith("You plan work"):
            return json.dumps({"tasks": [{"id": "t1", "role": "translator", "goal": "translate hello", "needs": []}]})
        return json.dumps({"final": "hola"})

    async def execute(step):
        return "ok"

    cfg = {"config": {"world": {"caps": {"task_timeout_s": 3, "max_custom": 2}}}}
    svc = WorldService(bus, cfg, chat=chat, execute=execute, store=AgentStore(tmp))
    svc.start()
    bus.start()
    st = svc.world.state

    async def cmd(**payload):
        await bus.publish(create_event("world.cmd.agent", "agent", payload, correlation_id="c"))
        await asyncio.sleep(0.9)

    def chats():
        return [e.payload["text"] for e in seen if e.topic == "ui.chat" and e.payload.get("role") == "system"]

    # create
    await cmd(op="create", description="Translate my replies into Spanish")
    customs = [a for a in st.agents.values() if a.kind == "custom"]
    check("create: one custom agent", len(customs) == 1, [a.role for a in customs])
    a = customs[0]
    check("create: role from description", a.role == "translator", a.role)
    check("create: name picked", a.name == "Wren", a.name)
    check("create: in a spare room", a.room in SPARE_ROOMS and a.room not in DEFAULT_ROOMS.values())
    check("create: persisted", [r["id"] for r in json.loads(tmp.read_text())["agents"]] == [a.id])
    check("create: Bodie was shown working", any(e.topic == "world.agent.updated" and e.payload["agent"]["id"] == "bodie" and e.payload["agent"]["state"] == "working" for e in seen))
    check("create: told in chat", any("Wren joined" in t for t in chats()), chats())
    await cmd(op="create", description="")
    check("create: empty description refused", any("Tell me what" in t for t in chats()))

    # the new role is offered to the Thinker and gets work with its description
    long = "Please translate the following short greeting into Spanish for me and keep the tone friendly and warm thanks"
    job = await svc.world.director.handle(long)
    check("custom role used in a plan", job.status == "done" and st.tasks[f"{job.id}.t1"].agent_id == a.id, (job.status, job.answer))
    check("thinker saw the custom role", any("translator: (custom agent Wren)" in p for p in prompts))
    check("worker prompt carries the description", any("What you are for: Translate my replies" in p for p in prompts))

    # update
    await cmd(op="update", id=a.id, name="Paloma", description="Spanish translator")
    check("update: renamed + persisted", st.agents[a.id].name == "Paloma" and json.loads(tmp.read_text())["agents"][0]["name"] == "Paloma")
    await cmd(op="update", id="rhea", name="X")
    check("update: defaults refused", st.agents["rhea"].name == "Rhea" and any("default agent" in t for t in chats()))
    await cmd(op="update", id=a.id, look_seed="reroll-1")
    check("update: look seed", st.agents[a.id].look_seed == "reroll-1")

    # caps: max_custom = 2
    await cmd(op="create", description="Write short summaries of long emails")
    await cmd(op="create", description="Design slide outlines")
    check("cap: third custom refused", len([x for x in st.agents.values() if x.kind == "custom"]) == 2 and any("custom agents" in t for t in chats()), chats()[-1])

    # delete defaults refused, delete custom archives
    await cmd(op="delete", id="otto")
    check("delete: default refused", "otto" in st.agents and any("cannot be deleted" in t for t in chats()))
    await cmd(op="delete", id=a.id)
    check("delete: custom removed", a.id not in st.agents)
    data = json.loads(tmp.read_text())
    check("delete: archived, not lost", a.id not in [r["id"] for r in data["agents"]] and a.id in [r["id"] for r in data["archive"]])
    await cmd(op="archived")
    arch = [e for e in seen if e.topic == "world.archived"]
    check("archived list published", arch and arch[-1].payload["agents"][0]["id"] == a.id)
    await cmd(op="restore", id=a.id)
    check("restore: back with its name", a.id in st.agents and st.agents[a.id].name == "Paloma")

    # temp -> keep, temp -> dismiss
    tid = svc.world.runtime.spawn_temp("writer", "jx")
    await cmd(op="delete", id=next(x.id for x in st.agents.values() if x.kind == "custom" and x.id != a.id))
    await cmd(op="keep", id=tid)
    check("keep: temp becomes custom and is saved", st.agents[tid].kind == "custom" and tid in [r["id"] for r in json.loads(tmp.read_text())["agents"]])
    t2 = svc.world.runtime.spawn_temp("coder", "jy")
    await cmd(op="delete", id=t2)
    check("dismiss: temp removed, not archived", t2 not in st.agents and t2 not in [r["id"] for r in json.loads(tmp.read_text())["archive"]])
    await cmd(op="delete", id="nobody")
    check("unknown id handled", any("not in the building" in t for t in chats()))

    # restart: customs come back from disk
    svc2 = WorldService(MessageBus(), cfg, chat=chat, execute=execute, store=AgentStore(tmp))
    back = sorted(x.name for x in svc2.world.state.agents.values() if x.kind == "custom")
    check("restart restores custom agents", back == sorted(x.name for x in st.agents.values() if x.kind == "custom"), back)
    rooms = [x.room for x in svc2.world.state.agents.values()]
    check("restart keeps rooms unique", len(rooms) == len(set(rooms)))

    check("slug_role avoids default roles", slug_role("researcher of fish", st) not in ("researcher",))


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
