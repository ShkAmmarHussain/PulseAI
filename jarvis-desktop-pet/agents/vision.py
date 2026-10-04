import logging

from agents.base import BaseAgent
from core.bus import Event, create_event

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("vision", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("vision.request", self.handle)

    async def handle(self, ev: Event):
        if ev.type not in ("request", "describe"):
            return
        payload = ev.payload
        query = str(payload.get("query") or payload.get("text") or "").strip()
        from skills.screen_vision import describe

        try:
            text = await describe(self.cfg, query, payload.get("region"), rtm=self.rtm)
            ok = True
        except Exception as e:
            logger.exception("vision request failed")
            text = f"Screen vision failed: {e}"
            ok = False
        await self.bus.publish(
            create_event(
                "tool.result",
                "tool_result",
                {"ok": ok, "summary": text, "steps": [{"action": "vision_describe", "risk": 0}]},
                correlation_id=ev.correlation_id,
            )
        )
