"""Mini World plan validation (doc 37, task 1.2).

Run: .venv/Scripts/python tests/world_plan_test.py
exit 0 = pass
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.world.plan import validate_plan  # noqa: E402

results = []
CAPS = {"max_tasks": 8, "max_new_agents": 3}
ROLES = {"researcher", "operator"}


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def T(i, role="researcher", needs=()):
    return {"id": i, "role": role, "goal": f"goal {i}", "needs": list(needs)}


DOC_PLAN = {
    "intent": "compare two laptops and save the result",
    "tasks": [
        T("t1"), T("t2"),
        T("t3", "writer", ["t1", "t2"]),
        T("t4", "operator", ["t3"]),
    ],
    "new_agents": [{"role": "writer", "why": "no default agent writes long documents"}],
}

order, errs = validate_plan(DOC_PLAN, ROLES, CAPS)
ids = [t["id"] for t in order]
check("doc example: no errors", errs == [], errs)
check("doc example: run order", ids.index("t3") > max(ids.index("t1"), ids.index("t2")) and ids.index("t4") > ids.index("t3"), ids)
check("doc example: stable order", ids == ["t1", "t2", "t3", "t4"], ids)


def errors(plan):
    return validate_plan(plan, ROLES, CAPS)[1]


check("unknown role", "unknown role: coder" in errors({"tasks": [T("t1", "coder")], "new_agents": []}))
check("cycle", "cycle in tasks" in errors({"tasks": [T("t1", needs=["t2"]), T("t2", needs=["t1"])]}))
check("unknown dependency", "unknown dependency: t9" in errors({"tasks": [T("t1", needs=["t9"])]}))
check("too many tasks", "too many tasks (9 > 8)" in errors({"tasks": [T(f"t{i}") for i in range(9)]}))
check(
    "too many new agents",
    "too many new agents (4 > 3)" in errors({"tasks": [T("t1")], "new_agents": [{"role": r} for r in "abcd"]}),
)
check("empty tasks", "plan has no tasks" in errors({"tasks": []}))
check("missing tasks key", "plan has no tasks" in errors({}))
check("duplicate id", "duplicate task id: t1" in errors({"tasks": [T("t1"), T("t1")]}))
check("not a dict", validate_plan("nope", ROLES, CAPS)[1] == ["plan is not an object"])
check("errors -> empty order", validate_plan({"tasks": []}, ROLES, CAPS)[0] == [])

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
