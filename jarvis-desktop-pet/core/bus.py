import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Awaitable
from collections import defaultdict

logger = logging.getLogger("bus")

TOPIC_ALL = "#"


@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    ttl_ms: Optional[int] = None
    source: Optional[str] = None
    target: Optional[str] = None
    priority: int = 5


Handler = Callable[[Event], Awaitable[None]]


class MessageBus:
    def __init__(self, max_queue_size: int = 1000, default_ttl_ms: int = 60000):
        self._subs: Dict[str, List[Handler]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue(maxsize=max_queue_size))
        self._default_ttl_ms = default_ttl_ms
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    def subscribe(self, topic: str, handler: Handler):
        self._subs[topic].append(handler)
        if self._running and topic not in self._tasks:
            self._tasks[topic] = asyncio.get_event_loop().create_task(self._dispatch(topic))

    async def publish(self, event: Event):
        if event.ttl_ms is None:
            event.ttl_ms = self._default_ttl_ms
        if self._subs.get(event.topic):
            await self._queues[event.topic].put(event)
        if self._subs.get(TOPIC_ALL):
            await self._queues[TOPIC_ALL].put(event)

    async def _dispatch(self, topic: str):
        q = self._queues[topic]
        while True:
            ev = await q.get()
            try:
                if ev.ttl_ms is not None and (time.time() - ev.timestamp) * 1000 > ev.ttl_ms:
                    continue
                for h in list(self._subs.get(topic, [])):
                    try:
                        await h(ev)
                    except Exception:
                        logger.exception("handler error on %s", topic)
            finally:
                q.task_done()

    def start(self):
        self._running = True
        for topic in list(self._subs.keys()):
            if topic not in self._tasks:
                self._tasks[topic] = asyncio.get_event_loop().create_task(self._dispatch(topic))

    async def stop(self):
        self._running = False
        for t in self._tasks.values():
            t.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()


def create_event(topic: str, etype: str, payload: Dict[str, Any], **kw) -> Event:
    return Event(topic=topic, type=etype, payload=payload, **kw)