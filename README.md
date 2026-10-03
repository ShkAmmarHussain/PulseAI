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
- **Floating 3D pet** — a small robot that follows its mood: idle, listening, thinking, speaking, happy, concerned. Drag it anywhere, right-click for quick actions.
- **Multi-agent core** — planner / tool-control / perception / memory / safety agents route work through an in-process event bus.
- **PC control + vision** — skills for files, shell, browser and screen understanding, gated by a permission/approval system.
- **Everything local** — models and config live under `%APPDATA%\JarvisDesktopPet\`.

---

## How it works

```
┌────────────────────────── Tauri (Rust) ──────────────────────────┐
│  index.html  ── main window (chat, settings)                     │
│  pet.html    ── always-on-top transparent 3D pet (three.js)      │
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
| `models\` | downloaded model weights |
| `backend.log` | runtime log (wake scores, mic device, TTS, errors) |

Settings can also be edited live in the app (**Settings** tab) — changes are written back to these files.

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

`voice_e2e` and `wake_e2e` bind port `8765` themselves — stop any running backend first, and never run them in parallel.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Hey Jarvis" never fires | Settings → Voice → check the **Input level** meter while speaking; pick another microphone; lower wake threshold; see `backend.log` (`wake live: score_max=…`) |
| No sound / meter flat | Windows Settings → Privacy → Microphone → allow desktop apps; check the device isn't muted in `sndvol` |
| No answers | LM Studio running on `localhost:1234` with a model loaded |
| No speech out | Settings → *Preview Voice*; first Kokoro run downloads ~300 MB |
| Build fails on MSI/`light.exe` | free up C: space / `build.bat` TEMP redirect; check `build_log.txt` |
| Backend port busy | `netstat -ano \| findstr :8765` then kill the stale PID |

---

## Docs

Detailed design documentation lives in [`docs/`](docs/) — architecture, agents, orchestration, models, safety guardrails, memory, vision, and the IPC message bus.

## License

All rights reserved by the author — see the repository owner for licensing terms.
