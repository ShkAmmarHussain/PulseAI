"""Auto-model router unit tests (spec 33, section 4).

Pure-offline: httpx.get is monkeypatched so no LM Studio / network needed.
Covers provider selection, auto_routing off-switch, cloud tier maps, local
model picking, query-complexity heuristics and the 45s cache + invalidate.

Run: .venv/Scripts/python tests/model_router_test.py
exit 0 = pass
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import model_router as mr  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def cfg_for(provider=None, auto=None, models=None):
    llm = {}
    if provider is not None:
        llm["provider"] = provider
    if auto is not None:
        llm["auto_routing"] = auto
    c = {"config": {"llm": llm, "lm_studio": {"base_url": "http://127.0.0.1:1234/v1"}}}
    return c


def fake_models(monkey_ids):
    """Patch httpx.get to return a canned /v1/models payload."""
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"id": m} for m in monkey_ids]}

    def _get(url, timeout=None):
        return _Resp()

    mr.httpx.get = _get


def unit_tests():
    # ---- provider + auto_routing ----
    check("default provider is lm_studio", mr.provider({}) == "lm_studio", mr.provider({}))
    check("unknown provider falls back", mr.provider(cfg_for("grok")) == "lm_studio", mr.provider(cfg_for("grok")))
    check("openai provider read", mr.provider(cfg_for("openai")) == "openai")
    check("auto_routing defaults on", mr.auto_routing({}) is True)
    check("auto_routing off honoured", mr.auto_routing(cfg_for(auto=False)) is False)

    # ---- cloud tiers ----
    check("openai heavy = gpt-4o", mr.route(cfg_for("openai"), "heavy") == "gpt-4o")
    check("openai fast = gpt-4o-mini", mr.route(cfg_for("openai"), "fast") == "gpt-4o-mini")
    check("openai vision = gpt-4o", mr.route(cfg_for("openai"), "vision") == "gpt-4o")
    check("anthropic heavy = sonnet", mr.route(cfg_for("anthropic"), "heavy") == "claude-3-7-sonnet-latest")
    check("anthropic fast = haiku", mr.route(cfg_for("anthropic"), "fast") == "claude-3-5-haiku-latest")
    check(
        "anthropic vision = claude-3-5-sonnet",
        mr.route(cfg_for("anthropic"), "vision") == "claude-3-5-sonnet-latest",
    )

    # ---- auto_routing off -> caller fallback ----
    check(
        "routing off returns fallback",
        mr.route(cfg_for("openai", auto=False), "heavy", fallback="agents.yaml-model") == "agents.yaml-model",
    )
    check(
        "routing off route_query returns fallback",
        mr.route_query(cfg_for("openai", auto=False), "refactor this", fallback="agents.yaml-model")
        == "agents.yaml-model",
    )

    # ---- local picking (offline, canned model list) ----
    models = [
        "qwen2.5-vl-7b-instruct",
        "qwen2.5-coder-7b-instruct",
        "llama-3.2-3b-instruct",
        "qwen3-8b",
    ]
    fake_models(models)
    mr.invalidate()
    c = cfg_for()
    check("local vision pick = vl model", mr.route(c, "vision") == "qwen2.5-vl-7b-instruct", mr.route(c, "vision"))
    check("local heavy pick = coder", mr.route(c, "heavy") == "qwen2.5-coder-7b-instruct", mr.route(c, "heavy"))
    check("local fast pick = small model", mr.route(c, "fast") == "llama-3.2-3b-instruct", mr.route(c, "fast"))
    check("single-model list always picked", mr._local_pick(["only-model"], "fast") == "only-model")
    check("empty list -> None", mr._local_pick([], "fast") is None)
    check(
        "vision fallback chain: no vl -> coder",
        mr._local_pick(["coder-7b", "tiny-1b"], "vision") == "coder-7b",
        mr._local_pick(["coder-7b", "tiny-1b"], "vision"),
    )

    # ---- query complexity heuristics ----
    check("short chat is not complex", mr.is_complex("what time is it") is False)
    check("heavy keyword escalates", mr.is_complex("refactor the auth module") is True)
    check("15+ words escalate", mr.is_complex(" ".join(["word"] * 15)) is True)
    check("code fence escalates", mr.is_complex("run ```python\nprint(1)\n```") is True)
    check("newline escalates", mr.is_complex("line one\nline two") is True)

    # ---- route_query on cloud ----
    check(
        "simple query -> fast tier",
        mr.route_query(cfg_for("openai"), "hello there") == "gpt-4o-mini",
        mr.route_query(cfg_for("openai"), "hello there"),
    )
    check(
        "complex query -> heavy tier",
        mr.route_query(cfg_for("openai"), "refactor this module and explain trade-offs") == "gpt-4o",
        mr.route_query(cfg_for("openai"), "refactor this module and explain trade-offs"),
    )
    check(
        "local route_query returns a loaded model",
        mr.route_query(c, "hi") in models,
        mr.route_query(c, "hi"),
    )

    # ---- cache + invalidate ----
    fake_models(["cached-model-a"])
    mr.invalidate()
    mr.lm_models(c)
    fake_models(["cached-model-b"])  # within TTL the cache must win
    check("cache wins inside TTL", mr.lm_models(c) == ["cached-model-a"], mr.lm_models(c))
    mr.invalidate()
    check("invalidate clears cache", mr.lm_models(c) == ["cached-model-b"], mr.lm_models(c))

    # ---- localhost normalisation ----
    mr.invalidate()
    c2 = {"config": {"llm": {}, "lm_studio": {"base_url": "http://localhost:1234/v1"}}}
    fake_models(["norm-model"])
    check("localhost base_url normalises", mr.lm_models(c2) == ["norm-model"], mr.lm_models(c2))


def main():
    unit_tests()
    print(f"== {sum(results)}/{len(results)} PASS ==")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
