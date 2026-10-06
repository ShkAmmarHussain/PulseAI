import logging
import re

from agents.base import BaseAgent
from core.bus import Event, create_event
from core.llm import chat

logger = logging.getLogger(__name__)

WEB_HINTS = (
    "latest", "today", "news", "weather", "current", "right now", "price", "stock",
    "score", "who won", "this week", "this year", "recent", "just released",
    "release date", "2026", "2025", "forecast", "exchange rate", "population of",
)
REFUSAL_PAT = re.compile(
    r"knowledge cutoff|don't have real[- ]?time|cannot (access|browse|search)|"
    r"unable to (access|browse)|no internet|not connected to the internet|"
    r"as of my last (knowledge|update)",
    re.I,
)


class MemoryAgent(BaseAgent):
    def __init__(self, bus):
        super().__init__("memory_agent", bus)

    async def start(self):
        await super().start()
        self.bus.subscribe("memory.request", self.handle)
        self.bus.subscribe("memory.store", self.handle)

    def _needs_web(self, query: str) -> bool:
        low = query.lower()
        return any(h in low for h in WEB_HINTS)

    async def _web(self, query: str) -> str:
        from skills.web_search import format_results, search

        results = await search(query, max_results=5)
        if results:
            return "Web search results (use these, cite sources):\n" + format_results(results)
        return ""

    async def _answer(self, query: str, web_ctx: str = "") -> str:
        from datetime import datetime

        agents = (self.cfg or {}).get("agents") or {}
        role = (agents.get("agent_roles") or {}).get("memory_agent") or {}
        ident = ((self.cfg or {}).get("personality") or {}).get("identity") or {}
        name = ident.get("name") or "Jarvis"
        style = ident.get("voice_style") or "friendly and concise"
        now = datetime.now().astimezone()
        system = (
            f"You are {name}, a desktop pet assistant running locally on the user's Windows PC. "
            f"Your style: {style}. "
            f"Current date and time: {now.strftime('%A, %B %d, %Y, %H:%M')} ({now.strftime('%Z')}, "
            f"UTC{now.strftime('%z')}). "
            "Use this date/time context when asked about dates, times, days, or schedules. "
            "You have a web search tool: when search results are provided below, answer from them "
            "and mention the source. Otherwise answer from your knowledge in 1-3 sentences "
            "unless asked for detail."
        )
        # recall injection (spec 32, section 6): persistent facts enter the
        # model context here so answers reflect what Jarvis already learned
        try:
            from skills import memory_skills

            recalled = memory_skills.recall(query, limit=6)
            if recalled:
                system += "\n\n" + recalled
        except Exception:
            logger.exception("memory recall injection failed")
        if web_ctx:
            system += "\n\n" + web_ctx
        model = role.get("model_id") or "llama-3.2-3b-instruct"
        return await chat(
            self.cfg or {},
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": query}],
            temperature=float(role.get("temperature", 0.7)),
            max_tokens=int(role.get("max_tokens", 256)),
        )

    async def handle(self, ev: Event):
        if ev.type == "recall":
            q = ev.payload.get("query", "")
            answer, web_ctx = "", ""
            try:
                if self._needs_web(q):
                    web_ctx = await self._web(q)
                answer = await self._answer(q, web_ctx)
                if not web_ctx and answer and REFUSAL_PAT.search(answer):
                    web_ctx = await self._web(q)
                    if web_ctx:
                        answer = await self._answer(q, web_ctx)
            except Exception:
                logger.exception("memory llm call failed (model unreachable?)")
            if not answer:
                answer = f"I recall context for: {q}"
            await self.bus.publish(
                create_event("memory.result", "memory_result", {"answer": answer}, correlation_id=ev.correlation_id)
            )
        elif ev.type == "store":
            pass
