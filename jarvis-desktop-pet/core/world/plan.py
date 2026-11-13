"""Plan validation for the Thinker's output (doc 36 §7.1).

A plan is ``{"intent": str, "tasks": [{"id","role","goal","needs"}],
"new_agents": [{"role","why"}]}``. ``validate_plan`` returns the tasks in a
runnable order (dependencies first, otherwise input order) and a list of
human-readable errors. Any error means the plan must not run.
"""

from __future__ import annotations

from typing import List, Set, Tuple


def validate_plan(plan, known_roles: Set[str], caps: dict) -> Tuple[List[dict], List[str]]:
    if not isinstance(plan, dict):
        return [], ["plan is not an object"]
    tasks = plan.get("tasks") or []
    new_agents = plan.get("new_agents") or []
    errors: List[str] = []
    if not isinstance(tasks, list) or not tasks:
        return [], ["plan has no tasks"]

    max_tasks = int(caps.get("max_tasks", 8))
    max_new = int(caps.get("max_new_agents", 3))
    if len(tasks) > max_tasks:
        errors.append(f"too many tasks ({len(tasks)} > {max_tasks})")
    if len(new_agents) > max_new:
        errors.append(f"too many new agents ({len(new_agents)} > {max_new})")

    roles = set(known_roles) | {str(a.get("role", "")) for a in new_agents if isinstance(a, dict)}
    ids: List[str] = []
    for t in tasks:
        if not isinstance(t, dict) or not t.get("id"):
            errors.append("task without id")
            continue
        tid = str(t["id"])
        if tid in ids:
            errors.append(f"duplicate task id: {tid}")
        ids.append(tid)
        role = str(t.get("role", ""))
        if role not in roles:
            errors.append(f"unknown role: {role}")
    idset = set(ids)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for dep in t.get("needs") or []:
            if dep not in idset:
                errors.append(f"unknown dependency: {dep}")
    if errors:
        return [], errors

    # Kahn's algorithm, stable by input order
    remaining = {str(t["id"]): set(t.get("needs") or []) for t in tasks}
    by_id = {str(t["id"]): t for t in tasks}
    order: List[dict] = []
    while remaining:
        ready = [tid for tid in ids if tid in remaining and not remaining[tid]]
        if not ready:
            return [], ["cycle in tasks"]
        for tid in ready:
            order.append(by_id[tid])
            del remaining[tid]
        for deps in remaining.values():
            deps.difference_update(ready)
    return order, []
