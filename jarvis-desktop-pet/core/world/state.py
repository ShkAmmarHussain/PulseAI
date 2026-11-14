"""World state: the single source of truth for agents, jobs and tasks (doc 36 §6).

Every mutation bumps ``seq`` by one and reports a diff dict to ``on_change``.
The UI rebuilds the same state from ``snapshot()`` plus the later diffs
(``apply_diff``), and asks for a fresh snapshot when it sees a seq gap.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class AgentInfo:
    id: str
    name: str
    role: str
    kind: str  # default | custom | temp
    room: str
    state: str = "idle"
    task_id: Optional[str] = None
    label: str = ""
    job_id: Optional[str] = None
    description: str = ""
    look_seed: str = ""


@dataclass
class TaskInfo:
    id: str
    job_id: str
    role: str
    goal: str
    needs: List[str] = field(default_factory=list)
    agent_id: Optional[str] = None
    state: str = "queued"  # queued | working | done | failed | skipped | stopped
    result: str = ""
    error: str = ""
    params: dict = field(default_factory=dict)


@dataclass
class JobInfo:
    id: str
    text: str
    status: str = "open"  # open | done | partial | failed | stopped
    answer: str = ""
    task_ids: List[str] = field(default_factory=list)


def empty_snapshot() -> dict:
    return {"seq": 0, "agents": {}, "jobs": {}, "tasks": {}}


def apply_diff(snapshot: dict, diff: dict) -> dict:
    """Pure: returns a new snapshot with ``diff`` applied."""
    s = copy.deepcopy(snapshot)
    t = diff["topic"]
    if t in ("world.agent.added", "world.agent.updated"):
        s["agents"][diff["agent"]["id"]] = copy.deepcopy(diff["agent"])
    elif t == "world.agent.removed":
        s["agents"].pop(diff["agent_id"], None)
    elif t in ("world.job.opened", "world.job.closed", "world.job.updated"):
        s["jobs"][diff["job"]["id"]] = copy.deepcopy(diff["job"])
    elif t in ("world.task.created", "world.task.updated"):
        task = copy.deepcopy(diff["task"])
        s["tasks"][task["id"]] = task
        if t == "world.task.created" and task["job_id"] in s["jobs"]:
            ids = s["jobs"][task["job_id"]]["task_ids"]
            if task["id"] not in ids:
                ids.append(task["id"])
    else:
        raise ValueError(f"unknown diff topic: {t}")
    s["seq"] = diff["seq"]
    return s


class WorldState:
    def __init__(self, on_change: Optional[Callable[[dict], None]] = None):
        self.on_change = on_change
        self.seq = 0
        self.agents: Dict[str, AgentInfo] = {}
        self.jobs: Dict[str, JobInfo] = {}
        self.tasks: Dict[str, TaskInfo] = {}

    def _emit(self, topic: str, **payload) -> None:
        self.seq += 1
        diff = {"topic": topic, "seq": self.seq, **payload}
        if self.on_change:
            self.on_change(diff)

    # agents
    def add_agent(self, info: AgentInfo) -> None:
        self.agents[info.id] = info
        self._emit("world.agent.added", agent=asdict(info))

    def update_agent(self, agent_id: str, **fields) -> AgentInfo:
        a = self.agents[agent_id]
        for k, v in fields.items():
            setattr(a, k, v)
        self._emit("world.agent.updated", agent=asdict(a))
        return a

    def remove_agent(self, agent_id: str) -> None:
        del self.agents[agent_id]
        self._emit("world.agent.removed", agent_id=agent_id)

    # jobs
    def open_job(self, job_id: str, text: str) -> JobInfo:
        j = JobInfo(id=job_id, text=text)
        self.jobs[job_id] = j
        self._emit("world.job.opened", job=asdict(j), job_id=job_id)
        return j

    def close_job(self, job_id: str, status: str, answer: str = "") -> JobInfo:
        j = self.jobs[job_id]
        j.status, j.answer = status, answer
        self._emit("world.job.closed", job=asdict(j), job_id=job_id)
        return j

    # tasks
    def add_task(self, task: TaskInfo) -> None:
        self.tasks[task.id] = task
        job = self.jobs.get(task.job_id)
        if job is not None and task.id not in job.task_ids:
            job.task_ids.append(task.id)
        self._emit("world.task.created", task=asdict(task), job_id=task.job_id, task_id=task.id)

    def update_task(self, task_id: str, **fields) -> TaskInfo:
        t = self.tasks[task_id]
        for k, v in fields.items():
            setattr(t, k, v)
        self._emit("world.task.updated", task=asdict(t), job_id=t.job_id, task_id=t.id)
        return t

    def snapshot(self) -> dict:
        return {
            "seq": self.seq,
            "agents": {k: asdict(v) for k, v in self.agents.items()},
            "jobs": {k: asdict(v) for k, v in self.jobs.items()},
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
        }
