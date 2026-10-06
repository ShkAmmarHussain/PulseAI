# 20. SETUP (Windows, LM Studio, First Run)

## 20.1 Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10/11 x64 | Win32 APIs used: named pipes, `RegisterHotKey`, SendInput, COM |
| Python ≥ 3.10 | `.venv` created by `scripts/setup.ps1` |
| Node.js 18+ | Tauri CLI + Vite (dev typecheck only) |
| Rust stable + VS 2022 BuildTools | `cargo` on PATH; `build.bat` invokes `vcvars64.bat` |
| WebView2 Runtime | Bundled with Windows 11 / Evergreen on 10 |
| **LM Studio** running | Local server at `http://localhost:1234/v1` with models from `config/agents.yaml` (`qwen3-8b`, `qwen2.5-coder-7b-instruct`, `qwen2.5-vl-7b-instruct`, `llama-3.2-3b-instruct`, …) |

## 20.2 Dev Setup

```powershell
# 1. Python env
cd jarvis-desktop-pet
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#    → python -m venv .venv; pip install -r requirements.txt

# 2. First run (two consoles, or use run-dev.bat)
scripts\run-dev.bat
#    console A: python backend\main.py     → WS ws://127.0.0.1:8765/ws
#    console B: cd ui_pet && npm run tauri dev
```

Config in dev is read from the bundled `jarvis-desktop-pet/config/`.

## 20.3 Production Build

```powershell
build.bat      # vcvars64 + cargo PATH + `npm run tauri build`, log → build_log.txt
```

Outputs `ui_pet\src-tauri\target\release\jarvis-pet.exe` (binary name) — **copy/rename to `JarvisDesktopPet.exe` when deploying to `test_install\`** next to `jarvis-backend.exe` (sidecar from `src-tauri/binaries/`). Tauri embeds `src/` via `distDir`, so **every HTML/CSS/JS edit requires a rebuild** (mirror tabs opened at `file:///…/ui_pet/src/` show edits immediately).

## 20.4 First Run (Installed)

1. `setup()` in `main.rs` spawns `jarvis-backend.exe` from the exe directory (dev mode spawns nothing — backend runs from source).
2. Backend seeds `%APPDATA%\JarvisDesktopPet\config\` from the bundled `config/` on first run (subsequent edits happen there, **not** in the repo copy).
3. Three windows come up: `main` "Jarvis" (1100×760), `pet` "Jarvis Pet" (360×360, transparent, bottom-right), `dock` hidden (240×36, top center).
4. Verify: settings → *Test LM Studio*; chat a trivial prompt; mic hotkey `Ctrl+Alt+J`.

## 20.5 Ports & Endpoints (nothing else listens)

| Endpoint | Purpose |
|---|---|
| `127.0.0.1:8765/ws` | UI ↔ backend WebSocket |
| `localhost:1234/v1` (+ `/api/v1/models/*`) | LM Studio |
| `\\.\pipe\jarvis-hook` | Hook relay (created on demand) |
| `127.0.0.1:9334` / `:9335` | Browser CDP — **tests/debug only** (launch app with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335`) |

## 20.6 Autostart

Settings → toggle (or HKCU `…\Run\JarvisDesktopPet` = `"…\JarvisDesktopPet.exe" --hidden`, frozen only). `--hidden` starts with the main window hidden; tray menu restores it.

## 20.7 Health Check

```powershell
& .venv\Scripts\python.exe tests\ws_ping.py     # expect: pong
& .venv\Scripts\python.exe tests\chat_e2e.py    # expect: assistant ui.chat reply
Get-Content "$env:APPDATA\JarvisDesktopPet\backend.log" -Tail 50
```
