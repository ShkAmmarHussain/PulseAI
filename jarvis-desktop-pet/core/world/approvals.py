"""Approval bridge: world workers ask the user through the existing cards (doc 36 §16).

Raises ``ui.approval`` on a fresh correlation id (the island, pet and main
window already render it) and waits for the first ``ui.approval.response``
on that id. Timeout counts as deny, like the Orchestrator's own approvals.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Dict

from core.bus import Event, create_event


class ApprovalBridge:
    def __init__(self, bus, timeout_s: float = 45.0):
        self.bus = bus
        self.timeout_s = float(timeout_s)
        self._waiting: Dict[str, asyncio.Future] = {}
        bus.subscribe("ui.approval.response", self._on_response)

    @staticmethod
    def timeout_from(cfg: dict) -> float:
        perms = (cfg or {}).get("permissions") or {}
        ms = ((perms.get("approvals") or {}).get("timeout_ms")) or 45000
        try:
            return max(5.0, float(ms) / 1000.0)
        except (TypeError, ValueError):
            return 45.0

    async def _on_response(self, ev: Event) -> None:
        fut = self._waiting.get(ev.correlation_id or "")
        if fut is not None and not fut.done():
            fut.set_result(bool((ev.payload or {}).get("allow", False)))

    async def ask(self, step: dict, risk: int, job_id: str = "") -> bool:
        cid = f"world-{uuid.uuid4().hex[:12]}"
        fut = asyncio.get_running_loop().create_future()
        self._waiting[cid] = fut
        action = step.get("action", "unknown")
        await self.bus.publish(create_event(
            "ui.approval", "approval",
            {"action": step, "risk": risk, "job_id": job_id, "message": f"Allow this action? ({action}, risk {risk}/10)"},
            correlation_id=cid,
        ))
        try:
            return await asyncio.wait_for(fut, timeout=self.timeout_s)
        except asyncio.TimeoutError:
            await self.bus.publish(create_event("ui.approval_cancelled", "approval_cancelled", {"reason": "timeout"}, correlation_id=cid))
            return False
        except asyncio.CancelledError:
            # the job was stopped while the card was up: take the card down
            await asyncio.shield(self.bus.publish(create_event("ui.approval_cancelled", "approval_cancelled", {"reason": "stopped"}, correlation_id=cid)))
            raise
        finally:
            self._waiting.pop(cid, None)

    def pending(self) -> int:
        return len(self._waiting)
