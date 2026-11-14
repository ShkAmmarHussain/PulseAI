"""Director: the main agent. Routes, staffs, tracks and closes jobs (doc 36 §7).

It never calls a model and never runs a skill. The thinking (``thinker``),
the work (``workers`` by role) and the final answer (``reporter``) are
injected callables, and every one of them goes through the ``Brain`` queue.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Awaitable, Callable, Dict, Optional, Set

from core.bus import create_event
from core.world.brain import Brain
from core.world.plan import validate_plan
from core.world.runtime import AgentRuntime, CapError
from core.world.state import JobInfo, TaskInfo, WorldState

Thinker = Callable[[str], Awaitable[dict]]
Worker = Callable[[TaskInfo, Dict[str, str]], Awaitable[str]]
Reporter = Callable[[str, Dict[str, str]], Awaitable[str]]

_ENDED = ("done", "failed", "skipped", "stopped")


class Director:
    def __init__(
        self,
        bus,
        state: WorldState,
        runtime: AgentRuntime,
        brain: Brain,
        *,
        thinker: Thinker,
        workers: Dict[str, Worker],
        reporter: Reporter,
        caps: dict,
        make_temp_worker: Optional[Callable[[str], Worker]] = None,
    ):
        self.bus, self.state, self.runtime, self.brain = bus, state, runtime, brain
        self.thinker, self.workers, self.reporter, self.caps = thinker, workers, reporter, caps
        self.make_temp_worker = make_temp_worker
        self.timeout_s = float(caps.get("task_timeout_s", 300))
        self._stopping: Set[str] = set()
        self._open: Set[str] = set()
        prev = state.on_change

        def on_change(diff: dict) -> None:
            if prev:
                prev(diff)
            self._publish(diff["topic"], diff["topic"].rsplit(".", 1)[-1], diff, diff.get("job_id"))

        state.on_change = on_change

    # --- bus -------------------------------------------------------------
    def _publish(self, topic: str, etype: str, payload: dict, job_id: Optional[str]) -> None:
        if self.bus is None:
            return
        ev = create_event(topic, etype, payload, correlation_id=job_id, source="director")
        asyncio.get_running_loop().create_task(self.bus.publish(ev))

    def _close(self, job_id: str, status: str, answer: str) -> JobInfo:
        job = self.state.close_job(job_id, status, answer)
        self._open.discard(job_id)
        if not self._open:
            self._show("director", False)
        self._stopping.discard(job_id)
        if answer:
            self._publish("ui.chat", "chat", {"role": "assistant", "text": answer}, job_id)
        return job

    # --- helpers ---------------------------------------------------------
    def _known_roles(self) -> Set[str]:
        return {a.role for a in self.state.agents.values() if a.kind != "temp"}

    def _agent_for(self, role: str, job_id: str, busy: Set[str]) -> Optional[str]:
        cands = [a for a in self.state.agents.values() if a.role == role and (a.kind != "temp" or a.job_id == job_id)]
        free = [a for a in cands if a.id not in busy]
        pick = free or cands
        return pick[0].id if pick else None

    def _show(self, role: str, working: bool, label: str = "", task_id=None) -> None:
        """Make the default agent behind a Director step visible in the world
        (the Thinker while planning, the Reporter while answering, Pip routing)."""
        a = next((x for x in self.state.agents.values() if x.role == role and x.kind == "default"), None)
        if a is not None:
            self.state.update_agent(a.id, state="working" if working else "idle", label=label if working else "", task_id=None)

    async def _think(self, text: str, job_id: str, priority: int):
        self._show("thinker", True, "planning")
        try:
            return await self.brain.submit(lambda: self.thinker(text), job_id=job_id, priority=priority)
        finally:
            self._show("thinker", False)

    def _end_job(self, job_id: str, status: str, answer: str) -> JobInfo:
        for t in self.state.tasks.values():
            if t.job_id == job_id and t.state not in _ENDED:
                self.state.update_task(t.id, state="stopped" if status == "stopped" else "skipped")
        for a in list(self.runtime.temps(job_id)):
            self.runtime.dismiss(a.id)
        return self._close(job_id, status, answer)

    # --- the job ---------------------------------------------------------
    async def handle(self, text: str, job_id: Optional[str] = None, priority: int = 0) -> JobInfo:
        job_id = job_id or uuid.uuid4().hex[:12]
        self.state.open_job(job_id, text)
        self._open.add(job_id)
        self._show("director", True, "routing")
        try:
            return await self._run_job(text, job_id, priority)
        except asyncio.CancelledError:
            if job_id in self._stopping:
                return self._end_job(job_id, "stopped", "Stopped. Nothing else will run for this request.")
            raise

    async def _run_job(self, text: str, job_id: str, priority: int) -> JobInfo:
        plan = await self._think(text, job_id, priority)
        order, errors = validate_plan(plan, self._known_roles(), self.caps)
        if errors:
            plan = await self._think(f"{text}\n\nYour last plan was invalid: {'; '.join(errors)}", job_id, priority)
            order, errors = validate_plan(plan, self._known_roles(), self.caps)
        if errors:
            return self._end_job(job_id, "failed", f"I could not plan that: {errors[0]}")

        try:
            for na in plan.get("new_agents") or []:
                self.runtime.spawn_temp(str(na["role"]), job_id)
        except CapError as e:
            return self._end_job(job_id, "failed", f"I could not staff that: {e}")

        ids = {t["id"]: f"{job_id}.{t['id']}" for t in order}
        for t in order:
            self.state.add_task(TaskInfo(
                id=ids[t["id"]], job_id=job_id, role=str(t["role"]), goal=str(t.get("goal", "")),
                needs=[ids[d] for d in t.get("needs") or []],
                params={"steps": t["steps"]} if t.get("steps") else {},
            ))

        results: Dict[str, str] = {}
        running: Dict[asyncio.Task, str] = {}
        busy: Set[str] = set()
        while job_id not in self._stopping:
            pending = [self.state.tasks[ids[t["id"]]] for t in order if self.state.tasks[ids[t["id"]]].state == "queued"]
            for task in pending:
                needs = [self.state.tasks[n] for n in task.needs]
                if any(n.state in ("failed", "skipped", "stopped") for n in needs):
                    self.state.update_task(task.id, state="skipped", error="a task it needed did not finish")
                    continue
                if not all(n.state == "done" for n in needs):
                    continue
                agent = self._agent_for(task.role, job_id, busy)
                worker = self.workers.get(task.role)
                if worker is None and self.make_temp_worker is not None and agent is not None and self.state.agents[agent].kind == "temp":
                    worker = self.workers[task.role] = self.make_temp_worker(task.role)
                if agent is None or worker is None:
                    self.state.update_task(task.id, state="failed", error=f"no agent for role {task.role}")
                    continue
                if agent in busy:
                    continue
                needed = {n.id.split(".", 1)[1]: n.result for n in needs}
                busy.add(agent)
                run = asyncio.ensure_future(self.runtime.run(agent, task.id, self._wrap(worker, needed, job_id, priority), self.timeout_s))
                running[run] = agent
            if not running:
                if any(self.state.tasks[i].state == "queued" for i in ids.values()):
                    continue  # skips just cascaded; re-scan
                break
            done, _ = await asyncio.wait(list(running), return_when=asyncio.FIRST_COMPLETED)
            for r in done:
                busy.discard(running.pop(r))
        if running:
            await asyncio.gather(*running, return_exceptions=True)
        if job_id in self._stopping:
            return self._end_job(job_id, "stopped", "Stopped. Nothing else will run for this request.")

        for plan_id, tid in ids.items():
            if self.state.tasks[tid].state == "done":
                results[plan_id] = self.state.tasks[tid].result
        self._show("reporter", True, "writing the answer")
        try:
            answer = await self.brain.submit(lambda: self.reporter(text, results), job_id=job_id, priority=priority)
        finally:
            self._show("reporter", False)
        failed = any(self.state.tasks[i].state != "done" for i in ids.values())
        return self._end_job(job_id, "partial" if failed else "done", str(answer))

    def _wrap(self, worker: Worker, needed: Dict[str, str], job_id: str, priority: int):
        async def run(task: TaskInfo) -> str:
            return await self.brain.submit(lambda: worker(task, needed), job_id=job_id, priority=priority)
        return run

    async def stop_all(self) -> None:
        self._stopping |= set(self._open)
        self.runtime.stop(all=True)
        self.brain.cancel_all()
        await asyncio.sleep(0)
