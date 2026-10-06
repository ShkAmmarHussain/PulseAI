"""Async task / reminder engine (spec 32, section 3.1).

Reminders, one-shot timers and recurring automations run on a single asyncio
ticker (0.5s resolution) and persist to ``data/tasks.json`` so active timers
survive a backend restart. Every state change broadcasts ``tasks.updated``
for the Activity pane countdown pills; expiry plays the chime + toast and
speaks the reminder on the pet.
"""

import asyncio
import json
import logging
import os
import time
import uuid

from core.bus import create_event
from core.config import DATA_DIR

logger = logging.getLogger(__name__)

TASKS_FILE = DATA_DIR / "tasks.json"
MAX_PAST = 50

STATUS_ACTIVE = "active"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"
STATUS_MISSED = "missed"


# ---------- recurring actions (built-ins; register more at runtime) ----------


def _memory_report() -> str:
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return "System memory check failed."
    used_gb = (stat.ullTotalPhys - stat.ullAvailPhys) / (1024 ** 3)
    total_gb = stat.ullTotalPhys / (1024 ** 3)
    return f"System memory: {stat.dwMemoryLoad}% used ({used_gb:.1f} of {total_gb:.1f} GB)."


DEFAULT_HANDLERS = {"system_memory": _memory_report}


# ---------- store helpers ----------


def _now() -> float:
    return time.time()


def _load() -> dict:
    try:
        if not TASKS_FILE.exists():
            return {"tasks": []}
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
            return {"tasks": []}
        return data
    except Exception:
        logger.exception("tasks store unreadable (%s)", TASKS_FILE)
        return {"tasks": []}


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tasks = data.get("tasks", [])
    if len(tasks) > 200:
        active = [t for t in tasks if t.get("status") == STATUS_ACTIVE]
        rest = [t for t in tasks if t.get("status") != STATUS_ACTIVE]
        data = {"tasks": active + rest[:200 - len(active)]}
    tmp = TASKS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TASKS_FILE)


# ---------- manager ----------


class TaskManager:
    def __init__(self, bus=None):
        self.bus = bus
        self._tasks: list[dict] = []
        self._ticker: asyncio.Task | None = None
        self._handlers = dict(DEFAULT_HANDLERS)

    # -- lifecycle --

    async def start(self):
        if self._ticker is not None:
            return
        await asyncio.to_thread(self._load_into_memory)
        self._ticker = asyncio.create_task(self._run())
        logger.info("task manager running (%d persisted task(s))", len(self._tasks))

    async def stop(self):
        if self._ticker:
            self._ticker.cancel()
            self._ticker = None

    def _load_into_memory(self):
        data = _load()
        self._tasks = data.get("tasks", [])
        changed = False
        now = _now()
        for t in self._tasks:
            if t.get("status") == STATUS_ACTIVE:
                if t.get("type") == "recurring":
                    if (t.get("next_due") or 0) < now:
                        t["next_due"] = now + float(t.get("interval_seconds") or 60)
                        changed = True
                elif float(t.get("due_timestamp") or 0) < now:
                    # expired while we were away: record it, never chime late
                    t["status"] = STATUS_MISSED
                    changed = True
        if changed:
            _save({"tasks": self._tasks})

    # -- public API --

    def snapshot(self) -> dict:
        return {"tasks": [dict(t) for t in self._tasks]}

    def active(self) -> list:
        return [dict(t) for t in self._tasks if t.get("status") == STATUS_ACTIVE]

    def create_reminder(self, title: str, seconds: float = None, due_timestamp: float = None,
                        kind: str = "reminder") -> dict:
        now = _now()
        due = float(due_timestamp) if due_timestamp else now + max(0.1, float(seconds or 0))
        task = {
            "id": "tsk_" + uuid.uuid4().hex[:8],
            "type": "reminder",
            "kind": kind,
            "title": str(title or "Reminder")[:140],
            "created_at": now,
            "due_timestamp": due,
            "status": STATUS_ACTIVE,
        }
        self._tasks.insert(0, task)
        self._save_now()
        return dict(task)

    def create_recurring(self, title: str, interval_seconds: float, action: str) -> dict:
        task = {
            "id": "tsk_" + uuid.uuid4().hex[:8],
            "type": "recurring",
            "kind": "recurring",
            "title": str(title or "Recurring task")[:140],
            "created_at": _now(),
            "interval_seconds": max(5.0, float(interval_seconds)),
            "action": action if action in self._handlers else "system_memory",
            "next_due": _now() + max(5.0, float(interval_seconds)),
            "status": STATUS_ACTIVE,
        }
        self._tasks.insert(0, task)
        self._save_now()
        return dict(task)

    def cancel(self, task_id: str) -> bool:
        for t in self._tasks:
            if t.get("id") == task_id and t.get("status") == STATUS_ACTIVE:
                t["status"] = STATUS_CANCELLED
                self._save_now()
                return True
        return False

    def cancel_kind(self, kind: str) -> int:
        n = 0
        for t in self._tasks:
            if t.get("status") == STATUS_ACTIVE and t.get("kind") == kind:
                t["status"] = STATUS_CANCELLED
                n += 1
        if n:
            self._save_now()
        return n

    def register_handler(self, name: str, fn) -> None:
        self._handlers[name] = fn

    # -- persistence + broadcast --

    def _save_now(self):
        try:
            _save({"tasks": self._tasks})
        except Exception:
            logger.exception("task persist failed")

    async def _broadcast(self):
        if self.bus is None:
            return
        try:
            await self.bus.publish(create_event("tasks.updated", "tasks.updated", self.snapshot()))
        except Exception:
            logger.exception("tasks.updated broadcast failed")

    async def notify(self):
        """Public alias: re-broadcast the task list (e.g. right after create)."""
        await self._broadcast()

    # -- ticker --

    async def _run(self):
        while True:
            try:
                await asyncio.sleep(0.5)
                now = _now()
                fired = [t for t in self._tasks
                         if t.get("status") == STATUS_ACTIVE and t.get("type") == "reminder"
                         and float(t.get("due_timestamp") or 0) <= now]
                due_rec = [t for t in self._tasks
                           if t.get("status") == STATUS_ACTIVE and t.get("type") == "recurring"
                           and float(t.get("next_due") or 0) <= now]
                for t in fired:
                    await self._fire(t)
                for t in due_rec:
                    await self._run_recurring(t)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("task ticker iteration failed")

    async def _fire(self, task: dict):
        task["status"] = STATUS_DONE
        task["fired_at"] = _now()
        self._save_now()
        title = task.get("title") or "Reminder"
        logger.info("task fired: %s (%s)", title, task.get("id"))
        await self._broadcast()

        from skills import notify

        try:
            await asyncio.to_thread(notify.toast, "Jarvis reminder", title)
            await asyncio.to_thread(notify.chime)
        except Exception:
            logger.exception("task alert failed")
        if self.bus is None:
            return
        # pet bubble + spoken line + main-window chat entry (audible alert)
        text = f"Reminder: {title}"
        await self.bus.publish(create_event("ui.chat", "chat", {"role": "assistant", "text": text}))
        await self.bus.publish(create_event("voice.say", "say", {"text": text}))
        await self.bus.publish(create_event("task.fired", "task_fired", {"task": dict(task)}))

    async def _run_recurring(self, task: dict):
        task["next_due"] = _now() + float(task.get("interval_seconds") or 60)
        task["runs"] = int(task.get("runs") or 0) + 1
        self._save_now()
        fn = self._handlers.get(task.get("action"))
        if fn is None:
            return
        try:
            result = await asyncio.to_thread(fn)
        except Exception as e:
            logger.exception("recurring action failed (%s)", task.get("action"))
            result = f"Recurring task failed: {e}"
        if self.bus is None:
            return
        await self.bus.publish(
            create_event(
                "ui.chat", "chat",
                {"role": "system", "text": f"{task.get('title')}: {result}"},
            )
        )
        await self._broadcast()


# ---------- module-level singleton (shared by app, WS bridge and fast path) ----------

_manager: TaskManager | None = None


def get_task_manager(bus=None) -> TaskManager:
    global _manager
    if _manager is None:
        _manager = TaskManager(bus)
    elif bus is not None and _manager.bus is None:
        _manager.bus = bus
    return _manager


def reset_task_manager() -> None:
    """Test hook: drop the singleton so the next get_task_manager() rebuilds."""
    global _manager
    _manager = None
