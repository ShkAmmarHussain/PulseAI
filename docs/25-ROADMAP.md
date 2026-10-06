# 25. ROADMAP (Future Work)

Where to go next, ordered by leverage. Specs 27–31 are complete; 32 is the active blueprint.

## 25.1 Next Up — Spec 32 (planned, not started)

[32-TASKS-MEMORY-AND-PRODUCT-SURFACES](./32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md):
- **Memory Studio UI** — browse/edit/forget ChromaDB-backed facts (`data/memory.json` mirror).
- **Tasks, reminders & automations** — scheduled routines, live countdown in Activity, expiry chime.
- **PC input automation** — implement `skills/input_control.py` (currently a placeholder) with approval gating.
- **First-run onboarding** — guided model/mic/permission setup.

## 25.2 Product Surfaces (from doc 27, deferred)

Only `chat | activity | settings` panes exist today. Deferred: **Tasks**, **Automations**, **Memory** panes; **Integrations** detail screens; first-run flow; toast/notification system; offline/empty/error state taxonomy; **global search is deliberately excluded** (test markers forbid `id="global-search"` — do not add without a new spec decision).

## 25.3 Engineering Backlog

- **Skills completion** — 8 of 15 `skills/*` are placeholders (`input_control`, `memory_skills`, `notify`, `planning`, `stt`, `task_manager`, `tts`, `wakeword`).
- **Wire the safety config** — `permissions.yaml` `shell.allowlist/denylist` are not consumed by `skills/shell.py`; `core/permissions.py::SessionGrants` is implemented but unreferenced (hook bridge has its own 8 h grants).
- **Dependency hygiene** — declare `ddgs`, `kokoro_onnx`, `pycaw`, `pypdf` in `pyproject.toml` (currently only in `requirements.txt` or undeclared); consider dropping unused `smolagents`.
- **Test modernization** — migrate plain scripts to pytest (fixtures for WS/App) while keeping exit-code gates; move mirrored static checks into `tests/`.
- **`main.ts` cleanup** — vestigial Tauri TS stub, referenced nowhere; either adopt TS properly or delete.
- **Docs parity** — docs `09`–`16` are outline-thin; expand to match the "nothing skipped" promise of [00-README](./00-README.md).

## 25.4 Research Directions (original themes, kept)

- Better UI grounding / smaller local VLM for vision.
- Memory compression & forgetting curves; proactive mode (context-triggered suggestions).
- Local skill marketplace / plugin loading with sandboxed governance (`skills.yaml → governance`).
- Multi-monitor placement, gesture input, personality evolution driven by `personality.yaml` mood engine.
- Latency: streaming TTS chunk overlap, speculative fast-path matching (regex → tiny local classifier).

## 25.5 Packaging & Ops

- Signed MSI/NSIS installer (WiX `en-US` already configured), one-click portable zip.
- Crash/diagnostics bundle (log + `rm_state` + config redacted).
- Resource manager heuristics beyond `max_concurrent_models: 2` / `unload_idle_ms: 60000` (VRAM-aware per-role loading).
