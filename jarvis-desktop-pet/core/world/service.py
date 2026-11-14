"""WorldService: the Mini World inside the running backend (doc 37, sprint 3).

Owns the world built by ``build_world`` and connects it to the bus:
input in, ``ui.chat`` / ``voice.say`` / ``memory.store`` out, plus the
``world.cmd.*`` commands the UI sends (say, stop, snapshot).
"""

from __future__ import annotations

import asyncio
import re
import os
import uuid
from typing import Optional

from core.bus import Event, create_event
from dataclasses import asdict

from core.world.agents_store import AgentStore
from core.world.approvals import ApprovalBridge
from core.world.runtime import CapError
from core.world.skills_lab import DRAFT_PROMPT, SkillStore, check_code, run_sandboxed
from core.world.team import build_world, default_chat
from core.world.thinker import parse_json

NAMES = ["Wren", "Kai", "Juno", "Moss", "Nova", "Ivo", "Lark", "Pax", "Sol", "Tess", "Rio", "Fen", "Mika", "Zed"]
RESERVED_ROLES = {"director", "thinker", "builder", "reporter", "researcher", "operator", "watcher", "archivist"}
ROLE_WORDS = {"translat": "translator", "code": "coder", "program": "coder", "write": "writer", "summar": "writer",
              "design": "designer", "analy": "analyst", "data": "analyst", "math": "analyst", "email": "writer"}


def slug_role(text: str, state) -> str:
    """One lowercase word for a new agent's role, never clashing with a default role."""
    low = str(text or "").lower()
    role = next((r for k, r in ROLE_WORDS.items() if k in low), None)
    if role is None:
        words = [w for w in "".join(c if c.isalpha() else " " for c in low).split() if len(w) > 2]
        role = (words[0] if words else "helper")[:16]
    if role in RESERVED_ROLES:
        role += "2"
    taken = {a.role for a in state.agents.values()}
    base, n = role, 2
    while role in taken:
        role, n = f"{base}{n}", n + 1
    return role


def pick_name(state) -> str:
    used = {a.name for a in state.agents.values()}
    return next((n for n in NAMES if n not in used), f"Agent {len(state.agents) + 1}")


def world_enabled(cfg: dict) -> bool:
    env = os.environ.get("PULSEAI_WORLD")
    if env in ("0", "1"):
        return env == "1"
    # on by default since sprint 8; an explicit `enabled: false` still turns it off
    return bool((((cfg or {}).get("config") or {}).get("world") or {}).get("enabled", True))


class WorldService:
    def __init__(self, bus, cfg: dict, rtm=None, chat=None, execute=None, answer=None, store: Optional[AgentStore] = None,
                 skills: Optional[SkillStore] = None):
        self.bus = bus
        self.approvals = ApprovalBridge(bus, ApprovalBridge.timeout_from(cfg))
        self.skills = skills or SkillStore()
        self.chat = chat or default_chat(cfg)
        self.world = build_world(
            cfg, bus, chat=self.chat, execute=execute, answer=answer, rtm=rtm, skills=self.skills,
            approve=lambda step, risk: self.approvals.ask(step, risk),
        )
        self.store = store or AgentStore()
        self._jobs = set()
        self.enabled = True
        # custom agents come back after a restart, in their old rooms when free
        for rec in self.store.load():
            try:
                self.world.runtime.spawn_custom(
                    rec.get("name") or "Agent", rec.get("role") or "helper", rec.get("description") or "",
                    rec.get("look_seed") or "", agent_id=rec.get("id"), room=rec.get("room"),
                )
            except (CapError, ValueError):
                continue

    def start(self) -> None:
        self.bus.subscribe("world.cmd.say", self._on_say)
        self.bus.subscribe("world.cmd.stop", self._on_stop)
        self.bus.subscribe("world.cmd.snapshot", self._on_snapshot)
        self.bus.subscribe("world.cmd.agent", self._on_agent)
        self.bus.subscribe("world.cmd.skill", self._on_skill)

    # ---- skills (doc 37 sprint 6) ----
    def _skill_view(self, meta: dict) -> dict:
        v = dict(meta)
        try:
            v["code"] = self.skills.code(meta["name"])
        except (KeyError, OSError):
            v["code"] = ""
        return v

    async def _publish_skills(self, cid=None):
        await self.bus.publish(create_event("world.skills", "skills", {"skills": [self._skill_view(m) for m in self.skills.list()]}, correlation_id=cid))

    async def draft_skill(self, description: str) -> dict:
        description = str(description or "").strip()
        if not description:
            raise ValueError("Describe what the skill should do.")
        st = self.world.state
        builder = next((a for a in st.agents.values() if a.role == "builder" and a.kind == "default"), None)
        if builder:
            st.update_agent(builder.id, state="working", label="drafting a skill")
        try:
            raw = await self.world.brain.submit(
                lambda: self.chat([{"role": "system", "content": DRAFT_PROMPT}, {"role": "user", "content": description}], "heavy"),
                job_id="skill-draft", priority=1,
            )
        finally:
            if builder:
                st.update_agent(builder.id, state="idle", label="")
        spec = parse_json(raw) or {}
        code = str(spec.get("code") or "")
        if not code:
            raise ValueError("The Builder could not write that skill. Try describing it differently.")
        name = re.sub(r"[^a-z0-9_]", "_", str(spec.get("name") or "skill").lower()).strip("_")[:32] or "skill"
        if not name[0].isalpha():
            name = "s_" + name
        spec.update(name=name, code=code, description=str(spec.get("description") or description)[:200])
        perms = [p for p in spec.get("permissions") or [] if p in ("files", "network")]
        spec["permissions"] = perms
        errors = check_code(code, perms)
        test = ""
        if not errors:
            try:
                test = await asyncio.to_thread(run_sandboxed, code, spec.get("example") or {})
            except Exception as e:  # a skill that fails its own example is not enabled
                errors.append(f"test run failed: {e}")
        return self.skills.add_draft(spec, errors, test)

    async def _on_skill(self, ev: Event) -> None:
        p = ev.payload or {}
        op, cid = p.get("op"), ev.correlation_id
        try:
            if op == "list":
                pass
            elif op == "draft":
                meta = await self.draft_skill(p.get("description", ""))
                verdict = "passed the safety check and its test" if not meta["check"] else "has problems, so it stays a draft"
                await self._say(f"Bodie drafted the skill {meta['name']}. It {verdict}. Review it in Skills.", cid)
            elif op == "enable":
                self.skills.set_status(p["name"], "enabled")
                await self._say(f"Skill {p['name']} is on. Agents can use it now.", cid)
            elif op == "disable":
                self.skills.set_status(p["name"], "disabled")
            elif op == "delete":
                self.skills.delete(p["name"])
            elif op == "test":
                out = await asyncio.to_thread(run_sandboxed, self.skills.code(p["name"]), p.get("params") or {})
                await self.bus.publish(create_event("world.skill.test", "test", {"name": p["name"], "output": out}, correlation_id=cid))
            else:
                raise ValueError(f"unknown skill command: {op}")
        except KeyError:
            await self._say("That skill does not exist any more.", cid)
        except (ValueError, RuntimeError) as e:
            await self._say(str(e)[:1].upper() + str(e)[1:], cid)
        await self._publish_skills(cid)

    # ---- agents (doc 37 sprint 5) ----
    def _say(self, text: str, cid=None):
        return self.bus.publish(create_event("ui.chat", "chat", {"role": "system", "text": text}, correlation_id=cid))

    def _persist(self, agent_id: str) -> None:
        a = self.world.state.agents.get(agent_id)
        if a is not None and a.kind == "custom":
            self.store.save(asdict(a))

    async def create_agent(self, description: str, role: str = "", name: str = "") -> str:
        description = str(description or "").strip()
        if not description:
            raise ValueError("Tell me what the new agent should do.")
        role = slug_role(role or description, self.world.state)
        name = (name or "").strip()[:24] or pick_name(self.world.state)
        builder = next((a for a in self.world.state.agents.values() if a.role == "builder" and a.kind == "default"), None)
        if builder:
            self.world.state.update_agent(builder.id, state="working", label=f"making {name}")
        try:
            await asyncio.sleep(0.6)  # long enough to see Bodie at the bench
            agent_id = self.world.runtime.spawn_custom(name, role, description)
        finally:
            if builder:
                self.world.state.update_agent(builder.id, state="idle", label="")
        self._persist(agent_id)
        return agent_id

    async def _on_agent(self, ev: Event) -> None:
        p = ev.payload or {}
        op, cid = p.get("op"), ev.correlation_id
        rt, st = self.world.runtime, self.world.state
        try:
            if op == "create":
                aid = await self.create_agent(p.get("description", ""), p.get("role", ""), p.get("name", ""))
                a = st.agents[aid]
                await self._say(f"{a.name} joined the team and moved into a spare room.", cid)
            elif op == "keep":
                a = rt.keep(p["id"])
                self._persist(a.id)
                await self._say(f"{a.name} is staying as a lasting agent.", cid)
            elif op == "delete":
                a = rt.remove(p["id"])
                self.world.director.workers.pop(a.role, None)
                if a.kind == "custom":
                    self.store.archive(a.id)
                    await self._say(f"{a.name} left. You can bring them back for 30 days.", cid)
                else:
                    await self._say(f"{a.name} was dismissed.", cid)
            elif op == "update":
                a = st.agents[p["id"]]
                if a.kind == "default":
                    raise ValueError(f"{a.name} is a default agent; only custom and temporary agents can be edited.")
                fields = {k: str(p[k]).strip()[:400] for k in ("name", "description", "look_seed") if p.get(k) is not None}
                if "name" in fields:
                    fields["name"] = fields["name"][:24] or a.name
                st.update_agent(a.id, **fields)
                self.world.director.workers.pop(a.role, None)  # rebuild with the new description
                self._persist(a.id)
            elif op == "restore":
                rec = self.store.restore(p["id"])
                if rec is None:
                    raise ValueError("That agent is no longer in the archive.")
                rt.spawn_custom(rec["name"], rec["role"], rec.get("description", ""), rec.get("look_seed", ""), agent_id=rec["id"])
                self._persist(rec["id"])
                await self._say(f"{rec['name']} is back.", cid)
            elif op == "archived":
                await self.bus.publish(create_event("world.archived", "archived", {"agents": self.store.archived()}, correlation_id=cid))
            else:
                raise ValueError(f"unknown agent command: {op}")
        except KeyError:
            await self._say("That agent is not in the building any more.", cid)
        except (CapError, ValueError) as e:
            await self._say(str(e)[:1].upper() + str(e)[1:], cid)

    async def handle_input(self, text: str, cid: Optional[str] = None) -> asyncio.Task:
        text = str(text or "").strip()
        cid = cid or uuid.uuid4().hex[:12]
        await self.bus.publish(create_event("ui.chat", "chat", {"role": "user", "text": text}, correlation_id=cid))
        task = asyncio.get_running_loop().create_task(self._run(text, cid))
        self._jobs.add(task)
        task.add_done_callback(self._jobs.discard)
        return task

    async def _run(self, text: str, cid: str):
        job = await self.world.director.handle(text, job_id=cid)
        if job.answer:
            await self.bus.publish(create_event("voice.say", "say", {"text": job.answer}, correlation_id=cid))
        await self.bus.publish(create_event(
            "memory.store", "store", {"event": "world_job", "data": {"text": text, "status": job.status, "answer": job.answer}},
            correlation_id=cid,
        ))
        return job

    async def stop_all(self) -> int:
        n = len(self.world.director._open)
        await self.world.director.stop_all()
        return n

    async def _on_say(self, ev: Event) -> None:
        if not self.enabled:
            return
        await self.handle_input((ev.payload or {}).get("text", ""), ev.correlation_id)

    async def _on_stop(self, ev: Event) -> None:
        n = await self.stop_all()
        await self.bus.publish(create_event("ui.chat", "chat", {"role": "system", "text": f"Stopped {n} running job(s)."}, correlation_id=ev.correlation_id))

    async def _on_snapshot(self, ev: Event) -> None:
        await self.bus.publish(create_event("world.snapshot", "snapshot", self.world.state.snapshot(), correlation_id=ev.correlation_id))
