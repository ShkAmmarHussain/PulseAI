import logging

from agents.base import BaseAgent
from core.bus import Event, create_event

logger = logging.getLogger(__name__)


class ToolControlAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("tool_control", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("tool.execute", self.handle)

    async def _execute(self, s: dict) -> str:
        from skills import app_control, browser, file_ops, input_control, screen_vision, shell, web_search

        name = s.get("action", "noop")
        if name == "vision_describe":
            return await screen_vision.describe(
                self.cfg, s.get("query", ""), s.get("region"), rtm=self.rtm
            )
        if name == "vision_file":
            return await screen_vision.describe_file(
                self.cfg, s.get("path", ""), s.get("query", ""), rtm=self.rtm
            )
        if name == "summarize_file":
            return await self._summarize_file(s.get("path", ""))
        if name == "launch_app":
            return app_control.launch_app(s.get("target", ""))
        if name == "close_app":
            return app_control.close_app(s.get("target", ""))
        if name == "open_url":
            return browser.open_url(s.get("url", ""))
        if name == "delete_file":
            return file_ops.delete_path(s.get("target", ""))
        if name == "move_file":
            return file_ops.move_file(s.get("src", ""), s.get("dst", ""))
        if name == "create_file":
            return file_ops.create_file(s.get("path", ""), s.get("content", ""))
        if name == "list_dir":
            return file_ops.list_dir(s.get("target", "."))
        if name == "run_shell":
            return shell.run_command(s.get("cmd", ""))
        if name == "type_text":
            # approved input automation (spec 32, section 4)
            return input_control.type_text(s.get("text", ""))
        if name == "press_hotkey":
            return input_control.press_hotkey(s.get("keys") or [])
        if name == "click":
            return input_control.click(
                int(s.get("x") or 0), int(s.get("y") or 0),
                button=str(s.get("button") or "left"), clicks=int(s.get("clicks") or 1),
            )
        if name == "move_mouse":
            return input_control.move_mouse(int(s.get("x") or 0), int(s.get("y") or 0))
        if name == "web_search":
            results = await web_search.search(s.get("query", ""), max_results=5)
            if not results:
                return f"No web results for: {s.get('query', '')}"
            return "Web results:\n" + web_search.format_results(results)
        if name == "respond":
            return s.get("text", "ok")
        return f"executed {name}"

    async def _summarize_file(self, path: str) -> str:
        """Extract text (incl. PDF) and summarize via the orchestrator model."""
        import asyncio

        from core import llm
        from skills import file_ops

        text = file_ops.read_text(path)
        if text.startswith("File not found") or text.startswith("Failed"):
            return text
        roles = (((self.cfg or {}).get("agents") or {}).get("agent_roles")) or {}
        model = (roles.get("orchestrator") or {}).get("model_id") or "qwen3-8b"
        from pathlib import Path

        name = Path(path).name
        excerpt = text[:12000]
        prompt = (
            f"Summarize this file ({name}) for the user in a compact briefing: "
            "key points, structure/purpose, and anything notable. Plain text only.\n\n"
            f"--- file: {name} ---\n{excerpt}"
        )
        summary = await asyncio.to_thread(
            llm.chat_sync,
            self.cfg,
            model,
            [{"role": "user", "content": prompt}],
            0.3,
            450,
        )
        return summary or text[:600]

    async def handle(self, ev: Event):
        if ev.type == "execute":
            steps = ev.payload.get("steps", [])
            done, ok = [], True
            for s in steps:
                try:
                    done.append(await self._execute(s))
                except Exception as e:
                    logger.exception("tool step failed: %s", s)
                    done.append(f"Failed: {e}")
                    ok = False
            summary = "\n".join(done) if done else "Done."
            res = {"ok": ok, "summary": summary, "steps": steps}
            await self.bus.publish(create_event("tool.result", "tool_result", res, correlation_id=ev.correlation_id))
