import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


async def search(query: str, max_results: int = 5) -> List[dict]:
    """Web search via DuckDuckGo (no API key). Returns [{title, url, snippet}]."""
    from ddgs import DDGS

    def _run():
        out = []
        with DDGS() as d:
            for r in d.text(query, max_results=max_results):
                out.append({
                    "title": r.get("title", ""),
                    "url": r.get("href") or r.get("url", ""),
                    "snippet": r.get("body", ""),
                })
        return out

    try:
        return await asyncio.to_thread(_run)
    except Exception:
        logger.exception("web search failed: %s", query)
        return []


def format_results(results: List[dict], max_snippet: int = 280) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        snip = (r.get("snippet") or "").replace("\n", " ").strip()[:max_snippet]
        lines.append(f"{i}. {r.get('title', '')} - {snip} ({r.get('url', '')})")
    return "\n".join(lines)
