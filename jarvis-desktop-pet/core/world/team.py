"""Builds a ready world: default team, brain, runtime, Director (doc 37, task 2.4).

Model calls, skill execution and approvals are injectable so tests can run
offline. The defaults use the real LM Studio / cloud models through
``core.model_router`` and the real skills through ``execute_step``.
Sprint 3 wires this into the backend behind ``world.enabled``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

from core.world.brain import Brain
from core.world.director import Director
from core.world.reporter import make_reporter
from core.world.roles import DEFAULT_TEAM, ROLE_ACTIONS, ROLE_TIER, TEMP_TIER, WORKING_ROLES
from core.world.runtime import DEFAULT_ROOMS, AgentRuntime
from core.world.state import AgentInfo, WorldState
from core.world.thinker import make_thinker
from core.world.worker import make_worker

DEFAULT_CAPS = {"max_active_temp": 6, "max_temp_per_job": 3, "max_custom": 16, "max_tasks": 8, "max_new_agents": 3, "task_timeout_s": 300}


@dataclass
class World:
    state: WorldState
    runtime: AgentRuntime
    brain: Brain
    director: Director


def default_chat(cfg: dict):
    from core import llm, model_router

    roles = ((cfg.get("agents") or {}).get("agent_roles")) or {}
    fallback = (roles.get("orchestrator") or {}).get("model_id") or "qwen3-8b"

    async def chat(messages: list, tier: str) -> str:
        model = model_router.route(cfg, tier, fallback=fallback)
        return await llm.chat(cfg, model, messages, temperature=0.2, max_tokens=700)

    return chat


def default_execute(cfg: dict, rtm=None, skills=None):
    import asyncio

    from agents.tool_control import execute_step

    async def execute(step: dict) -> str:
        act = str(step.get("action", ""))
        if act.startswith("skill.") and skills is not None:
            from core.world.skills_lab import run_sandboxed

            params = {k: v for k, v in step.items() if k not in ("action", "risk")}
            return await asyncio.to_thread(run_sandboxed, skills.code(act[6:]), params)
        return await execute_step(cfg, rtm, step)

    return execute


def default_answer(cfg: dict):
    async def answer(question: str, needed: Dict[str, str]) -> str:
        from agents.memory_agent import MemoryAgent

        ma = MemoryAgent(None)
        ma.cfg = cfg
        q = question + "".join(f"\n\nContext from the team:\n{v}" for v in needed.values() if v)
        web = await ma._web(question) if ma._needs_web(question) else ""
        return await ma._answer(q, web) or "I don't know that yet."

    return answer


def build_world(
    cfg: dict,
    bus,
    *,
    chat: Optional[Callable] = None,
    execute: Optional[Callable] = None,
    approve: Optional[Callable] = None,
    answer: Optional[Callable] = None,
    rtm=None,
    skills=None,
) -> World:
    wcfg = ((cfg.get("config") or {}).get("world")) or {}
    caps = dict(DEFAULT_CAPS, **(wcfg.get("caps") or {}))
    chat = chat or default_chat(cfg)
    execute = execute or default_execute(cfg, rtm, skills)
    enabled_skills = (lambda: skills.enabled()) if skills is not None else (lambda: {})
    answer = answer or default_answer(cfg)

    state = WorldState()
    runtime = AgentRuntime(state, caps)
    for aid, name, role, room in DEFAULT_TEAM:
        runtime.register_default(AgentInfo(id=aid, name=name, role=role, kind="default", room=DEFAULT_ROOMS[room]))
    brain = Brain(concurrency=int(wcfg.get("brain_concurrency", 1)))

    workers = {
        role: make_worker(
            role, cfg, chat=chat, execute=execute, approve=approve, allowed=ROLE_ACTIONS[role],
            tier=ROLE_TIER.get(role, "fast"), answer=answer if role == "archivist" else None, skills=enabled_skills,
        )
        for role in WORKING_ROLES
    }

    def temp_worker(role: str):
        desc = next((a.description for a in state.agents.values() if a.role == role and a.description), "")
        return make_worker(role, cfg, chat=chat, execute=execute, approve=approve, allowed=[], tier=TEMP_TIER, extra=desc, skills=enabled_skills)

    def roles():
        extra = [f"skill.{n}" for n in enabled_skills()]
        r = {k: ROLE_ACTIONS[k] + extra for k in WORKING_ROLES}
        for a in state.agents.values():
            if a.kind == "custom" and a.role not in r:
                r[a.role] = f"(custom agent {a.name}) {a.description or 'general helper'}; answers with text"
        return r

    director = Director(
        bus, state, runtime, brain,
        thinker=make_thinker(cfg, chat=chat, roles=roles),
        workers=workers,
        reporter=make_reporter(cfg, chat=chat),
        caps=caps,
        make_temp_worker=temp_worker,
    )
    return World(state=state, runtime=runtime, brain=brain, director=director)
