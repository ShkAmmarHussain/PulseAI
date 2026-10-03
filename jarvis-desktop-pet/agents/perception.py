from agents.base import BaseAgent
from core.bus import Event, create_event


class PerceptionAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("perception", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("ui.input.text", self.handle)
        self.bus.subscribe("audio.input.voice", self.handle)

    async def handle(self, ev: Event):
        if ev.type == "text":
            await self.bus.publish(create_event("input.text", "text", ev.payload, correlation_id=ev.correlation_id, source="ui"))
        elif ev.type == "voice":
            await self.bus.publish(create_event("input.voice", "voice", ev.payload, correlation_id=ev.correlation_id, source="audio"))
