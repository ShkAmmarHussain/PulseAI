"""Thinker: turns a request into a plan (doc 36 §7.1, §7.2).

Cheapest first: a rule match from the existing planner (no model), then a
plain question (one archivist task, no model), and only a complex request
goes to the heavy model for a JSON plan.
"""

from __future__ import annotations

import json
import re
from typing import Awaitable, Callable, Dict, List

from agents.planner import plan_steps
from core import model_router
from core.world.roles import ROLE_FOR_ACTION

Chat = Callable[[list, str], Awaitable[str]]
RETRY_MARK = "Your last plan was invalid"


def parse_json(raw: str):
    """First JSON object in a model reply (handles ``` fences and prose); None if none."""
    if not raw:
        return None
    text = re.sub(r"```(?:json)?", "", str(raw))
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def single(text: str, role: str, steps=None) -> dict:
    task = {"id": "t1", "role": role, "goal": text, "needs": []}
    if steps:
        task["steps"] = steps
    return {"intent": text, "tasks": [task], "new_agents": []}


def system_prompt(roles) -> str:
    def can(a):
        if isinstance(a, str):
            return a
        return "can " + (", ".join(a) if a else "answer from memory and general knowledge")
    lines = [f"- {r}: {can(a)}" for r, a in roles.items()]
    return (
        "You plan work for a team of agents on the user's Windows PC. You never do the work yourself.\n"
        "Team roles:\n" + "\n".join(lines) + "\n\n"
        "Reply with ONLY a JSON object:\n"
        '{"intent": "...", "tasks": [{"id": "t1", "role": "researcher", "goal": "...", "needs": []}], '
        '"new_agents": [{"role": "writer", "why": "..."}]}\n'
        "Rules: at most 8 tasks; ids t1, t2, ...; 'needs' lists task ids whose results this task uses; "
        "use a team role when one fits, otherwise invent a one-word lowercase role (writer, coder, translator) "
        "and list it in new_agents (at most 3); each goal is one concrete instruction; "
        "when a skill.<name> fits, the goal must say to use that skill and with which values."
    )


def make_thinker(cfg: dict, *, chat: Chat, roles: Dict[str, List[str]]):
    async def think(text: str) -> dict:
        text = str(text or "").strip()
        # long or multi-part requests always get a real plan: the rule router
        # would grab one keyword ("write ...") and type the whole sentence
        if RETRY_MARK not in text and not model_router.is_complex(text):
            steps = plan_steps(text)
            if steps:
                acts = [s.get("action") for s in steps if s.get("action") != "respond"]
                role = ROLE_FOR_ACTION.get(acts[0], "operator") if acts else "archivist"
                return single(text, role, steps)
            return single(text, "archivist")
        raw = await chat(
            [{"role": "system", "content": system_prompt(roles() if callable(roles) else roles)}, {"role": "user", "content": text}],
            "heavy",
        )
        return parse_json(raw) or {}

    return think
