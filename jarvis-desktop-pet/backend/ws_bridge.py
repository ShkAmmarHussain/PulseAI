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

            res = await test_lm(payload.get("url"))
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
            await self._send(ws, {"type": "rm_state", "payload": snap, "correlation_id": cid})

    async def _send(self, ws, obj):
        try:
            await ws.send_json(obj)
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

        for t in ("ui.pet_state", "ui.chat", "ui.approval", "ui.state", "ui.pet_visibility", "ui.voice_state", "ui.mic_level", "ui.wake_test", "tts_state", "rm_state", "ui.approval_cancelled", "tool.result"):
            self.bus.subscribe(t, fwd_ui)