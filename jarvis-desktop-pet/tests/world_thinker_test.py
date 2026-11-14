"""Mini World Thinker, workers, Reporter (doc 37, tasks 2.1-2.4 unit level).

Run: .venv/Scripts/python tests/world_thinker_test.py
exit 0 = pass
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.planner import plan_steps  # noqa: E402
from agents.tool_control import execute_step  # noqa: E402
from core.world.reporter import make_reporter  # noqa: E402
from core.world.roles import ROLE_ACTIONS, WORKING_ROLES  # noqa: E402
from core.world.runtime import LoopError  # noqa: E402
from core.world.state import TaskInfo  # noqa: E402
from core.world.thinker import make_thinker, parse_json  # noqa: E402
from core.world.worker import make_worker  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


class FakeChat:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, messages, tier):
        self.calls.append((messages, tier))
        r = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return r


async def expect(exc, coro, msg=None):
    try:
        await coro
    except exc as e:
        return msg is None or str(e) == msg
    return False


async def main():
    # 2.1 shared helpers
    check("plan_steps rule", plan_steps("open notepad") == [{"action": "launch_app", "target": "notepad", "risk": 2}])
    check("plan_steps no rule", plan_steps("what is the capital of France") is None)
    check("execute_step respond", await execute_step({}, None, {"action": "respond", "text": "hi"}) == "hi")

    # 2.2 thinker
    roles = {r: ROLE_ACTIONS[r] for r in WORKING_ROLES}
    plan_json = {"intent": "x", "tasks": [{"id": "t1", "role": "researcher", "goal": "g", "needs": []}], "new_agents": []}
    chat = FakeChat(["```json\n" + json.dumps(plan_json) + "\n```"])
    think = make_thinker({}, chat=chat, roles=roles)
    p = await think("open notepad")
    check("rule -> operator task with steps, no model", p["tasks"][0]["role"] == "operator" and p["tasks"][0]["steps"][0]["action"] == "launch_app" and not chat.calls, p)
    p = await think("search the web for pulse oximeters")
    check("search rule -> researcher", p["tasks"][0]["role"] == "researcher" and not chat.calls)
    p = await think("what is the capital of France")
    check("plain question -> archivist, no model", p["tasks"][0]["role"] == "archivist" and "steps" not in p["tasks"][0] and not chat.calls, p)
    long = "Find the specs of the X1 Carbon and the XPS 14 laptops, compare them in a table and save it to my documents folder"
    p = await think(long)
    check("complex -> one heavy model call", len(chat.calls) == 1 and chat.calls[0][1] == "heavy")
    check("complex -> fenced JSON parsed", p == plan_json, p)
    check("system prompt lists roles", "researcher: can web_search" in chat.calls[0][0][0]["content"])
    chat2 = FakeChat(["Sure! Here is the plan: " + json.dumps(plan_json) + " Hope it helps."])
    check("JSON inside prose", await make_thinker({}, chat=chat2, roles=roles)(long) == plan_json)
    chat3 = FakeChat(["I cannot do that."])
    check("garbage -> {}", await make_thinker({}, chat=chat3, roles=roles)(long) == {})
    chat4 = FakeChat([json.dumps(plan_json)])
    await make_thinker({}, chat=chat4, roles=roles)("open notepad\n\nYour last plan was invalid: unknown role: x")
    check("retry always asks the model", len(chat4.calls) == 1)
    check("parse_json nested", parse_json('x {"a": {"b": 1}} y') == {"a": {"b": 1}})

    # 2.3 workers
    executed = []

    async def execute(step):
        executed.append(step)
        return f"ran {step['action']}"

    def T(goal="g", steps=None):
        return TaskInfo(id="j.t1", job_id="j", role="r", goal=goal, params={"steps": steps} if steps else {})

    w = make_worker("researcher", {}, chat=FakeChat(["x"]), execute=execute, approve=None, allowed=ROLE_ACTIONS["researcher"])
    check("steps run directly", await w(T(steps=[{"action": "web_search", "query": "q", "risk": 0}]), {}) == "ran web_search")
    check("action outside allow-list refused", await expect(PermissionError, w(T(steps=[{"action": "run_shell", "cmd": "dir"}]), {}), "not allowed for researcher: run_shell"))

    asked = []

    async def deny(step, risk):
        asked.append(risk)
        return False

    async def allow(step, risk):
        asked.append(risk)
        return True

    shell = [{"action": "run_shell", "cmd": "dir", "risk": 8}]
    op = lambda appr, cfg=None: make_worker("operator", cfg or {}, chat=FakeChat(["x"]), execute=execute, approve=appr, allowed=ROLE_ACTIONS["operator"])
    check("risky step denied", await expect(PermissionError, op(deny)(T(steps=shell), {}), "denied: run_shell") and asked == [8], asked)
    check("risky step approved runs", await op(allow)(T(steps=shell), {}) == "ran run_shell")
    check("no approver -> denied", await expect(PermissionError, op(None)(T(steps=shell), {}), "denied: run_shell"))
    n = len(asked)
    check("autonomous policy skips approval", await op(deny, {"permissions": {"default_policy": "autonomous"}})(T(steps=shell), {}) == "ran run_shell" and len(asked) == n)
    check("low risk needs no approval", await op(None)(T(steps=[{"action": "launch_app", "target": "notepad"}]), {}) == "ran launch_app")

    loop_chat = FakeChat(['{"action": "web_search", "query": "a"}', '{"final": "the specs"}'])
    w = make_worker("researcher", {}, chat=loop_chat, execute=execute, approve=None, allowed=ROLE_ACTIONS["researcher"])
    out = await w(T(goal="find specs"), {"t0": "earlier notes"})
    check("model loop: action then final", out == "the specs" and executed[-1]["action"] == "web_search", out)
    first_user = loop_chat.calls[0][0][1]["content"]
    check("needed results in prompt", "earlier notes" in first_user and "find specs" in first_user, first_user)
    check("tool result fed back", "ran web_search" in loop_chat.calls[1][0][-1]["content"])
    wc = FakeChat(['{"action": "web_search", "query": "x"}', '{"final": "summary from notes"}'])
    w = make_worker("writer", {}, chat=wc, execute=execute, approve=None, allowed=[])
    check("disallowed ask is refused once, then the model finishes", await w(T(), {"t1": "notes"}) == "summary from notes" and "cannot use web_search" in wc.calls[1][0][-1]["content"])
    w = make_worker("writer", {}, chat=FakeChat(['{"action": "web_search", "query": "x"}']), execute=execute, approve=None, allowed=[])
    check("repeated disallowed ask fails the task", await expect(PermissionError, w(T(), {}), "not allowed for writer: web_search"))
    w = make_worker("writer", {}, chat=FakeChat(["Plain text answer"]), execute=execute, approve=None, allowed=[])
    check("plain reply is the result", await w(T(), {}) == "Plain text answer")
    async def flaky(step):
        if step.get("query") == "bad":
            raise RuntimeError("missing 1 required argument")
        return "good result"

    fc = FakeChat(['{"action": "web_search", "query": "bad"}', '{"action": "web_search", "query": "ok"}', '{"final": "fixed"}'])
    w = make_worker("researcher", {}, chat=fc, execute=flaky, approve=None, allowed=ROLE_ACTIONS["researcher"])
    check("failed tool call is fed back, model fixes it", await w(T(), {}) == "fixed" and any("Error: missing 1 required argument" in m["content"] for m in fc.calls[-1][0]))
    w = make_worker("researcher", {}, chat=FakeChat(['{"action": "web_search", "query": "same"}']), execute=execute, approve=None, allowed=ROLE_ACTIONS["researcher"])
    check("loop guard stops repeats", await expect(LoopError, w(T(), {})))

    class Counter:
        n = 0

        async def __call__(self, messages, tier):
            self.n += 1
            return json.dumps({"action": "web_search", "query": f"q{self.n}"})

    w = make_worker("researcher", {}, chat=Counter(), execute=execute, approve=None, allowed=ROLE_ACTIONS["researcher"], max_steps=6)
    check("max steps", await expect(RuntimeError, w(T(), {}), "no final answer after 6 steps"))

    async def ans(q, needed):
        return "answer:" + q

    w = make_worker("archivist", {}, chat=FakeChat(["x"]), execute=execute, approve=None, allowed=[], answer=ans)
    check("archivist uses answer()", await w(T(goal="capital of France"), {}) == "answer:capital of France")

    # 2.4 reporter
    rc = FakeChat(["Saved the comparison."])
    rep = make_reporter({}, chat=rc)
    check("one result -> as is, no model", await rep("x", {"t1": "only"}) == "only" and not rc.calls)
    check("several -> fast model", await rep("x", {"t1": "a", "t2": "b"}) == "Saved the comparison." and rc.calls[0][1] == "fast")
    check("none -> fallback text", await rep("x", {}) == "I could not finish that.")


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
