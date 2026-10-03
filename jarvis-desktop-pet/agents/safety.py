from agents.base import BaseAgent
from core.bus import Event, create_event
from core.guardrails import risk_score


class SafetyAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("safety", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("safety.check", self.handle)

    async def handle(self, ev: Event):
        if ev.type == "check":
            action = ev.payload.get("action", {})
            all_steps = ev.payload.get("all_steps", [action])
            r = max(risk_score(s.get("action", ""), s) for s in all_steps) if all_steps else 0
            decision = "allow" if r < 6 else "deny"
            await self.bus.publish(
                create_event(
                    "safety.decision",
                    "decision",
                    {"decision": decision, "risk": r, "action": action, "all_steps": all_steps},
                    correlation_id=ev.correlation_id,
                )
            )