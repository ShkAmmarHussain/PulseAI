"""Reporter: turns task results into the reply for chat and voice (doc 36 §7, §18).

One result is the answer as is (no model call, keeps simple jobs fast).
Several results get one short fast-model summary.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Dict

Chat = Callable[[list, str], Awaitable[str]]


def make_reporter(cfg: dict, *, chat: Chat):
    async def report(text: str, results: Dict[str, str]) -> str:
        vals = [v for v in results.values() if v]
        if not vals:
            return "I could not finish that."
        if len(vals) == 1:
            return vals[0]
        body = "\n\n".join(f"{k}: {v}" for k, v in results.items() if v)
        out = await chat(
            [
                {"role": "system", "content": "Write the reply to the user from the team's results. 1-4 sentences, plain text, no lists unless needed."},
                {"role": "user", "content": f"Request: {text}\n\nResults:\n{body}"},
            ],
            "fast",
        )
        return str(out or "").strip() or "\n".join(vals)

    return report
