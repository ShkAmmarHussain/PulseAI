"""WorldService: the Mini World inside the running backend (doc 37, sprint 3).

Owns the world built by ``build_world`` and connects it to the bus:
input in, ``ui.chat`` / ``voice.say`` / ``memory.store`` out, plus the
``world.cmd.*`` commands the UI sends (say, stop, snapshot).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Optional

from core.bus import Event, create_event
from core.world.approvals import ApprovalBridge
from core.world.team import build_world


def world_enabled(cfg: dict) -> bool:
    if os.environ.get("PULSEAI_WORLD") == "1":
        return True
    return bool((((cfg or {}).get("config") or {}).get("world") or {}).get("enabled", False))


class WorldService:
    def __init__(self, bus, cfg: dict, rtm=None, chat=None, execute=None, answer=None):
        self.bus = bus
        self.approvals = ApprovalBridge(bus, ApprovalBridge.timeout_from(cfg))
        self.world = build_world(
            cfg, bus, chat=chat, execute=execute, answer=answer, rtm=rtm,
            approve=lambda step, risk: self.approvals.ask(step, risk),
        )
        self._jobs = set()

    def start(self) -> None:
        self.bus.subscribe("world.cmd.say", self._on_say)
        self.bus.subscribe("world.cmd.stop", self._on_stop)
        self.bus.subscribe("world.cmd.snapshot", self._on_snapshot)

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
        await self.handle_input((ev.payload or {}).get("text", ""), ev.correlation_id)

    async def _on_stop(self, ev: Event) -> None:
        n = await self.stop_all()
        await self.bus.publish(create_event("ui.chat", "chat", {"role": "system", "text": f"Stopped {n} running job(s)."}, correlation_id=ev.correlation_id))

    async def _on_snapshot(self, ev: Event) -> None:
        await self.bus.publish(create_event("world.snapshot", "snapshot", self.world.state.snapshot(), correlation_id=ev.correlation_id))
