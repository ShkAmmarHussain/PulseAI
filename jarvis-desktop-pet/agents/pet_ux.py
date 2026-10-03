from agents.base import BaseAgent
from core.bus import Event, create_event


class PetUXAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("pet_ux", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("pet.state", self.handle)

    async def handle(self, ev: Event):
        if ev.type == "speak":
            # forward to UI over WS later
            await self.bus.publish(create_event("ui.pet_state", "bubble", ev.payload, correlation_id=ev.correlation_id))
