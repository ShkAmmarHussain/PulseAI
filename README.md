# PulseAI — Offline Desktop AI Companion

A fully local, voice-first desktop assistant that lives as a floating pet on your Windows desktop. Say **"Hey Jarvis"**, speak, and it listens, thinks, and talks back — no cloud required for voice, and the LLM runs on your own machine through [LM Studio](https://lmstudio.ai/).

Built with a **Tauri (Rust) UI** + a **Python async backend** connected over a WebSocket event bus.

---

## What it does

- **Wake word** — always-on local detection of "Hey Jarvis" (openWakeWord, ONNX, ~0 ms cloud).
- **Push-to-talk hotkey** — a global shortcut (default `Ctrl+Alt+J`, configurable in Settings → Voice) starts/stops listening from any app.
- **Start with Windows** — optional autostart (Settings → Desktop) opens Jarvis at login with the chat hidden; the pet and tray stay available.
- **Speech-to-text** — faster-whisper runs locally and transcribes what you say.
- **Local LLM** — answers come from a model you host in LM Studio (`http://localhost:1234`).
- **Neural text-to-speech** — Kokoro TTS (natural voices like `af_heart`), with Windows SAPI as a fast fallback.
- **Pip, your desktop companion** — a cream egg-shaped character with an antenna-sprout and a warm amber core light, in 2D (SVG) or 3D (WebGL). Pip follows its mood (idle, listening, thinking, speaking, happy, concerned, approval), can be dragged anywhere, catches dropped files, and has a hover dock (talk, chat, island mode, 2D/3D, settings).
- **Top-edge island** — an alternative to the floating pet: a thin strip at the top of the screen that opens into a compact pill, then into cards for the current task, approvals (Deny `N` / Allow `Y`), questions, results, errors and a quick inline chat.
- **Main window** — Chat, Activity (task cards and live timers), Memory (search, add, inline edit, forget/undo, export) and Settings, plus a first-run onboarding (Meet Pip → Microphone → Model).
- **Local or cloud models** — LM Studio by default; OpenAI or Anthropic Claude with your own key, with auto-routing of each task to a fast, heavy or vision model. Cloud keys are stored in **Windows Credential Manager**, never in the config files.
- **Multi-agent core** — planner / tool-control / perception / memory / safety agents route work through an in-process event bus.
- **Mini World** — a **World** tab where Pip (the Director) hands your requests to a team of chibi agents working in a 3D, 3-floor HQ building. You watch them plan, research, act and report, approve risky steps, create and delete your own agents, and add new skills that are safety-checked and run in a sandbox. On by default; turn it off in the World tab. See [docs/36](docs/36-MINI-WORLD-MULTI-AGENT-VISION.md).
- **PC control + vision** — skills for files, shell, browser, keyboard/mouse and screen understanding, gated by a permission/approval system with friendly action names and one risk level.
- **Tray app, single instance** — closing the window hides Jarvis to the tray (Pip keeps working); **Quit** in the tray menu or Settings → About ends the window and the background service together. Launching Jarvis again just brings the existing window back.
- **Everything local** — models, config, memory and logs live under `%APPDATA%\JarvisDesktopPet\`.

---

## How it works

```
┌────────────────────────── Tauri (Rust) ──────────────────────────┐
│  index.html  ── main window (chat, activity, memory, settings)   │
│  pet.html    ── always-on-top transparent pet, Pip (SVG/three.js)│
│  dock.html   ── top-edge island (alternative companion)          │
│        │  WebSocket  ws://127.0.0.1:8765/ws                      │
└────────┼─────────────────────────────────────────────────────────┘
         ▼
┌──────────────────────── Python backend ──────────────────────────┐
│  ws_bridge ── commands/settings  ←→  core.bus (event bus)        │
│                                                                  │
│  voice_service:                                                  │
│    mic → wake word → capture → whisper → bus → LLM → Kokoro → you│
│                                                                  │
│  agents: orchestrator, planner, tool_control, perception,        │
│          memory_agent, safety, vision, pet_ux, voice_tts          │
│  skills: shell, file_ops, browser, web_search, app_control       │
└──────────────────────────────────────────────────────────────────┘
         ▼
   LM Studio (local LLM) · whisper · openWakeWord · Kokoro · ONNX
```

**One voice turn, end to end:**

1. `voice_service` keeps a mic stream open and scores every 80 ms frame with openWakeWord.
2. Score crosses the threshold → state flips to **listening**, mic audio is buffered with an RMS VAD.
3. Silence → faster-whisper transcribes the buffer.
4. Text goes onto the bus → orchestrator/agents produce a reply through LM Studio.
5. Reply is spoken by Kokoro; while it plays the mic is suppressed so the pet never hears itself.
6. State returns to **listening** for the next "Hey Jarvis".

---

## Repository layout

```
Personal_AI/
├── docs/                     # Design docs: architecture, agents, models, safety…
├── jarvis-desktop-pet/
│   ├── backend/              # aiohttp WS server, voice_service, ws_bridge
│   ├── core/                 # bus, config, llm, orchestrator, guardrails
│   ├── agents/               # multi-agent implementations
│   ├── skills/               # shell, files, browser, web_search, app_control
│   ├── ui_pet/src/           # frontend served raw by Tauri (HTML/CSS/JS + three.js)
│   ├── ui_pet/src-tauri/     # Rust shell: windows, tray, sidecar launch
│   ├── tests/                # e2e suites (voice, wake, agent, chat, smoke)
│   ├── scripts/              # setup.ps1, run-dev.bat
│   ├── jarvis-backend.spec   # PyInstaller spec → sidecar .exe
│   └── build.bat             # full Windows installer build
└── README.md
```

---

## Setup on a new system

### Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Windows 10/11 | x64 | target platform (mic/PC-control skills) |
| Python | 3.12.x | backend + models |
| Node.js | 18+ | frontend + Tauri CLI |
| Rust | stable (`rustup`) | building the Tauri shell |
| VS Build Tools 2022 | with C++ workload + Windows SDK | `cargo` linker (vcvars64) |
| [LM Studio](https://lmstudio.ai/) | latest | local LLM server |

Optional but recommended: [`uv`](https://github.com/astral-sh/uv) for fast Python envs.

### 1. Clone

```powershell
git clone https://github.com/ShkAmmarHussain/PulseAI.git
cd PulseAI\jarvis-desktop-pet
```

### 2. Python environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

(Or with uv: `uv venv && uv pip install -r requirements.txt --python .venv\Scripts\python.exe`.)

Models download on first run and are cached under `%APPDATA%\JarvisDesktopPet\models\`:
whisper (`base`), openWakeWord (`hey jarvis`), Kokoro (`kokoro-v1.0.onnx` + voices).

### 3. Frontend + Tauri

```powershell
cd ui_pet
npm install
```

### 4. LM Studio

1. Install LM Studio, download a chat model (e.g. `qwen2.5-7b-instruct` GGUF).
2. Start the local server on **`http://localhost:1234`** (Developer > Local Server).
3. Verify: Settings > *Test LM Studio* inside the app.

### 5. Run in dev mode

```powershell
# terminal 1 — backend
.venv\Scripts\python.exe backend\main.py

# terminal 2 — UI
cd ui_pet
npm run tauri dev
```

or simply `scripts\run-dev.bat`.

### 6. Build the installer

```powershell
# 1) Python sidecar (only when backend code changed)
.venv\Scripts\python.exe -m PyInstaller jarvis-backend.spec --noconfirm
Copy-Item dist\jarvis-backend.exe ui_pet\src-tauri\binaries\jarvis-backend-x86_64-pc-windows-msvc.exe -Force

# 2) Full app (MSI + NSIS installers → ui_pet\src-tauri\target\release\bundle\)
build.bat          # writes ..\build_log.txt, ends with BUILD_OK / BUILD_FAILED
```

Notes:
- `build.bat` redirects `%TEMP%` to a **project-local folder on the same drive** — WiX CAB files overflow a full C: drive, so keep several GB free or edit those two lines.
- Frontend-only changes still need a full `build.bat` run: Tauri embeds `ui_pet/src/` into the exe (there is no `beforeBuildCommand`).
- Silent install: `JarvisDesktopPet_0.1.0_x64-setup.exe /S /D=C:\Path\To\Install`.

---

## Configuration

All config lives in `%APPDATA%\JarvisDesktopPet\`:

| File | Purpose |
|------|---------|
| `config\config.yaml` | LM Studio URL, voice (`stt_model`, `wake.threshold`, `device`, TTS), resource limits |
| `config\agents.yaml` | per-agent model ids + quantization |
| `config\permissions.yaml` | safety policy, approval timeouts |
| `config\personality.yaml` | name, wake word, voice style |
| `data\` | memory facts, tasks/timers, onboarding marker |
| `models\` | downloaded model weights |
| `backend.log` | runtime log (wake scores, mic device, TTS, errors) |
| `diagnostics\` | bundles from Settings → About → **Export diagnostics** (logs, settings with secrets redacted, model state) |

Settings can also be edited live in the app (**Settings** tab) — changes are written back to these files.

OpenAI / Anthropic API keys are **not** stored in `config.yaml`: they live in Windows Credential Manager as `PulseAI/llm.openai` and `PulseAI/llm.anthropic`, and the config only keeps a reference (`api_key_ref`). Keys that were typed into older versions are moved there automatically at startup. Use **Forget key** in Settings → Model to remove one.

Closing behaviour is set in Settings → Character & Desktop → **Keep running in the tray when closed** (on by default; off makes the ✕ button quit Jarvis completely).

---

## Voice setup (important on a laptop/dock)

1. Open **Settings → Voice**.
2. Pick your actual **Microphone** — Windows' *default* input is often a quiet/unplugged jack while you speak into a headset or webcam mic.
3. Watch the **Input level** meter while you talk: the bar must jump. (Green = voice detected.)
4. Press **Test "Hey Jarvis"** — it listens for 8 seconds and reports the wake model's peak score against your threshold, so you can tune with real numbers.
5. Adjust **Wake threshold** if it triggers too often (raise) or not at all (lower, e.g. `0.35`).
6. Press **Preview Voice** to confirm TTS works.
7. Optionally set a **Push-to-talk hotkey** (e.g. `ctrl+alt+j`) to toggle listening from anywhere, and enable **Start with Windows** under Settings → Desktop.

---

## Tests

Run from `jarvis-desktop-pet\` with the virtualenv active.

| Suite | Command | Needs |
|-------|---------|-------|
| TTS + wake model | `python tests\tts_wake_test.py` | – |
| Agent loop | `python tests\agent_e2e.py` | backend running |
| Voice pipeline | `python tests\voice_e2e.py` | **port 8765 free** (self-hosts) |
| Wake state machine | `python tests\wake_e2e.py` | **port 8765 free** (self-hosts) |
| Hotkey + autostart | `python tests\hotkey_e2e.py` | backend running (injects real keystrokes) |
| Smoke / WS ping | `python tests\smoke_test.py`, `python tests\ws_ping.py` | backend running |
| Accessibility (contrast, focus, wording) | `python tests\a11y_check.py` | – |
| Credential Manager + diagnostics | `python tests\credentials_test.py` | backend running for the export part |
| Pet performance (idle FPS, paused when hidden) | `python tests\perf_check.py` | real app with `--remote-debugging-port=9335` |
| Memory inline edit | `python tests\memory_update_test.py` | backend running |
| Mini World engine (state, plans, queue, runtime, Director, thinker/workers, agents, skills, service) | `python tests\world_<name>_test.py` (state, plan, brain, runtime, director, thinker, team, service, agents, skills) | – |
| Mini World UI logic | `node tests\world_store_test.mjs`, `node tests\world_looks_test.mjs` | – |
| Mini World on the real backend (on, off, live toggle) | `python tests\world_backend_e2e.py` | port 8799 free |
| Mini World with real models | `python tests\world_live_test.py` | LM Studio running (skips if not) |
| Full QA on the installed build | `python scripts\qa35_lifecycle.py`, `python scripts\qa35_surfaces.py` | `test_install\` built; see [docs/35](docs/35-FULL-QA-TEST-PLAN.md) |

`voice_e2e` and `wake_e2e` bind port `8765` themselves — stop any running backend first, and never run them in parallel. The full test inventory and gate practice are in [docs/23](docs/23-TESTING.md) and [docs/35](docs/35-FULL-QA-TEST-PLAN.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Hey Jarvis" never fires | Settings → Voice → check the **Input level** meter while speaking; pick another microphone; lower wake threshold; see `backend.log` (`wake live: score_max=…`) |
| No sound / meter flat | Windows Settings → Privacy → Microphone → allow desktop apps; check the device isn't muted in `sndvol` |
| No answers | LM Studio running on `localhost:1234` with a model loaded |
| No speech out | Settings → *Preview Voice*; first Kokoro run downloads ~300 MB |
| Build fails on MSI/`light.exe` | free up C: space / `build.bat` TEMP redirect; check `build_log.txt` |
| Backend port busy | `netstat -ano \| findstr :8765` then kill the stale PID. Current builds stop the backend when Jarvis quits or crashes, so this should only happen with older builds |
| Jarvis still running after closing the window | Expected: ✕ hides it to the tray. Use **Quit** (tray menu, or Settings → About), or turn off *Keep running in the tray when closed* |
| A bug report needs details | Settings → About → **Export diagnostics**, then attach the zip (API keys are removed) |

---

## Docs

Detailed design documentation lives in [`docs/`](docs/) — architecture, agents, orchestration, models, safety guardrails, memory, vision, and the IPC message bus. The latest product work: [34 — sleek revamp](docs/34-SLEEK-REVAMP-SPEC.md) (design tokens, island, Pip, production items) and [35 — full QA test plan and results](docs/35-FULL-QA-TEST-PLAN.md). Credits for adapted ideas are in [`jarvis-desktop-pet/ATTRIBUTIONS.md`](jarvis-desktop-pet/ATTRIBUTIONS.md).

## License

All rights reserved by the author — see the repository owner for licensing terms.
