import asyncio
import json
import logging
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger("model_lifecycle")

_INSTANCE: "ModelLifecycle | None" = None


def set_lifecycle(lc: "ModelLifecycle | None") -> None:
    global _INSTANCE
    _INSTANCE = lc


def get_lifecycle() -> "ModelLifecycle | None":
    return _INSTANCE


class ModelLifecycle:
    """Loads models on demand for the task at hand and offloads idle ones,
    using LM Studio's REST API (POST /api/v1/models/load, /api/v1/models/unload,
    GET /api/v0/models for per-model state)."""

    def __init__(self, lm_cfg: dict, rm_cfg: dict):
        base = str(lm_cfg.get("base_url") or "http://localhost:1234/v1").strip().rstrip("/")
        if base.endswith("/v1"):
            base = base[: -len("/v1")].rstrip("/")
        self.base = base or "http://localhost:1234"
        self.api_key = lm_cfg.get("api_key") or "lm-studio"
        self.auto_manage = bool(rm_cfg.get("auto_manage", True))
        self.unload_idle_ms = int(rm_cfg.get("unload_idle_ms", 60000))
        self.cooldown_ms = int(rm_cfg.get("cooldown_ms", 2000))
        self.max_concurrent = max(1, int(rm_cfg.get("max_concurrent_models", 2)))
        self._last_used: dict = {}
        self._in_use: dict = {}
        self._lock = threading.RLock()
        self._last_unload_at = 0.0
        self._started_at = time.time()
        self.on_change = None  # async fn(snapshot) - set by the app
        self._task: asyncio.Task | None = None
        set_lifecycle(self)

    # ---------- config refresh (settings saved) ----------
    def update_config(self, lm_cfg: dict, rm_cfg: dict) -> None:
        with self._lock:
            base = str(lm_cfg.get("base_url") or self.base).strip().rstrip("/")
            if base.endswith("/v1"):
                base = base[: -len("/v1")].rstrip("/")
            self.base = base or self.base
            self.api_key = lm_cfg.get("api_key") or self.api_key
            self.auto_manage = bool(rm_cfg.get("auto_manage", True))
            self.unload_idle_ms = int(rm_cfg.get("unload_idle_ms", self.unload_idle_ms))
            self.cooldown_ms = int(rm_cfg.get("cooldown_ms", self.cooldown_ms))
            self.max_concurrent = max(1, int(rm_cfg.get("max_concurrent_models", self.max_concurrent)))

    # ---------- HTTP ----------
    def _http(self, method: str, path: str, body: dict | None = None, timeout: float = 30.0) -> dict | None:
        url = self.base + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            logger.debug("LM Studio %s %s -> HTTP %s %s", method, path, e.code, detail)
            return {"__error__": f"HTTP {e.code}", "__detail__": detail}
        except Exception as e:
            logger.debug("LM Studio %s %s failed: %s", method, path, e)
            return {"__error__": str(e)}

    def list_states(self) -> dict:
        """{model_id: 'loaded' | 'not-loaded' | ...} from LM Studio."""
        res = self._http("GET", "/api/v0/models", timeout=6.0)
        if not res or "__error__" in res:
            return {}
        out = {}
        for m in res.get("data") or []:
            mid = m.get("id")
            if mid:
                out[mid] = m.get("state") or "unknown"
        return out

    def load(self, model: str) -> bool:
        # a 7B/13B model can legitimately take a while to come up
        res = self._http("POST", "/api/v1/models/load", {"model": model}, timeout=90.0)
        ok = bool(res) and "__error__" not in res and res.get("status") in (None, "loaded")
        if ok:
            logger.info("model loaded: %s", model)
        else:
            logger.warning("model load failed: %s -> %s", model, res)
        return ok

    def unload(self, instance_id: str) -> bool:
        res = self._http("POST", "/api/v1/models/unload", {"instance_id": instance_id})
        ok = bool(res) and "__error__" not in res
        if ok:
            logger.info("model unloaded: %s", instance_id)
        else:
            logger.debug("model unload skipped/failed: %s -> %s", instance_id, res)
        return ok

    # ---------- ensure on demand (called from LLM threads) ----------
    def before_chat(self, model: str) -> None:
        if not model:
            return
        with self._lock:
            try:
                self._ensure(model)
            except Exception:
                logger.exception("ensure model failed (chat continues): %s", model)
            self._last_used[model] = time.time()
            self._in_use[model] = self._in_use.get(model, 0) + 1

    def after_chat(self, model: str) -> None:
        if not model:
            return
        with self._lock:
            self._in_use[model] = max(0, self._in_use.get(model, 0) - 1)
            self._last_used[model] = time.time()

    def _ensure(self, model: str) -> None:
        if not self.auto_manage:
            return
        states = self.list_states()
        if not states:
            return  # LM Studio unreachable / old - OpenAI endpoint auto-load is the fallback
        if states.get(model) == "loaded":
            return
        # make room: unload least-recently-used, idle, not-in-use models if over budget
        loaded = [m for m, s in states.items() if s == "loaded" and m != model and self._in_use.get(m, 0) == 0]
        overflow = (len(loaded) + 1) - self.max_concurrent
        if overflow > 0:
            loaded.sort(key=lambda m: self._last_used.get(m, 0.0))  # LRU first
            freed = 0
            for victim in loaded:
                if freed >= overflow:
                    break
                if self.unload(victim):
                    self._last_unload_at = time.time()
                    freed += 1
        self.load(model)

    # ---------- idle sweep ----------
    def sweep_once(self) -> list:
        """Unload models idle longer than unload_idle_ms. Returns unloaded ids."""
        if not self.auto_manage:
            return []
        with self._lock:
            now = time.time()
            if (now - self._last_unload_at) * 1000 < self.cooldown_ms:
                return []
            states = self.list_states()
            if not states:
                return []
            unloaded = []
            for mid, st in states.items():
                if st != "loaded":
                    continue
                if self._in_use.get(mid, 0) > 0:
                    continue
                last = self._last_used.get(mid, self._started_at)
                if (now - last) * 1000 >= self.unload_idle_ms and self.unload(mid):
                    self._last_unload_at = now
                    unloaded.append(mid)
            return unloaded

    def snapshot(self) -> dict:
        with self._lock:
            states = self.list_states()
            now = time.time()
            loaded, not_loaded = [], []
            for mid, st in sorted(states.items()):
                if st == "loaded":
                    last = self._last_used.get(mid, self._started_at)
                    loaded.append(
                        {
                            "id": mid,
                            "idle_s": round(now - last, 1),
                            "in_use": int(self._in_use.get(mid, 0)),
                        }
                    )
                else:
                    not_loaded.append(mid)
            return {
                "auto_manage": self.auto_manage,
                "unload_idle_s": round(self.unload_idle_ms / 1000),
                "max_concurrent": self.max_concurrent,
                "loaded": loaded,
                "not_loaded": not_loaded,
                "lm_base": self.base,
            }

    # ---------- background sweeper ----------
    async def run(self, interval_s: float = 5.0) -> None:
        logger.info(
            "model lifecycle started (auto_manage=%s, idle=%ss, max_concurrent=%s)",
            self.auto_manage,
            self.unload_idle_ms // 1000,
            self.max_concurrent,
        )
        while True:
            try:
                before = self.list_states()
                unloaded = await asyncio.to_thread(self.sweep_once)
                if unloaded:
                    logger.info("idle sweep unloaded: %s", ", ".join(unloaded))
                    await self._notify()
                elif before != self.list_states():
                    await self._notify()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("lifecycle sweep failed")
            await asyncio.sleep(interval_s)

    async def _notify(self) -> None:
        if self.on_change:
            try:
                await self.on_change(self.snapshot())
            except Exception:
                logger.exception("rm_state notify failed")

    async def notify_now(self) -> None:
        await self._notify()

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
