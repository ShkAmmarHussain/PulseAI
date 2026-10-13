# 25. ROADMAP (Future Work)

Where to go next, ordered by leverage. Specs 27–33 are complete (32: memory, tasks, input automation, onboarding; 33: titlebar, multi-provider LLM, auto-router). The next spec is not written yet.

## 25.1 Shipped Since the Last Roadmap

- **Spec 32** — Memory Studio, tasks/reminders/timers, `skills/input_control.py` (ctypes `SendInput`, approval-gated), 3-step onboarding. See [32](./32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md) §8.
- **Spec 33** — frameless titlebar, OpenAI / Anthropic / LM Studio providers, auto-model router with a Settings on/off switch. See [33](./33-CUSTOM-TITLEBAR-CLOUD-MODELS-AND-UI-POLISH.md) §9.

## 25.2 Product Surfaces (from doc 27, deferred)

Panes today: `chat | activity | memory | settings` (tasks/timers live inside Activity). Still deferred: a dedicated **Automations** pane; **Integrations** detail screens; toast/notification system beyond the Memory undo toast; offline/empty/error state taxonomy; **global search is deliberately excluded** (test markers forbid `id="global-search"` — do not add without a new spec decision).

## 25.3 Engineering Backlog

- **Skills completion** — 4 of 15 `skills/*` are still placeholders (`planning`, `stt`, `tts`, `wakeword`; the real STT/TTS/wake code lives in `core/` and `backend/voice_service.py`).
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
