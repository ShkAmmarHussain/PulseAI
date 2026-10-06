# 22. TIMELINE (As-Built Phased Roadmap)

Historical record of how the product was actually built, mapped to the specs and the gate suites that proved each phase. (Original estimates lived here as a stub; this reflects shipped reality.)

## 22.1 Phase Table

| Phase | Scope | Key Deliverables | Proof |
|---|---|---|---|
| **0. Foundation** | Bus, config, agents skeleton, WS bridge, Tauri shell | `core/bus.py`, `backend/app.py`, `ws.js`, 3-window layout (main/pet/dock), tray | `smoke_test.py`, `ws_ping.py` |
| **1. Core assistant loop** | Perception → planner → safety → tools → memory → TTS | `agents/*`, `skills/{app_control,browser,file_ops,shell,web_search,screen_vision}`, LM Studio client, ChromaDB memory | `chat_e2e.py`, `agent_e2e.py` |
| **2. Voice** | Wake word, STT, TTS, hotkeys | openWakeWord, faster-whisper, Kokoro ONNX + SAPI fallback, `Ctrl+Alt+J` | `voice_e2e.py`, `wake_e2e.py`, `tts_wake_test.py`, `hotkey_e2e.py` |
| **Spec 29 §3 — Fast-Path Audio** | Pre-rendered acks, earcons | `core/audio_cache.py` (11 clips), `chat.js` Web-Audio earcons | `audio_cache_test.py`, `phase1_earcons_test.py` |
| **Spec 29 §3 — Dictation** | System-wide dictation + dictionary | `tools/dictation_injector.py`, `core/stt.py` vocabulary, `Ctrl+Alt+D`, Settings tabs | `vocab_test.py`, `injector_test.py`, `dictation_flow_test.py`, `dictation_ui_test.py` |
| **Spec 29 §3 — Fast Router** | Zero-LLM deterministic intents | `core/fast_router.py` (volume/media/power/timer/app), compound splitter, `rm_state` metrics | `fast_router_test.py` |
| **Spec 29 §4 — Hook Relay** | Coding-agent bridge | `bin/jarvis-hook.exe`, `backend/hook_bridge.py`, Claude/Antigravity installers, diff ticker | `hook_e2e.py` |
| **Spec 29 §5 — Presence** | Physics, states, dock, ingestion | `pet_springs.js` (RK4), 10-state mood machine, superellipse renderer, Dynamic Island (`dock.html`), file drop | `phase5_e2e.py`, `phase5_dock_check.py`, `phase5_visual_check.py` |
| **Spec 30 — UI revamp** | Cozy aesthetic, declared dock window, workspace polish | Hero mochi, sidebar fix, diff cards, `inspect_ui.ps1`, dock window declared in `tauri.conf.json` (fixed 0×0 host) | 15/15 gate + 16/16 captures |
| **Spec 30 §9 — 3D parity** | 3D matches 2D hero 1:1 | `SUPER_N 4.2→2.5`, bunny ears + glints, eyelid removal | `phase5_visual_check.py` (n=2.5 markers) |
| **Spec 31 — Switcher & polish** | 2D/3D engine, defect fixes, chat/settings UX | `pet2d.js`, `setRenderMode` + `runtime.pet_render_mode`, dock toggle, blush/lighting fixes, `ResizeObserver` resize, 820 px stream, strict single-tab settings | doc31 probe 20/20, 15/15 gate, 2D+3D captures |
| **Spec 32 (next)** | Memory Studio, tasks/reminders, input automation, onboarding | see [32-TASKS-MEMORY-AND-PRODUCT-SURFACES](./32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md) | pending |

## 22.2 Cadence Notes

- Specs are numbered documents in `docs/`; each spec = one implementation push (spec 29 was split across multiple commits, 30/31 one each).
- Every phase ended with the same ritual: full gate suite → `inspect_states.py` captures → visual review → commit as Ammar Hussain.
- Regression policy: gate markers live in `tests/` (and mirrored static checks); a phase is not "done" until the whole suite is green, not just the new tests.

## 22.3 Effort Shape (guidance for future phases)

- Wire-up phase (bus/topic/UI) ≈ hours; visual/physics phase ≈ dominated by capture-review iterations; specs with exact code blocks (29/30/31) implement fast, the cost is in verification.
- Budget rebuild cycles: `cargo build --release` ≈ 10–12 s incremental, but every asset edit requires it for the real app (mirror tabs are free).
