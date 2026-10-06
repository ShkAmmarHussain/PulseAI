"""Persistent long-term memory store (spec 32, section 2.1).

A small JSON-backed fact store at ``data/memory.json``:

    {"profile": {...}, "facts": [{"id", "category", "content",
                                  "created_at", "confidence"}, ...]}

Categories: preferences | facts | projects | workflows | people.
Writes are atomic (tmp file + os.replace) and guarded by a process-wide lock
so the WS bridge, the fast path and the MemoryAgent can all touch it.
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone

from core.config import DATA_DIR

logger = logging.getLogger(__name__)

CATEGORIES = ("preferences", "facts", "projects", "workflows", "people")
DEFAULT_CATEGORY = "facts"
MAX_FACTS = 2000

MEMORY_FILE = DATA_DIR / "memory.json"

_DEFAULT = {"profile": {}, "facts": []}

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return "mem_" + uuid.uuid4().hex[:8]


def _empty() -> dict:
    return {"profile": {}, "facts": []}


def _load_unlocked() -> dict:
    try:
        if not MEMORY_FILE.exists():
            return _empty()
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty()
        data.setdefault("profile", {})
        data.setdefault("facts", [])
        if not isinstance(data["facts"], list):
            data["facts"] = []
        return data
    except Exception:
        logger.exception("memory store unreadable (%s); starting empty", MEMORY_FILE)
        return _empty()


def _save_unlocked(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MEMORY_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, MEMORY_FILE)


def snapshot() -> dict:
    """A deep-ish copy of {profile, facts} safe to hand to JSON."""
    with _lock:
        data = _load_unlocked()
        return {"profile": dict(data["profile"]), "facts": [dict(f) for f in data["facts"]]}


def profile() -> dict:
    with _lock:
        return dict(_load_unlocked()["profile"])


def set_profile_value(key: str, value) -> dict:
    with _lock:
        data = _load_unlocked()
        data["profile"][str(key)] = value
        _save_unlocked(data)
        return dict(data["profile"])


def list_facts(category: str = None, query: str = None) -> list:
    facts = snapshot()["facts"]
    if category and category.lower() not in ("", "all"):
        facts = [f for f in facts if str(f.get("category", "")).lower() == category.lower()]
    if query:
        q = query.lower()
        facts = [f for f in facts if q in str(f.get("content", "")).lower()
                 or q in str(f.get("category", "")).lower()]
    return facts


def add_fact(content: str, category: str = None, confidence: float = 0.95) -> dict:
    content = str(content or "").strip()
    if not content:
        raise ValueError("empty memory content")
    cat = (category or "").strip().lower()
    if cat not in CATEGORIES:
        cat = classify(content)
    fact = {
        "id": _new_id(),
        "category": cat,
        "content": content,
        "created_at": _now(),
        "confidence": round(float(confidence), 3),
    }
    with _lock:
        data = _load_unlocked()
        # de-duplicate: same content keeps its original id/timestamp
        for existing in data["facts"]:
            if str(existing.get("content", "")).strip().lower() == content.lower():
                return dict(existing)
        data["facts"].insert(0, fact)
        if len(data["facts"]) > MAX_FACTS:
            data["facts"] = data["facts"][:MAX_FACTS]
        _save_unlocked(data)
    return dict(fact)


def delete_fact(fact_id: str) -> bool:
    with _lock:
        data = _load_unlocked()
        before = len(data["facts"])
        data["facts"] = [f for f in data["facts"] if f.get("id") != fact_id]
        removed = len(data["facts"]) != before
        if removed:
            _save_unlocked(data)
        return removed


def clear() -> int:
    with _lock:
        data = _load_unlocked()
        n = len(data["facts"])
        data["facts"] = []
        _save_unlocked(data)
        return n


def classify(content: str) -> str:
    """Heuristic category for facts stored from natural language."""
    t = content.lower()
    if any(k in t for k in ("project", "repo", "repository", "working on", "codebase",
                            "d:\\", "d:/", "branch", "sprint", "build of")):
        return "projects"
    if any(k in t for k in ("colleague", "friend", "manager", "boss", "wife", "husband",
                            "partner", "team lead", "client is", "my doctor")):
        return "people"
    if any(k in t for k in ("every time", "each time", "always when", "routine",
                            "workflow", "step by step", "from now on when")):
        return "workflows"
    if any(k in t for k in ("prefer", "likes?", "favorite", "favourite", "always use",
                            "default to", "my language", "remind me i", "hate", "want my")):
        return "preferences"
    return DEFAULT_CATEGORY


def recall_context(query: str, limit: int = 6) -> str:
    """Facts most relevant to a query, formatted for an LLM system prompt."""
    q = (query or "").lower()
    facts = snapshot()["facts"]
    if not facts:
        return ""
    tokens = {w for w in q.replace("?", " ").replace(",", " ").split() if len(w) > 2}
    scored = []
    for f in facts:
        content = str(f.get("content", "")).lower()
        score = sum(1 for w in tokens if w in content)
        if q and q in content:
            score += 3
        scored.append((score, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [f for s, f in scored[:limit] if s > 0] or [f for _s, f in scored[: min(3, len(scored))]]
    if not picked:
        return ""
    lines = [f"- [{f.get('category', 'facts')}] {f.get('content', '')}" for f in picked]
    return "Known facts about the user (use when relevant, do not restate):\n" + "\n".join(lines)
