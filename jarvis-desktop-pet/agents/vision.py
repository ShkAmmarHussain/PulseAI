from agents.base import BaseAgent
from core.bus import Event


class VisionAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("vision", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("vision.request", self.handle)

    async def handle(self, ev: Event):
        pass
