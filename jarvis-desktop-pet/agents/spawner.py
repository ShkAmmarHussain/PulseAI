from agents.base import BaseAgent
from core.bus import Event, create_event
from skills.templates.agent_spec import AgentSpec
from skills.templates.skill_spec import SkillSpec


class SpawnerAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("spawner", bus)
        self._active = 0

    async def start(self):
        await super().start()
        self.bus.subscribe("spawner.request", self.handle)

    async def handle(self, ev: Event):
        et = ev.type
        if et == "spawn_agent":
            spec = ev.payload.get("spec", {})
            # basic validation + spawn acknowledgment
            name = spec.get("name") or "worker"
            await self.bus.publish(create_event("spawner.result", "spawned", {"agent": name, "ok": True}, correlation_id=ev.correlation_id))
        elif et == "create_skill":
            spec = ev.payload.get("spec", {})
            name = spec.get("name") or "skill"
            # governance: respect require_approval_high_risk later
            await self.bus.publish(create_event("spawner.result", "skill_created", {"skill": name, "enabled": spec.get("enabled", False)}, correlation_id=ev.correlation_id))
