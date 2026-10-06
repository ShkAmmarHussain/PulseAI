# 17. FILE STRUCTURE (Complete Repo Layout)

Repo root: `D:\Personal_projects\2\Personal_AI` (git: PulseAI). App root: `jarvis-desktop-pet/`.

## 17.1 Repository Root

| Path | Purpose | Tracked |
|---|---|---|
| `docs/` | Numbered design docs `00-README.md` … `32-…` (specs, plans, this file) | yes |
| `jarvis-desktop-pet/` | The product (Python backend + Tauri frontend) | yes |
| `test_install/` | Installed build output: `JarvisDesktopPet.exe`, `jarvis-backend.exe`, `cache/` | ignored |
| `artifacts/` | Build/CI artifacts | mixed |
| `.commandcode/` | Local tool state (`taste/`) | **no — leave untracked** |
| `coucou/`, `hey-jev/` | Reference competitor projects | ignored |
| `temp_build/`, `build_log*.txt`, `*.wav` | Build/voice-test scratch | ignored |

## 17.2 `jarvis-desktop-pet/` — Python Side

| Path | Purpose |
|---|---|
| `backend/` | Process entry & OS integration |
| `backend/main.py` | Entry point; logs to `%APPDATA%\JarvisDesktopPet\backend.log` (rotating 1 MB) |
| `backend/app.py` | Composition root: builds bus, agents, voice, WS bridge, hook bridge, fast router |
| `backend/ws_bridge.py` | WebSocket protocol: 26 commands, 20 forwarded bus topics, settings persistence |
| `backend/voice_service.py` | Mic capture, VAD, faster-whisper STT, wake word, TTS ducking |
| `backend/hotkey_service.py` | Win32 `RegisterHotKey`: `Ctrl+Alt+J` (PTT), `Ctrl+Alt+D` (dictation) |
| `backend/hook_bridge.py` | Named-pipe server `\\.\pipe\jarvis-hook`, hook risk scoring, installers |
| `core/` | Infrastructure: `bus.py` (event bus), `config.py`, `llm.py` (LM Studio), `fast_router.py`, `guardrails.py` (risk), `stt.py` (vocabulary), `audio_cache.py`, `model_lifecycle.py`, `resources.py`, `autostart.py`, `state.py` |
| `agents/` | 10 registered agents: `orchestrator`, `perception`, `planner`, `safety`, `tool_control`, `memory_agent`, `vision`, `voice_tts`, `pet_ux`, `spawner` (+ `registry.py`) |
| `skills/` | Tool executors — 6 functional (`app_control`, `browser`, `file_ops`, `screen_vision`, `shell`, `web_search`), 8 placeholders, `registry.py`, `templates/` |
| `tools/dictation_injector.py` | Win32 SendInput text injection + JSONL history |
| `config/` | Bundled defaults: `config.yaml`, `agents.yaml`, `permissions.yaml`, `personality.yaml`, `skills.yaml`, `vocabulary.json`, `apps.json` |
| `tests/` | 18 plain-Python gate scripts (exit 0 = pass, no pytest) — see [23-TESTING](./23-TESTING.md) |
| `scripts/` | `setup.ps1`, `run-dev.bat`, `inspect_states.py`, `inspect_ui.ps1` |
| `bin/jarvis-hook.exe` | Shipped Rust CLI (source crate in `jarvis-hook/`) |
| `memory/chroma/` | ChromaDB persistence |
| `artifacts/ui_inspection/` | Visual captures: 8 default states + `pet3d/` (2D/3D renders) |
| `pyproject.toml`, `requirements.txt`, `jarvis-backend.spec`, `build.bat` | Deps & PyInstaller packaging |

## 17.3 `ui_pet/` — Tauri Frontend

| Path | Purpose |
|---|---|
| `package.json` | `vite`, `tsc`, `@tauri-apps/cli`, `three` (dev), `@tauri-apps/api` |
| `vite.config.ts` | Root `src`, outDir `../dist` (dev tooling only; Tauri serves `src` directly) |
| `src-tauri/tauri.conf.json` | Tauri v1: `distDir ../src`, windows `main`/`pet`/`dock`, tray, sidecar `binaries/jarvis-backend` |
| `src-tauri/src/main.rs` | 4 commands (`open_chat`, `open_settings`, `set_pet`, `set_companion`), tray, window positioning, backend spawn |
| `src/index.html` | Main shell: icon sprite, `pane-chat`/`pane-activity`/`pane-settings`, settings index |
| `src/app.css` | All styling (pet, dock, chat, approval cards, settings) |
| `src/ws.js` | Shared WS client `window.Jarvis` (`ws://127.0.0.1:8765/ws`) |
| `src/chat.js` | Chat pane, approval cards, procedural earcons, hook-diff ticker |
| `src/settings.js` | Settings form, strict single-tab `showSettingsTab`, dirty guard |
| `src/activity.js` | Activity timeline (filtered bus wildcard) |
| `src/main.js` | Tabs, sidebar collapse, dictation bubble, mic meter, companion mode |
| `src/pet.html` | Pet window: dual stage `#pet-2d` (SVG, default) + `#pet-3d` (WebGL), hover dock |
| `src/pet.js` | Pet controller: moods, bubbles, approvals, drag, file-drop, `setRenderMode` |
| `src/pet2d.js` | 2D animation engine (`window.Pet2D`): blink, saccade, squish, mood morphs |
| `src/pet3d.js` | Three.js renderer: superellipsoid body, springs, colorways, `Pet3D.resize` |
| `src/pet_springs.js` | RK4 `Spring`, `Taffy` drag physics, `volumeScales` |
| `src/vendor/three.module.js` | Vendored Three.js r170 |
| `src/dock.html` + `dock_standalone.js` | Dynamic Island window (240×36 → 460×150) |

## 17.4 Runtime Data (`%APPDATA%\JarvisDesktopPet\`)

`config/` (seeded from bundled `config/` on first run; `config.yaml`, `permissions.yaml`, `agents.yaml`, `personality.yaml`, `skills.yaml`, `vocabulary.json`), `models/` (Kokoro ONNX), `wakeword_models/`, `backend.log`.
