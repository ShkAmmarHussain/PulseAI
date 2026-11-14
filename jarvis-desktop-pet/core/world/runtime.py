"""Agent runtime: spawns, runs, stops and removes world agents (doc 36 §9, §12).

Rooms follow the 3x3x3 building: ``f{floor}r{row}c{col}``, floor 1 at the
bottom, row 1 at the open front, col 1 on the left. The front row holds the
eight default rooms. Every other room is spare and goes to temp and custom
agents, studio (f2r1c3) first.
"""

from __future__ import annotations

import asyncio
import itertools
import json
from typing import Awaitable, Callable, Dict, Optional, Set

from core.world.state import AgentInfo, TaskInfo, WorldState

DEFAULT_ROOMS: Dict[str, str] = {
    "lobby": "f1r1c1", "archive": "f1r1c2", "watch": "f1r1c3",
    "research": "f2r1c1", "ops": "f2r1c2",
    "planning": "f3r1c1", "director": "f3r1c2", "workshop": "f3r1c3",
}
_ALL_ROOMS = [f"f{f}r{r}c{c}" for f in (1, 2, 3) for r in (1, 2, 3) for c in (1, 2, 3)]
SPARE_ROOMS = ["f2r1c3"] + [x for x in _ALL_ROOMS if x not in DEFAULT_ROOMS.values() and x != "f2r1c3"]


class CapError(Exception):
    """A spawn would go past the agent caps."""


class LoopError(Exception):
    """An agent repeated the same skill call too many times."""


class LoopGuard:
    def __init__(self, limit: int = 3):
        self.limit = limit
        self._last: Dict[str, tuple] = {}

    def check(self, agent_id: str, skill: str, args: dict) -> None:
        key = (skill, json.dumps(args, sort_keys=True, default=str))
        prev, n = self._last.get(agent_id, (None, 0))
        n = n + 1 if prev == key else 1
        self._last[agent_id] = (key, n)
        if n >= self.limit:
            raise LoopError(f"repeated {skill} {self.limit} times with the same input")


class AgentRuntime:
    def __init__(self, state: WorldState, caps: dict):
        self.state = state
        self.max_active_temp = int(caps.get("max_active_temp", 6))
        self.max_temp_per_job = int(caps.get("max_temp_per_job", 3))
        self.max_custom = int(caps.get("max_custom", 6))
        self._running: Dict[str, asyncio.Task] = {}
        self._stopped: Set[str] = set()
        self._ids = itertools.count(1)

    def register_default(self, info: AgentInfo) -> None:
        self.state.add_agent(info)

    def temps(self, job_id: Optional[str] = None):
        return [a for a in self.state.agents.values() if a.kind == "temp" and (job_id is None or a.job_id == job_id)]

    def spawn_temp(self, role: str, job_id: str) -> str:
        if len(self.temps()) >= self.max_active_temp:
            raise CapError(f"already {self.max_active_temp} temporary agents")
        if len(self.temps(job_id)) >= self.max_temp_per_job:
            raise CapError(f"job {job_id} already has {self.max_temp_per_job} temporary agents")
        used = {a.room for a in self.state.agents.values()}
        room = next((r for r in SPARE_ROOMS if r not in used), None)
        if room is None:
            raise CapError("no free room")
        agent_id = f"temp-{role}-{next(self._ids)}"
        self.state.add_agent(AgentInfo(id=agent_id, name=role.title(), role=role, kind="temp", room=room, job_id=job_id, look_seed=agent_id))
        return agent_id

    def free_room(self) -> Optional[str]:
        used = {a.room for a in self.state.agents.values()}
        return next((r for r in SPARE_ROOMS if r not in used), None)

    def customs(self):
        return [a for a in self.state.agents.values() if a.kind == "custom"]

    def spawn_custom(self, name: str, role: str, description: str = "", look_seed: str = "",
                     agent_id: Optional[str] = None, room: Optional[str] = None) -> str:
        """A lasting agent made by the user (doc 36 §9.3). Not counted against temp caps."""
        if len(self.customs()) >= self.max_custom:
            raise CapError(f"already {self.max_custom} custom agents")
        used = {a.room for a in self.state.agents.values()}
        if not room or room in used or room not in SPARE_ROOMS:
            room = self.free_room()
        if room is None:
            raise CapError("no free room")
        agent_id = agent_id or f"custom-{role}-{next(self._ids)}"
        if agent_id in self.state.agents:
            raise ValueError(f"{agent_id} already exists")
        self.state.add_agent(AgentInfo(id=agent_id, name=name, role=role, kind="custom", room=room,
                                       description=description, look_seed=look_seed or agent_id))
        return agent_id

    def keep(self, agent_id: str) -> AgentInfo:
        """Turn a temporary agent into a custom (lasting) one."""
        a = self.state.agents[agent_id]
        if a.kind != "temp":
            raise ValueError(f"{agent_id} is not temporary")
        if len(self.customs()) >= self.max_custom:
            raise CapError(f"already {self.max_custom} custom agents")
        return self.state.update_agent(agent_id, kind="custom", job_id=None, look_seed=a.look_seed or agent_id)

    def remove(self, agent_id: str) -> AgentInfo:
        """Remove a temp or custom agent (defaults can never be removed), stopping its task first."""
        a = self.state.agents[agent_id]
        if a.kind == "default":
            raise ValueError(f"{a.name} is a default agent and cannot be deleted")
        if a.task_id:
            self.stop(a.task_id)
        self.state.remove_agent(agent_id)
        return a

    def dismiss(self, agent_id: str) -> None:
        a = self.state.agents[agent_id]
        if a.kind != "temp":
            raise ValueError(f"{agent_id} is a {a.kind} agent and cannot be dismissed")
        self.state.remove_agent(agent_id)

    async def run(
        self,
        agent_id: str,
        task_id: str,
        worker: Callable[[TaskInfo], Awaitable[str]],
        timeout_s: float,
    ) -> str:
        task = self.state.tasks[task_id]
        self.state.update_task(task_id, state="working", agent_id=agent_id)
        self.state.update_agent(agent_id, state="working", task_id=task_id, label=task.goal)
        fut = asyncio.ensure_future(worker(task))
        self._running[task_id] = fut
        result = ""
        try:
            result = str(await asyncio.wait_for(fut, timeout=timeout_s))
            self.state.update_task(task_id, state="done", result=result)
        except asyncio.TimeoutError:
            self.state.update_task(task_id, state="failed", error=f"timeout after {timeout_s:g}s")
        except asyncio.CancelledError:
            if task_id not in self._stopped:
                raise
            self.state.update_task(task_id, state="stopped")
        except Exception as e:
            self.state.update_task(task_id, state="failed", error=str(e) or type(e).__name__)
        finally:
            self._running.pop(task_id, None)
            self._stopped.discard(task_id)
            if agent_id in self.state.agents:
                self.state.update_agent(agent_id, state="idle", task_id=None, label="")
        return result

    def stop(self, task_id: Optional[str] = None, all: bool = False) -> int:
        targets = list(self._running) if all else [t for t in [task_id] if t in self._running]
        for t in targets:
            self._stopped.add(t)
            self._running[t].cancel()
        return len(targets)
