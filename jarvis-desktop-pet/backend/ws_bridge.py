import asyncio
import json
import logging
import sys
import time

import yaml
from aiohttp import web

from core.bus import create_event
from core.config import CONFIG_DIR

logger = logging.getLogger("ws_bridge")


def _read_yaml(name: str) -> dict:
    p = CONFIG_DIR / name
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(name: str, data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    p = CONFIG_DIR / name
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def get_settings() -> dict:
    return {
        "config": _read_yaml("config.yaml"),
        "agents": _read_yaml("agents.yaml"),
        "permissions": _read_yaml("permissions.yaml"),
        "personality": _read_yaml("personality.yaml"),
        "skills": _read_yaml("skills.yaml"),
    }


def save_settings(payload: dict) -> dict:
    allowed = {"config", "agents", "permissions", "personality", "skills"}
    for key, value in payload.items():
        if key in allowed and isinstance(value, dict):
            _write_yaml(f"{key}.yaml", value)
    return get_settings()


class WSBridge:
    def __init__(self, bus, voice=None):
        self.bus = bus
        self.voice = voice
        self.clients: set = set()

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        logger.info("ws connected from %s (clients=%d)", request.remote, len(self.clients))

        async def _heartbeat():
            loop = asyncio.get_event_loop()
            prev = loop.time()
            while True:
                await asyncio.sleep(2.0)
                now = loop.time()
                drift = now - prev - 2.0
                if drift > 0.5:
                    logger.warning("event-loop lag: %.2fs", drift)
                prev = now

        hb = None
        try:
            hb = asyncio.ensure_future(_heartbeat())
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue
                    try:
                        logger.info("recv %s", data.get("type"))
                        await self._dispatch(ws, data)
                    except Exception:
                        logger.exception("dispatch failed: %s", str(data.get("type")))
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            if hb is not None:
                hb.cancel()
            self.clients.discard(ws)
            logger.info("ws closed from %s (clients=%d)", request.remote, len(self.clients))
        return ws

    async def _dispatch(self, ws, data):
        et = data.get("type")
        payload = data.get("payload", {})
        cid = data.get("correlation_id")
        if et == "text_input":
            await self.bus.publish(
                create_event("ui.input.text", "text", {"text": payload.get("text", "")}, correlation_id=cid)
            )
        elif et == "approval_response":
            await self.bus.publish(
                create_event("ui.approval.response", "approval_response", payload, correlation_id=cid)
            )
        elif et == "file_ingest":
            from pathlib import Path as _P

            from skills.screen_vision import is_image_path

            raw = payload.get("paths") or []
            if isinstance(raw, str):
                raw = [raw]
            items = []
            for s in list(raw)[:10]:
                try:
                    p = _P(str(s).strip().strip('"'))
                    exists = p.is_file()
                    size = p.stat().st_size if exists else 0
                except OSError:
                    exists, size = False, 0
                items.append(
                    {
                        "path": str(s),
                        "name": p.name,
                        "kind": "image" if is_image_path(str(s)) else "document",
                        "exists": exists,
                        "size": size,
                    }
                )
            await self.bus.publish(
                create_event("ui.file_ingest", "file_ingest", {"items": items}, correlation_id=cid)
            )
            await self._send(
                ws, {"type": "file_ingest", "payload": {"ok": True, "items": items}, "correlation_id": cid}
            )
        elif et == "get_settings":
            await self._send(ws, {"type": "settings", "payload": get_settings()})
        elif et == "save_settings":
            t0 = time.monotonic()
            saved = save_settings(payload)
            logger.info("save_settings: files written in %.0fms cid=%s", (time.monotonic() - t0) * 1000, cid)
            await self.bus.publish(create_event("settings.updated", "updated", saved, correlation_id=cid))
            logger.info("save_settings: bus published in %.0fms cid=%s", (time.monotonic() - t0) * 1000, cid)
            await self._send(ws, {"type": "settings_saved", "payload": saved, "correlation_id": cid})
            logger.info("save_settings: reply sent in %.0fms cid=%s", (time.monotonic() - t0) * 1000, cid)
        elif et == "ping":
            await self._send(ws, {"type": "pong"})
        elif et == "test_lm_studio":
            from core.llm import test_lm

            res = await test_lm(
                payload.get("url"),
                provider=payload.get("provider"),
                api_key=payload.get("api_key"),
            )
            await self._send(ws, {"type": "lm_test", "payload": res, "correlation_id": cid})
        elif et == "set_pet":
            enabled = bool(payload.get("enabled", True))
            cfg = _read_yaml("config.yaml") or {}
            rt = cfg.get("runtime") or {}
            rt["pet_enabled"] = enabled
            cfg["runtime"] = rt
            _write_yaml("config.yaml", cfg)
            await self.bus.publish(
                create_event("ui.pet_visibility", "pet_visibility", {"enabled": enabled}, correlation_id=cid)
            )
        elif et == "state":
            await self._send(ws, {"type": "state", "payload": {"ok": True}})
        elif et == "voice_listen":
            if self.voice:
                await self.voice.set_listening(bool(payload.get("on", True)))
        elif et == "voice_wake":
            if self.voice:
                self.voice.set_wake_enabled(bool(payload.get("enabled", True)))
        elif et == "voice_devices":
            devices = self.voice.list_devices() if self.voice else []
            current = self.voice.current_device() if self.voice else "default"
            await self._send(
                ws,
                {"type": "voice_devices", "payload": {"devices": devices, "current": current}, "correlation_id": cid},
            )
        elif et == "voice_device":
            name = payload.get("device") or None
            cfg = _read_yaml("config.yaml") or {}
            v = cfg.get("voice") or {}
            v["device"] = name
            cfg["voice"] = v
            _write_yaml("config.yaml", cfg)
            ok = self.voice.set_device(name) if self.voice else False
            await self.bus.publish(create_event("settings.updated", "updated", get_settings(), correlation_id=cid))
            await self._send(
                ws,
                {"type": "voice_device_set", "payload": {"device": name, "ok": ok}, "correlation_id": cid},
            )
        elif et == "tts_test":
            from core.bus import create_event as _ce

            text = str(payload.get("text") or "Hello, I'm Jarvis. This is how I sound now.")
            await self.bus.publish(
                _ce("voice.say", "say", {"text": text, "voice": payload.get("voice")}, correlation_id=cid)
            )
        elif et == "wake_test":
            ok = self.voice.start_wake_test(payload.get("seconds", 8)) if self.voice else False
            await self._send(ws, {"type": "wake_test_ack", "payload": {"ok": ok}, "correlation_id": cid})
        elif et == "autostart":
            from core.autostart import set_autostart

            res = set_autostart(bool(payload.get("enabled", False)))
            await self._send(ws, {"type": "autostart_state", "payload": res, "correlation_id": cid})
        elif et == "autostart_state":
            from core.autostart import get_autostart

            await self._send(ws, {"type": "autostart_state", "payload": get_autostart(), "correlation_id": cid})
        elif et == "rm_state":
            from core.model_lifecycle import get_lifecycle

            lc = get_lifecycle()
            snap = await asyncio.to_thread(lc.snapshot) if lc else {"auto_manage": False, "loaded": [], "not_loaded": []}
            extra = getattr(self, "stats_extra", None)
            if extra:
                try:
                    snap["fast_path"] = extra()
                except Exception:
                    pass
            await self._send(ws, {"type": "rm_state", "payload": snap, "correlation_id": cid})
        elif et == "hook_state":
            from backend.hook_bridge import hook_state

            st = await asyncio.to_thread(hook_state)
            h = getattr(self, "hook", None)
            if h is not None:
                st["stats"] = dict(h.stats)
                st["sessions"] = dict(h.sessions)
                st["listening"] = h.alive
            await self._send(ws, {"type": "hook_state", "payload": st, "correlation_id": cid})
        elif et == "hook_install":
            from backend.hook_bridge import install_hook

            res = await asyncio.to_thread(install_hook, str(payload.get("target") or ""))
            res["target"] = str(payload.get("target") or "")
            await self._send(ws, {"type": "hook_install", "payload": res, "correlation_id": cid})
        elif et == "hook_uninstall":
            from backend.hook_bridge import uninstall_hook

            res = await asyncio.to_thread(uninstall_hook, str(payload.get("target") or ""))
            res["target"] = str(payload.get("target") or "")
            await self._send(ws, {"type": "hook_uninstall", "payload": res, "correlation_id": cid})
        elif et == "hook_terminal":
            from backend.hook_bridge import focus_pid

            ok = await asyncio.to_thread(focus_pid, payload.get("pid"))
            await self._send(ws, {"type": "hook_terminal", "payload": {"ok": bool(ok)}, "correlation_id": cid})
        elif et == "dictation":
            await self._dictation(ws, payload, cid)
        elif et == "dictation_history":
            from tools.dictation_injector import read_history

            entries = await asyncio.to_thread(read_history, int(payload.get("limit") or 100))
            await self._send(
                ws, {"type": "dictation_history", "payload": {"entries": entries}, "correlation_id": cid}
            )
        elif et == "vocabulary_get":
            from core.stt import load_vocabulary

            mappings = await asyncio.to_thread(load_vocabulary)
            await self._send(ws, {"type": "vocabulary", "payload": {"mappings": mappings}, "correlation_id": cid})
        elif et == "vocabulary_save":
            from core.stt import load_vocabulary, save_vocabulary

            mappings = payload.get("mappings") if isinstance(payload.get("mappings"), list) else []
            path = await asyncio.to_thread(save_vocabulary, mappings)
            fresh = await asyncio.to_thread(load_vocabulary)
            await self._send(
                ws,
                {
                    "type": "vocabulary",
                    "payload": {"mappings": fresh, "saved": True, "path": str(path)},
                    "correlation_id": cid,
                },
            )
        elif et in ("memory.list", "memory_list"):
            state = await self._memory_state()
            await self._send(ws, {"type": "memory.list", "payload": state, "correlation_id": cid})
        elif et in ("memory.add", "memory_add"):
            reply = await self._memory_add(payload, cid)
            await self._send(ws, {"type": "memory.add", "payload": reply, "correlation_id": cid})
        elif et in ("memory.delete", "memory_delete"):
            reply = await self._memory_delete(str(payload.get("id") or ""), cid)
            await self._send(ws, {"type": "memory.delete", "payload": reply, "correlation_id": cid})
        elif et in ("memory.clear", "memory_clear"):
            reply = await self._memory_clear(cid)
            await self._send(ws, {"type": "memory.clear", "payload": reply, "correlation_id": cid})
        elif et in ("tasks.list", "tasks_list"):
            tm = getattr(self, "tasks", None)
            await self._send(
                ws, {"type": "tasks.list", "payload": tm.snapshot() if tm else {"tasks": []},
                     "correlation_id": cid}
            )
        elif et in ("tasks.create", "tasks_create"):
            reply = await self._task_create(payload, cid)
            await self._send(ws, {"type": "tasks.create", "payload": reply, "correlation_id": cid})
        elif et in ("tasks.cancel", "tasks_cancel"):
            reply = await self._task_cancel(str(payload.get("task_id") or ""), cid)
            await self._send(ws, {"type": "tasks.cancel", "payload": reply, "correlation_id": cid})
        elif et == "onboarding_state":
            await self._send(
                ws, {"type": "onboarding_state", "payload": await self._onboarding_state(),
                     "correlation_id": cid}
            )
        elif et == "onboarding_done":
            await self._send(
                ws, {"type": "onboarding_done", "payload": await self._onboarding_done(payload),
                     "correlation_id": cid}
            )

    # ---------- memory / tasks / onboarding helpers (spec 32) ----------

    async def _memory_state(self) -> dict:
        from skills import memory_skills

        return await asyncio.to_thread(memory_skills.snapshot)

    async def _memory_add(self, payload: dict, cid) -> dict:
        from skills import memory_skills

        content = str(payload.get("content") or "").strip()
        if not content:
            return {"ok": False, "error": "empty content"}
        fact = await asyncio.to_thread(
            memory_skills.remember, content, payload.get("category"), float(payload.get("confidence") or 0.95)
        )
        state = await self._memory_state()
        await self.bus.publish(create_event("memory.updated", "memory.updated", state, correlation_id=cid))
        return {"ok": True, "fact": fact, **state}

    async def _memory_delete(self, fact_id: str, cid) -> dict:
        from skills import memory_skills

        removed = await asyncio.to_thread(memory_skills.forget, fact_id) if fact_id else False
        state = await self._memory_state()
        await self.bus.publish(create_event("memory.updated", "memory.updated", state, correlation_id=cid))
        return {"ok": removed, "id": fact_id, **state}

    async def _memory_clear(self, cid) -> dict:
        from skills import memory_skills

        count = await asyncio.to_thread(memory_skills.clear_all)
        state = await self._memory_state()
        await self.bus.publish(create_event("memory.updated", "memory.updated", state, correlation_id=cid))
        return {"ok": True, "removed": count, **state}

    async def _task_create(self, payload: dict, cid) -> dict:
        tm = getattr(self, "tasks", None)
        if tm is None:
            return {"ok": False, "error": "task manager unavailable"}
        ttype = str(payload.get("type") or "reminder")
        title = str(payload.get("title") or "Reminder")[:140]
        if ttype == "recurring":
            task = tm.create_recurring(title, float(payload.get("interval_seconds") or 3600),
                                       str(payload.get("action") or "system_memory"))
        else:
            due = payload.get("due_timestamp")
            seconds = payload.get("seconds")
            if due:
                task = tm.create_reminder(title, due_timestamp=float(due),
                                          kind=str(payload.get("kind") or "reminder"))
            else:
                task = tm.create_reminder(title, seconds=float(seconds or 60),
                                          kind=str(payload.get("kind") or "reminder"))
        await tm.notify()
        return {"ok": True, "task": task, **tm.snapshot()}

    async def _task_cancel(self, task_id: str, cid) -> dict:
        tm = getattr(self, "tasks", None)
        removed = bool(tm and tm.cancel(task_id))
        if tm:
            await tm.notify()
        return {"ok": removed, "id": task_id, **(tm.snapshot() if tm else {"tasks": []})}

    async def _onboarding_state(self) -> dict:
        from core.config import DATA_DIR

        marker = DATA_DIR / "onboarded.json"
        first_run = (_read_yaml("config.yaml").get("runtime") or {}).get("first_run", True)
        show = bool(first_run is not False and not marker.exists())
        return {"show": show}

    async def _onboarding_done(self, payload: dict) -> dict:
        import json as _json

        from core.config import DATA_DIR

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        marker = DATA_DIR / "onboarded.json"
        with open(marker, "w", encoding="utf-8") as f:
            _json.dump({"completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "pet_style": str(payload.get("pet_style") or "")}, f)
        # packaged installs also flip the config flag; the dev config doubles as
        # the bundled template, so only touch it when running frozen
        if getattr(sys, "frozen", False):
            cfg = _read_yaml("config.yaml")
            rt = cfg.get("runtime") or {}
            rt["first_run"] = False
            cfg["runtime"] = rt
            _write_yaml("config.yaml", cfg)
        return {"ok": True, "show": False}

    async def _dictation(self, ws, payload, cid):
        """spec 29 section 3.2: toggle/apply dictate-to-cursor."""
        action = str(payload.get("action") or "toggle")
        if not self.voice:
            await self._send(
                ws, {"type": "dictation_ack", "payload": {"ok": False, "error": "voice unavailable"}, "correlation_id": cid}
            )
            return
        if action in ("start", "stop", "toggle"):
            target = action == "start" or (action == "toggle" and not self.voice.is_dictating)
            ok = await self.voice.set_dictation(target)
            await self._send(
                ws,
                {"type": "dictation_ack", "payload": {"ok": ok, "active": self.voice.is_dictating}, "correlation_id": cid},
            )
        elif action == "apply":
            res = await self.voice.apply_dictation_text(str(payload.get("text") or ""))
            res["active"] = self.voice.is_dictating
            await self._send(ws, {"type": "dictation_ack", "payload": res, "correlation_id": cid})
        else:
            await self._send(
                ws,
                {"type": "dictation_ack", "payload": {"ok": False, "error": "unknown action"}, "correlation_id": cid},
            )

    async def _send(self, ws, obj):
        try:
            # bounded: one stalled/frozen client must never freeze the loop
            await asyncio.wait_for(ws.send_json(obj), timeout=0.5)
        except Exception as e:
            logger.warning("send failed (%s): %r; dropping client (clients=%d)", obj.get("type") or obj.get("topic"), e, len(self.clients))
            self.clients.discard(ws)

    async def broadcast(self, topic: str, payload: dict, cid=None):
        obj = {"topic": topic, "payload": payload}
        if cid:
            obj["correlation_id"] = cid
        for ws in list(self.clients):
            await self._send(ws, obj)

    def wire_bus(self):
        async def fwd_ui(ev):
            await self.broadcast(ev.topic, ev.payload, ev.correlation_id)

        for t in ("ui.pet_state", "ui.chat", "ui.approval", "ui.state", "ui.pet_visibility", "ui.voice_state", "ui.mic_level", "ui.wake_test", "tts_state", "rm_state", "ui.approval_cancelled", "tool.result", "dictation.start", "dictation.result", "dictation.stop", "intent.fast_path", "agent.hook.session", "agent.hook.diff", "agent.hook.approval_request", "ui.file_ingest", "memory.updated", "tasks.updated", "task.fired", "voice.say"):
            self.bus.subscribe(t, fwd_ui)