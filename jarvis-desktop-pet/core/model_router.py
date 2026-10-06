"""Intelligent auto-model router (spec 33, section 4).

Maps task tiers to the best model for the active provider:

    heavy   -> planning, tool use, complex coding/analysis
    fast    -> memory recall, quick conversational answers, classification
    vision  -> screen analysis / OCR
    primary -> orchestrator conversational core

Cloud providers use fixed tier maps; LM Studio queries /v1/models and picks
the coder / vision / small models dynamically. With auto_routing off the
caller's fallback (agents.yaml model_id) is used instead.
"""
import logging
import re
import time

import httpx

logger = logging.getLogger("model_router")

CLOUD_TIERS = {
    "openai": {
        "heavy": "gpt-4o",
        "fast": "gpt-4o-mini",
        "vision": "gpt-4o",
        "primary": "gpt-4o",
    },
    "anthropic": {
        "heavy": "claude-3-7-sonnet-latest",
        "fast": "claude-3-5-haiku-latest",
        "vision": "claude-3-5-sonnet-latest",
        "primary": "claude-3-5-sonnet-latest",
    },
}

CACHE_TTL_S = 45.0
_cache = {"at": 0.0, "models": None, "base": None}

# complexity signals -> escalate fast tier answers to the heavy tier
_HEAVY_RE = re.compile(
    r"\b(analy[sz]e|design|architect|refactor|debug|strategy|step[- ]by[- ]step|"
    r"compare|trade[- ]offs?|implement|algorithm|proof|proofread|optimize|"
    r"plan\b|planning|write (a|the) (function|class|script|program|module|essay)|"
    r"code (for|that|which)|generate code|explain (in detail|how it works))\b",
    re.I,
)
_SMALL_RE = re.compile(r"(^|[^a-z0-9])(1b|2b|3b|mini|small|tiny|flash)([^a-z0-9]|$)", re.I)
_VISION_RE = re.compile(r"(^|[^a-z0-9])(vl|vision|visual)([^a-z0-9]|$)", re.I)
_CODE_RE = re.compile(r"(coder|code|coding|coder-)", re.I)


def _llm_cfg(cfg: dict) -> dict:
    return (((cfg or {}).get("config") or {}).get("llm") or {})


def provider(cfg: dict) -> str:
    p = str(_llm_cfg(cfg).get("provider") or "lm_studio").strip().lower()
    return p if p in ("lm_studio", "openai", "anthropic") else "lm_studio"


def auto_routing(cfg: dict) -> bool:
    return _llm_cfg(cfg).get("auto_routing", True) is not False


def lm_models(cfg: dict) -> list:
    """Loaded LM Studio models via /v1/models (cached 45s, spec 33 section 4.2)."""
    lm = (((cfg or {}).get("config") or {}).get("lm_studio")) or {}
    base = str(lm.get("base_url") or "http://127.0.0.1:1234/v1").strip().rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    if base.lower().startswith("http://localhost"):
        base = "http://127.0.0.1" + base[len("http://localhost"):]
    now = time.monotonic()
    if _cache["models"] is not None and _cache["base"] == base and (now - _cache["at"]) < CACHE_TTL_S:
        return _cache["models"]
    try:
        r = httpx.get(base + "/models", timeout=2.0)
        r.raise_for_status()
        data = r.json() or {}
        ids = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
    except Exception as e:
        logger.debug("lm models query failed: %s", e)
        ids = _cache["models"] if _cache["base"] == base else None
        ids = ids or []
    _cache.update(at=now, models=ids, base=base)
    return ids


def invalidate() -> None:
    _cache.update(at=0.0, models=None, base=None)


def _local_pick(models: list, tier: str):
    """Tier pick from loaded local models (spec 33, section 4.2)."""
    if not models:
        return None
    if len(models) == 1:
        return models[0]
    vision = next((m for m in models if _VISION_RE.search(m)), None)
    coder = next((m for m in models if _CODE_RE.search(m) and not _VISION_RE.search(m)), None)
    small = next((m for m in models if _SMALL_RE.search(m) and not _VISION_RE.search(m)), None)
    instruct = next((m for m in models if not _VISION_RE.search(m) and not _SMALL_RE.search(m)), None)
    if tier == "vision":
        return vision or instruct or coder or models[0]
    if tier == "heavy":
        return coder or instruct or vision or models[0]
    if tier == "fast":
        return small or instruct or coder or models[0]
    return instruct or coder or vision or models[0]


def route(cfg: dict, tier: str, fallback: str = None) -> str:
    """Best model for a task tier, or fallback when auto-routing is off."""
    if not auto_routing(cfg):
        return fallback
    p = provider(cfg)
    if p in CLOUD_TIERS:
        return CLOUD_TIERS[p].get(tier) or fallback
    picked = _local_pick(lm_models(cfg), tier)
    return picked or fallback


def is_complex(query: str) -> bool:
    """Heavy-tier trigger: long or explicitly complex prompts."""
    q = str(query or "")
    if len(q.split()) > 14:
        return True
    if "```" in q or "\n" in q.strip():
        return True
    return bool(_HEAVY_RE.search(q))


def route_query(cfg: dict, query: str, fallback: str = None) -> str:
    """Auto-tier for conversational/memory answers: heavy when complex, else fast."""
    if not auto_routing(cfg):
        return fallback
    p = provider(cfg)
    if p in CLOUD_TIERS:
        return CLOUD_TIERS[p]["heavy" if is_complex(query) else "fast"]
    picked = _local_pick(lm_models(cfg), "fast")
    return picked or fallback
