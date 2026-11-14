"""Workers: the agents that actually do tasks (doc 36 §9.4).

A task carrying rule ``steps`` runs them directly. Otherwise the worker runs
a small JSON tool loop with its model: ``{"action": ...}`` to use a skill,
``{"final": "..."}`` to finish. Every action is checked against the role's
allow-list, the loop guard and the risk/approval rules before it runs.
"""

from __future__ import annotations

import json
from typing import Awaitable, Callable, Dict, List, Optional

from core.guardrails import risk_score
from core.world.runtime import LoopError, LoopGuard
from core.world.state import TaskInfo
from core.world.thinker import parse_json

Chat = Callable[[list, str], Awaitable[str]]
Execute = Callable[[dict], Awaitable[str]]
Approve = Callable[[dict, int], Awaitable[bool]]
Answer = Callable[[str, Dict[str, str]], Awaitable[str]]


def _policy(cfg: dict) -> str:
    return str((((cfg or {}).get("permissions") or {}).get("default_policy")) or "conservative").lower()


def worker_prompt(role: str, allowed: List[str], extra: str = "", skills: Optional[Dict[str, dict]] = None) -> str:
    acts = ", ".join(allowed) if allowed else "none (answer with text only)"
    if skills:
        acts += "; user skills: " + "; ".join(
            f"skill.{n} ({m.get('description', '')}; params: {', '.join(m.get('params') or {}) or 'none'})" for n, m in skills.items()
        )
    purpose = f"What you are for: {extra}\n" if extra else ""
    return (
        f"You are the {role} agent on the user's Windows PC. Do the task you are given.\n"
        + purpose
        + f"Actions you may use: {acts}.\n"
        'To use one, reply with ONLY JSON like {"action": "web_search", "query": "..."}. '
        "You will get its result back.\n"
        'When done, reply with ONLY {"final": "<your result for the team>"}. Keep results short and factual.'
    )


def make_worker(
    role: str,
    cfg: dict,
    *,
    chat: Chat,
    execute: Execute,
    approve: Optional[Approve],
    allowed: List[str],
    tier: str = "fast",
    max_steps: int = 6,
    answer: Optional[Answer] = None,
    guard: Optional[LoopGuard] = None,
    extra: str = "",
    skills: Optional[Callable[[], Dict[str, dict]]] = None,
):
    guard = guard or LoopGuard()

    def can_use(act: str) -> bool:
        if act == "respond" or act in allowed:
            return True
        return act.startswith("skill.") and skills is not None and act[6:] in skills()

    async def run_step(step: dict, key: str) -> str:
        act = str(step.get("action", ""))
        if not can_use(act):
            raise PermissionError(f"not allowed for {role}: {act}")
        guard.check(key, act, {k: v for k, v in step.items() if k != "risk"})
        risk = risk_score(act, step)
        if act.startswith("skill."):
            risk = int((skills() or {}).get(act[6:], {}).get("risk", 5))
        if risk >= 6 and _policy(cfg) != "autonomous":
            if approve is None or not await approve(step, risk):
                raise PermissionError(f"denied: {act}")
        return str(await execute(step))

    async def work(task: TaskInfo, needed: Dict[str, str]) -> str:
        steps = (task.params or {}).get("steps")
        if steps:
            return "\n".join([await run_step(s, task.id) for s in steps])
        if answer is not None:
            return await answer(task.goal, needed)
        context = "".join(f"\n\nResult of {k}:\n{v}" for k, v in needed.items() if v)
        msgs = [
            {"role": "system", "content": worker_prompt(role, allowed, extra, skills() if skills else None)},
            {"role": "user", "content": f"Task: {task.goal}{context}"},
        ]
        refused = 0
        for _ in range(max_steps):
            raw = await chat(msgs, tier)
            obj = parse_json(raw)
            if obj is None:
                return str(raw or "").strip()
            if "final" in obj:
                return str(obj["final"])
            act = str(obj.get("action", ""))
            if not can_use(act):
                # a model asking for a skill it does not have gets told so and
                # keeps going with what it has; only repeated asks fail the task
                refused += 1
                if refused >= 2:
                    raise PermissionError(f"not allowed for {role}: {act}")
                msgs += [
                    {"role": "assistant", "content": json.dumps(obj)},
                    {"role": "user", "content": f"You cannot use {act}. Work only with the task and the results above, then reply with the final JSON."},
                ]
                continue
            try:
                out = await run_step(obj, task.id)
            except (PermissionError, LoopError):
                raise
            except Exception as e:  # a failed tool call goes back to the model to fix
                out = f"Error: {e}. Fix the action (check the parameter names) or finish with what you have."
            msgs += [
                {"role": "assistant", "content": json.dumps(obj)},
                {"role": "user", "content": f"Result:\n{out[:4000]}"},
            ]
        raise RuntimeError(f"no final answer after {max_steps} steps")

    return work
