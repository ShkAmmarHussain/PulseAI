import uuid

from agents.base import BaseAgent
from core.bus import Event, create_event
from core.guardrails import risk_score


class OrchestratorAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("orchestrator", bus)
        self._approval_timers = {}
        self._approval_expired = set()
        self._approval_settled = set()
        self._approval_steps = {}

    def _approval_timeout_s(self) -> float:
        perms = (self.cfg or {}).get("permissions") or {}
        appr = perms.get("approvals") or {}
        try:
            return max(5.0, float(appr.get("timeout_ms", 45000))) / 1000.0
        except Exception:
            return 45.0

    def _arm_approval(self, cid):
        if not cid or cid in self._approval_timers:
            return
        if len(self._approval_settled) > 128:
            self._approval_settled.clear()
        if len(self._approval_expired) > 128:
            self._approval_expired.clear()
        import asyncio

        async def _expire():
            await asyncio.sleep(self._approval_timeout_s())
            if self._approval_timers.pop(cid, None) is None:
                return
            self._approval_steps.pop(cid, None)
            self._approval_expired.add(cid)
            await self.bus.publish(
                create_event("ui.approval_cancelled", "approval_cancelled", {"reason": "timeout"}, correlation_id=cid)
            )
            await self.bus.publish(
                create_event(
                    "ui.chat", "chat",
                    {"role": "system", "text": "Approval timed out \u2014 treated as denied. Nothing was changed."},
                    correlation_id=cid,
                )
            )

        self._approval_timers[cid] = asyncio.get_event_loop().create_task(_expire())

    def _settle_approval(self, cid) -> bool:
        """True only for the first valid response to a still-pending approval.

        Duplicate answers (both main and pet window clicked), responses to
        expired prompts and responses for never-armed correlation ids are all
        rejected - the old code executed the tool again for any of these.
        """
        if not cid:
            return False
        if cid in self._approval_settled:
            return False
        t = self._approval_timers.pop(cid, None)
        if t is not None:
            t.cancel()
            self._approval_settled.add(cid)
            return True
        if cid in self._approval_expired:
            self._approval_expired.discard(cid)
            self._approval_settled.add(cid)
        return False

    async def start(self):
        await super().start()
        self.bus.subscribe("orchestrator.input", self.handle)
        self.bus.subscribe("orchestrator.handoff.orchestrator", self.handle)
        self.bus.subscribe("tool.result", self.handle)
        self.bus.subscribe("safety.decision", self.handle)
        self.bus.subscribe("memory.result", self.handle)
        self.bus.subscribe("planner.result", self.handle)
        self.bus.subscribe("ui.approval.response", self.handle)

    async def handle(self, ev: Event):
        et = ev.type
        topic = ev.topic
        payload = ev.payload
        cid = ev.correlation_id

        if et == "input":
            text = str(payload.get("text", payload.get("transcript", ""))).strip()
            if not text:
                return
            await self.bus.publish(
                create_event("ui.chat", "chat", {"role": "user", "text": text}, correlation_id=cid)
            )
            low = text.lower()
            triggers = ("open", "type", "click", "run", "delete", "launch", "close", "move", "create", "search")
            if len(text.split()) > 8 or any(t in low for t in triggers):
                await self.bus.publish(create_event("planner.request", "plan", {"query": text}, correlation_id=cid))
            else:
                await self.bus.publish(create_event("memory.request", "recall", {"query": text}, correlation_id=cid))

        elif et == "plan":
            # planner handed a plan back; check safety before executing steps
            steps = payload.get("steps", [])
            if steps:
                await self.bus.publish(
                    create_event("safety.check", "check", {"action": steps[0], "all_steps": steps}, correlation_id=cid)
                )

        elif et == "decision":
            decision = payload.get("decision", "deny")
            action = payload.get("action", {})
            steps = payload.get("all_steps", [action])
            if decision == "allow":
                await self.bus.publish(
                    create_event("tool.execute", "execute", {"steps": steps}, correlation_id=cid)
                )
            else:
                if not cid:
                    # voice/hotkey inputs can arrive without a correlation id;
                    # approvals must always have one so they can be answered
                    cid = uuid.uuid4().hex
                risk = payload.get("risk", 5)
                await self.bus.publish(
                    create_event(
                        "ui.approval",
                        "approval",
                        {
                            "action": action,
                            "risk": risk,
                            "message": f"Allow this action? ({action.get('action', 'unknown')}, risk {risk}/10)",
                        },
                        correlation_id=cid,
                    )
                )
                self._approval_steps[cid] = steps
                self._arm_approval(cid)
                # no correlation id here: clients treat any ui.chat carrying
                # the approval cid as its outcome and would hide the fresh card
                await self.bus.publish(
                    create_event("ui.chat", "chat", {"role": "assistant", "text": "I need your approval for that action."})
                )

        elif et == "approval_response":
            if not self._settle_approval(cid):
                # duplicate / expired / unknown answer: never re-execute;
                # re-sync clients in case a card is stuck in pending state
                if cid:
                    await self.bus.publish(
                        create_event(
                            "ui.approval_cancelled", "approval_cancelled", {"reason": "already_answered"}, correlation_id=cid
                        )
                    )
                return
            allowed = payload.get("allow", False)
            # execute the steps safety reviewed at prompt time - never steps
            # supplied by the responding client
            steps = self._approval_steps.pop(cid, None)
            if not steps:
                return
            if allowed:
                await self.bus.publish(create_event("tool.execute", "execute", {"steps": steps}, correlation_id=cid))
            else:
                await self.bus.publish(
                    create_event("ui.chat", "chat", {"role": "assistant", "text": "Action denied. No changes made."}, correlation_id=cid)
                )

        elif et == "tool_result":
            summary = payload.get("summary", "Done.")
            await self.bus.publish(create_event("memory.store", "store", {"event": "tool_result", "data": payload}, correlation_id=cid))
            await self.bus.publish(create_event("ui.chat", "chat", {"role": "assistant", "text": summary}, correlation_id=cid))
            await self.bus.publish(create_event("voice.say", "say", {"text": summary}, correlation_id=cid))

        elif et == "memory_result":
            ans = payload.get("answer", "")
            if ans:
                await self.bus.publish(create_event("ui.chat", "chat", {"role": "assistant", "text": ans}, correlation_id=cid))
                await self.bus.publish(create_event("voice.say", "say", {"text": ans}, correlation_id=cid))

        elif topic.startswith("orchestrator.handoff."):
            await self.bus.publish(create_event("planner.request", "plan", payload, correlation_id=cid))