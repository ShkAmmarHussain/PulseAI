# Base agent class
from typing import Optional
from core.bus import MessageBus, Event


class BaseAgent:
    def __init__(self, name: str, bus: MessageBus):
        self.name = name
        self.bus = bus
        self._running = False
        self.rtm = None
        self.state = None
        self.cfg = {}

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False

    async def handle(self, ev: Event):
        pass
