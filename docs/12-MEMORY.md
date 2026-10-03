# 12. MEMORY

Episodic + Semantic + Procedural, ChromaDB + JSON, consolidation, learning.

## 12.1 Types
- Episodic: timeline events (what/when/context/outcome)
- Semantic: facts about user (name, prefs, projects)
- Procedural: how-to (worked solutions)

## 12.2 Storage
- Vector: ChromaDB (local, persistence memory/chroma/, CPU/light)
- Episodic: memory/episodic.json (append-only, time-series)
- Semantic/Procedural: Chroma collections + summaries

## 12.3 Recall
Hybrid: recency + semantic similarity + relevance + importance. Inject ContextBundle into agents.

## 12.4 Consolidation
Periodic (after task, idle), dedupe, summarize, decay low-value, cap size.

## 12.5 Learning
Incremental, non-destructive, auditable, forget policy configurable.
