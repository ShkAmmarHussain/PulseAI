import asyncio
import logging

from core.bus import MessageBus, Event, create_event
from core.config import load_config
from core.resources import ResourceTransitionManager
from core.state import GlobalState
from agents.registry import AGENTS

logger = logging.getLogger("backend")


class App:
    def __init__(self):
        self.cfg = load_config()
        self.bus = MessageBus(max_queue_size=self.cfg["config"].get("ipc", {}).get("max_queue_size", 1000))
        rm_cfg = self.cfg["config"].get("resource_manager", {})
        self.rtm = ResourceTransitionManager(
            vision_timeout_ms=rm_cfg.get("vision_timeout_ms", 20000),
            unload_idle_ms=rm_cfg.get("unload_idle_ms", 60000),
            cooldown_ms=rm_cfg.get("cooldown_ms", 2000),
        )
        from core.model_lifecycle import ModelLifecycle

        self.lifecycle = ModelLifecycle(
            self.cfg["config"].get("lm_studio") or {},
            rm_cfg,
        )
        from core import llm

        llm.set_lifecycle(self.lifecycle)
        self.state = GlobalState()
        self.agents = {}
        self.bridge = None

    async def start(self):
        for name, cls in AGENTS.items():
            inst = cls(self.bus)
            for attr, val in (("rtm", self.rtm), ("state", self.state), ("cfg", self.cfg)):
                if hasattr(inst, attr):
                    setattr(inst, attr, val)
            self.agents[name] = inst
            await inst.start()

        async def on_input(ev: Event):
            text = str(ev.payload.get("text", ev.payload.get("transcript", ""))).strip()
            fast = getattr(self, "fast", None)
            if text and fast is not None and await fast.try_handle(text, ev.correlation_id):
                return
            await self.bus.publish(
                create_event(
                    "orchestrator.input", "input", ev.payload,
                    correlation_id=ev.correlation_id, source=ev.source or "perception",
                )
            )

        self.bus.subscribe("input.text", on_input)
        self.bus.subscribe("input.voice", on_input)

        async def on_settings(ev: Event):
            self.cfg = load_config()
            for a in self.agents.values():
                a.cfg = self.cfg
            self.lifecycle.update_config(
                self.cfg["config"].get("lm_studio") or {},
                self.cfg["config"].get("resource_manager") or {},
            )
            if getattr(self, "hotkey", None):
                vc = (self.cfg.get("config", {}).get("voice") or {})
                self.hotkey.start(vc.get("hotkey"), vc.get("dictation_hotkey") or "ctrl+alt+d")
            if getattr(self, "fast", None):
                self.fast.update_config(self.cfg)
            if self.bridge:
                await self.bridge.broadcast("ui.state", {"settings_saved": True}, ev.correlation_id)
                await self.lifecycle.notify_now()

        self.bus.subscribe("settings.updated", on_settings)

        # WS bridge + server (pet/chat/settings windows connect here)
        from backend.ws_bridge import WSBridge
        from backend.voice_service import VoiceService

        self.voice = VoiceService(self.bus, self.cfg)
        self.bridge = WSBridge(self.bus, voice=self.voice)
        self.bridge.wire_bus()

        from skills.task_manager import get_task_manager

        self.tasks = get_task_manager(self.bus)
        await self.tasks.start()
        self.bridge.tasks = self.tasks

        from backend.hook_bridge import HookBridge

        self.hook = HookBridge(self.bus)
        self.bridge.hook = self.hook
        self.hook.start(asyncio.get_running_loop())

        async def rm_changed(snap: dict):
            if self.bridge:
                try:
                    snap["fast_path"] = self.fast.stats()
                except Exception:
                    pass
                await self.bridge.broadcast("rm_state", snap)

        self.lifecycle.on_change = rm_changed
        self._lifecycle_task = asyncio.create_task(self.lifecycle.run())
        await self.voice.start()

        from backend.hotkey_service import HotkeyService

        self.hotkey = HotkeyService(self.voice)
        vc = (self.cfg.get("config", {}).get("voice") or {})
        self.hotkey.start(vc.get("hotkey"), vc.get("dictation_hotkey") or "ctrl+alt+d")

        from core.fast_router import FastRouter

        self.fast = FastRouter(self.bus, self.cfg)
        await self.fast.start()
        self.fast.tasks = self.tasks
        self.bridge.stats_extra = self.fast.stats

        self.bus.start()

        from aiohttp import web

        app = web.Application()
        app.router.add_get("/ws", self.bridge.handle_ws)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 8765)
        await site.start()
        logger.info("WS server on ws://127.0.0.1:8765/ws")


async def main():
    app = App()
    await app.start()
    print("Jarvis Desktop App - all systems running")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())