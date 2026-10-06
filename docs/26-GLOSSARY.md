# 26. GLOSSARY (Terms, Acronyms, Code Symbols)

## A–C

- **Approval card** — In-stream interactive card (`.approval-card`, alias `.chat-approval-card`) asking Allow once / Deny for actions with risk ≥ 6; also rendered on the pet. Sources: orchestrator safety, fast-path shutdown, terminal hook.
- **`apps.json`** — App-launcher mapping used by the fast router (`fast_path.app_open`); falls back to bundled defaults.
- **Audio cache** — `core/audio_cache.py`: 11 pre-rendered Kokoro WAVs (`ack.working`, `ack.done`, `ack.denied`, …) for sub-50 ms acknowledgments.
- **Bus (in-process)** — `core/bus.py`: asyncio pub/sub with per-topic queues, wildcard `"#"`, TTL 60 s, priority 5.
- **CDP** — Chrome DevTools Protocol; Edge instances on `:9334` (test mirror) and `:9335` (real app with debug args).

## D–H

- **Dirty guard** — Settings pattern: edits mark the form unsaved; explicit Save persists (`ownSaveAt` suppresses self-echo refetch).
- **Dictation injector** — `tools/dictation_injector.py`: Win32 SendInput UNICODE into the focused app, clipboard Ctrl+V fallback, JSONL history.
- **Dynamic Island** — The retractable top-edge dock window (`dock.html`, label `dock`, 240×36 ⇄ 460×150); companion alternative to the floating pet.
- **Earcons** — 8 procedural Web-Audio cues in `chat.js` (`snd_approval`, `snd_error`, …); gated by `voice.ui_sounds`.
- **`fast_path`** — `core/fast_router.py`: zero-LLM deterministic intent rules (volume/media/power/timer/app), `CONFIDENCE_MIN = 0.9`, compound splitting; metrics in `rm_state`.

## I–M

- **Ingestion** — Drag-and-drop of files onto pet/dock: `tauri://file-drop` → WS `file_ingest` → `ui.file_ingest` → composer prefill; pet plays a "crunch" particle animation.
- **IPC** — In this project both the in-process bus *and* the WS bridge; see [18-IPC_MESSAGE_BUS](./18-IPC_MESSAGE_BUS.md).
- **jarvis-hook** — Rust CLI (`bin/jarvis-hook.exe`) that relays coding-agent lifecycle/approval events over `\\.\pipe\jarvis-hook`; installers patch `~/.claude/settings.json` or `~/.gemini/config/hooks.json`.
- **Kokoro** — 82M ONNX TTS (`kokoro_onnx`, voice `af_heart`); fallback Windows SAPI.
- **LM Studio** — Local OpenAI-compatible server at `http://127.0.0.1:1234/v1` hosting role models from `agents.yaml`.

## N–R

- **Mochi** — The mascot: creamy dumpling with bunny ears (hero SVG in `index.html`, 2D engine `pet2d.js`, 3D `pet3d.js`).
- **Mood machine** — Pet states: `idle, sleep, listening, thinking, speaking, happy, poked, curious, approval, ingesting, dizzy…` exposed as `data-mood` on `#pet`.
- **`pet_render_mode`** — `runtime.pet_render_mode: "2d" | "3d"` in `config.yaml`; default `2d`; applied live via `window.setRenderMode(mode, persist)`.
- **Phonetic vocabulary** — `config/vocabulary.json` whole-word STT replacements (`kubectl` → "cube control") applied by `core/stt.py::apply_vocabulary()`.
- **Planner** — `agents/planner.py`: regex rule engine producing tool steps without an LLM.
- **Render budget** — Adaptive pet FPS: 60 active / 10 static / 1 hidden (`renderBudget` in `pet3d.js`).

## S–Z

- **Risk score** — `core/guardrails.py`: `AUTO 0, LOW 1, MEDIUM 3, HIGH 6, CRITICAL 8`; explicit map (`delete_file 9`, `run_shell 8`, `type_text 6`, `launch_app 2`, …); **allow iff max < 6**.
- **Session grant** — Remembered approval: hook key `agent:pid:tool` TTL 8 h; config-level `SessionGrants` exists but is unwired.
- **Sidecar** — `jarvis-backend.exe` declared as `bundle.externalBin`; spawned by `main.rs::setup()` from the exe directory.
- **Superellipse / `SUPER_N`** — Pet body geometry exponent (`2.5`) for the chubby squircle silhouette; `superellipsoid(rx, ry, rz, n, segs…)` in `pet3d.js`.
- **Taffy / Spring** — `pet_springs.js`: RK4 `Spring(stiffness, damping, …)` and `Taffy` drag with release; powers poke wobble and grab-and-drag.
- **Tauri (v1)** — Desktop shell: `main.rs` commands (`open_chat`, `open_settings`, `set_pet`, `set_companion`), tray, 3 declared windows.
- **TTFT/ack** — Stock spoken responses served from audio cache before any TTS synthesis.
- **VAD** — Voice activity detection: RMS threshold `voice.vad_threshold` (0.012), end at 1.2 s silence / 15 s max.
- **Wake word** — openWakeWord `hey jarvis`, threshold 0.35, 2 s cooldown; PTT hotkey `Ctrl+Alt+J`.
- **WS bridge** — `backend/ws_bridge.py`: 26 client commands, 20 forwarded bus topics, `ws://127.0.0.1:8765/ws`.
- **WS client** — `ui_pet/src/ws.js`: global `window.Jarvis`, reconnect backoff ≤ 5 s, outbox while closed, `jarvis:connected/disconnected` DOM events.
