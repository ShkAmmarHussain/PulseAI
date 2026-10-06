"""Memory skills (spec 32, section 2.1): thin, string-friendly wrappers over
``core.memory_store`` that the tool layer, WS bridge and fast path all use."""

from core import memory_store as store


def remember(content: str, category: str = None, confidence: float = 0.95) -> dict:
    """Persist one fact. Returns the stored fact (with id + timestamp)."""
    return store.add_fact(content, category=category, confidence=confidence)


def forget(fact_id: str) -> bool:
    """Delete one fact by id. True when something was removed."""
    return store.delete_fact(fact_id)


def list_memories(category: str = None, query: str = None) -> list:
    return store.list_facts(category=category, query=query)


def clear_all() -> int:
    """Forget everything. Returns how many facts were dropped."""
    return store.clear()


def recall(query: str, limit: int = 6) -> str:
    """Facts relevant to a query, formatted for prompt injection."""
    return store.recall_context(query, limit=limit)


def snapshot() -> dict:
    """Full {profile, facts} state for the Memory Studio UI."""
    return store.snapshot()


def classify(content: str) -> str:
    return store.classify(content)
