"""Brain: the only way world agents reach a model (doc 36 §12).

Calls wait in one priority queue (0 = interactive, 1 = background, FIFO
within a priority) and run on ``concurrency`` workers: 1 for local LM Studio,
more for cloud. ``cancel_job`` drops a job's queued calls and cancels its
running ones, which is what "Stop all" relies on.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional, Set


@dataclass(eq=False)
class _Call:
    fn: Callable[[], Awaitable]
    job_id: str
    future: asyncio.Future
    waited: bool = False
    running: Optional[asyncio.Task] = field(default=None, repr=False)


class Brain:
    def __init__(self, concurrency: int = 1):
        self.concurrency = max(1, int(concurrency))
        self.on_wait: Optional[Callable[[str, bool], None]] = None
        self._queue: Optional[asyncio.PriorityQueue] = None
        self._workers: List[asyncio.Task] = []
        self._counter = itertools.count()
        self._queued: List[_Call] = []
        self._running: Set[_Call] = set()

    def _ensure_workers(self) -> None:
        if self._queue is None:
            self._queue = asyncio.PriorityQueue()
        self._workers = [w for w in self._workers if not w.done()]
        while len(self._workers) < self.concurrency:
            self._workers.append(asyncio.get_running_loop().create_task(self._work()))

    async def submit(self, fn: Callable[[], Awaitable], *, job_id: str, priority: int = 1):
        self._ensure_workers()
        call = _Call(fn=fn, job_id=job_id, future=asyncio.get_running_loop().create_future())
        busy = len(self._running) >= self.concurrency or bool(self._queued)
        self._queued.append(call)
        if busy:
            call.waited = True
            self._notify(job_id, True)
        self._queue.put_nowait((priority, next(self._counter), call))
        return await call.future

    def _notify(self, job_id: str, waiting: bool) -> None:
        if self.on_wait:
            try:
                self.on_wait(job_id, waiting)
            except Exception:
                pass

    async def _work(self) -> None:
        while True:
            _, _, call = await self._queue.get()
            if call in self._queued:
                self._queued.remove(call)
            if call.future.done():
                continue
            if call.waited:
                self._notify(call.job_id, False)
            self._running.add(call)
            call.running = asyncio.ensure_future(call.fn())
            try:
                result = await asyncio.shield(call.running)
            except asyncio.CancelledError:
                if call.running.cancelled():
                    if not call.future.done():
                        call.future.cancel()
                    continue
                raise
            except Exception as e:  # propagate to the caller, keep serving
                if not call.future.done():
                    call.future.set_exception(e)
            else:
                if not call.future.done():
                    call.future.set_result(result)
            finally:
                self._running.discard(call)

    def waiting(self, job_id: Optional[str] = None) -> int:
        return sum(1 for c in self._queued if not c.future.done() and (job_id is None or c.job_id == job_id))

    def _cancel(self, match: Callable[[_Call], bool]) -> int:
        n = 0
        for c in list(self._queued):
            if match(c) and not c.future.done():
                c.future.cancel()
                self._queued.remove(c)
                n += 1
        for c in list(self._running):
            if match(c) and c.running and not c.running.done():
                c.running.cancel()
                if not c.future.done():
                    c.future.cancel()
                n += 1
        return n

    def cancel_job(self, job_id: str) -> int:
        return self._cancel(lambda c: c.job_id == job_id)

    def cancel_all(self) -> int:
        return self._cancel(lambda c: True)
