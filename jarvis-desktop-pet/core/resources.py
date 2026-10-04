import asyncio
import time
from enum import Enum
from typing import Optional, Dict, Any


class LoadState(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    VISION_ACTIVE = "vision_active"
    RESTORING = "restoring"
    UNLOADING = "unloading"
    ERROR = "error"


class ResourceTransitionManager:
    def __init__(self, vision_timeout_ms: int = 20000, unload_idle_ms: int = 60000, cooldown_ms: int = 2000):
        self._state = LoadState.IDLE
        self._lock = asyncio.Lock()
        self._vision_loaded_at: Optional[float] = None
        self._vision_task_id: Optional[str] = None
        self._vision_timeout_ms = vision_timeout_ms
        self._unload_idle_ms = unload_idle_ms
        self._cooldown_ms = cooldown_ms
        self._last_unload_at: float = 0.0
        self._last_load_at: float = 0.0

    def _can_load_unlocked(self) -> bool:
        now = time.time()
        if now - self._last_unload_at < self._cooldown_ms / 1000.0:
            return False
        if self._state != LoadState.IDLE:
            return False
        return True

    async def can_load_vision(self) -> bool:
        async with self._lock:
            return self._can_load_unlocked()

    async def acquire_vision(self, task_id: str) -> bool:
        # NOTE: _can_load_unlocked must not go through can_load_vision() here -
        # asyncio.Lock is not reentrant and that path deadlocked
        async with self._lock:
            if not self._can_load_unlocked():
                return False
            self._state = LoadState.LOADING
            self._last_load_at = time.time()
            self._vision_task_id = task_id
            self._vision_loaded_at = time.time()
            self._state = LoadState.VISION_ACTIVE
            return True

    async def release_vision(self, task_id: str, force: bool = False) -> bool:
        async with self._lock:
            now = time.time()
            if self._state != LoadState.VISION_ACTIVE and not force:
                return True
            self._state = LoadState.UNLOADING
            self._last_unload_at = now
            self._vision_task_id = None
            self._vision_loaded_at = None
            self._state = LoadState.IDLE
            return True

    def should_force_unload(self) -> bool:
        if self._state != LoadState.VISION_ACTIVE or self._vision_loaded_at is None:
            return False
        return (time.time() - self._vision_loaded_at) * 1000 > self._vision_timeout_ms

    @property
    def state(self) -> LoadState:
        return self._state
