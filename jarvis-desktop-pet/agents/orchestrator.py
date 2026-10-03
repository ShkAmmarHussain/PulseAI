from agents.base import BaseAgent
from core.bus import Event, create_event
from core.guardrails import risk_score


class OrchestratorAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("orchestrator", bus)

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
                await self.bus.publish(
                    create_event("ui.chat", "chat", {"role": "assistant", "text": "I need your approval for that action."}, correlation_id=cid)
                )

        elif et == "approval_response":
            allowed = payload.get("allow", False)
            action = payload.get("action", {})
            steps = payload.get("all_steps", [action])
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