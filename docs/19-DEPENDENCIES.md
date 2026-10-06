# 19. DEPENDENCIES (All Packages & Rationale)

## 19.1 Python Runtime (`jarvis-desktop-pet/pyproject.toml`, requires-python ≥ 3.10)

Lower-bound pins only. Grouped by role:

| Package | Why |
|---|---|
| `pydantic>=2.9` | Config/event validation |
| `pyyaml>=6.0.2` | YAML configs (`config/`, `%APPDATA%` copies) |
| `aiofiles>=24.1.0` | Async file IO in the event loop |
| `httpx>=0.27.2` | Async HTTP utilities |
| `openai>=1.52.0` | LM Studio OpenAI-compatible client (`core/llm.py`) |
| `aiohttp>=3.10.5` | WebSocket **server** (WS bridge on :8765) |
| `smolagents>=1.2.2` | Declared agent framework (agents are hand-rolled on `core/bus.py`) |
| `faster-whisper>=1.0.3` | STT — Whisper `base`, CPU int8 |
| `kokoro>=0.9.2` | TTS family (runtime actually loads **`kokoro_onnx`** ONNX) |
| `sounddevice>=0.5.0` | Mic input / speaker output streams |
| `numpy>=1.26.4` | Audio buffers |
| `openwakeword>=0.6.0` | "Hey Jarvis" wake word (ONNX) |
| `mss>=9.0.2` | Fast screenshots for vision |
| `rapidocr-onnxruntime>=1.4.4` | OCR pipeline |
| `Pillow>=10.4.0` | Image handling |
| `chromadb>=0.5.15` | Vector memory (`memory/chroma`) |
| `pyautogui>=0.9.54`, `pynput>=1.7.7` | PC control / input simulation |
| `pywin32>=306` (Windows) | Named pipes, `RegisterHotKey`, SAPI/COM |
| `rich>=13.9.2`, `loguru>=0.7.2`, `python-dotenv>=1.0.1` | Logging & utilities |

`requirements.txt` additionally (not in pyproject): `pycaw>=20240210` (volume/media keys — fast path), `pypdf>=6.0.0` (PDF summarization), commented `asyncio-mqtt`.

**Undeclared runtime imports** (present in the environment, missing from both files): `ddgs` (`skills/web_search.py`), `kokoro_onnx` (TTS), `winsound` (stdlib), `pythoncom` (COM STA). Install/`requirements.txt` should grow these eventually — see [25-ROADMAP](./25-ROADMAP.md).

## 19.2 Rust (`ui_pet/src-tauri/Cargo.toml`)

| Crate | Why |
|---|---|
| `tauri = "1.6"` (`system-tray`, `api-all`) | App shell, windows, tray, IPC |
| `serde = "1"` + `serde_json = "1"` | Command/serialization |
| `tauri-build = "1.5"` (build) | Asset embedding (`distDir: ../src`) |

`jarvis-hook/` crate: `serde_json` only; release profile `strip`, `lto`, `opt-z = "z"` for a small CLI.

## 19.3 Frontend (`ui_pet/package.json`)

Dev: `vite ^5.4`, `typescript ^5.5`, `@tauri-apps/cli ^1.6`, **`three ^0.170`** (source for the vendored `src/vendor/three.module.js` — the app itself never runs Vite). Runtime: `@tauri-apps/api ^1.6`. `npm run build` = `tsc && vite build` (CI-style check; Tauri serves `src/` raw).

## 19.4 Vendored / Model Artifacts (not package-managed)

- `ui_pet/src/vendor/three.module.js` — Three.js r170 snapshot.
- `%APPDATA%\JarvisDesktopPet\models\` — `kokoro-v1.0.onnx` + `voices-v1.0.bin` (Kokoro 82M).
- `%APPDATA%\JarvisDesktopPet\wakeword_models\` — `hey jarvis` openWakeWord model.
- `jarvis-desktop-pet/bin/jarvis-hook.exe` — prebuilt Rust binary (source in `jarvis-hook/`).
- `ui_pet/src-tauri/binaries/jarvis-backend-x86_64-pc-windows-msvc.exe` — PyInstaller sidecar (~190 MB, git-ignored).

## 19.5 Version Sensitive Notes

- Tauri is **v1** (v1 config schema, `tauri::command`, `withGlobalTauri`) — do not mix v2 snippets.
- LM Studio endpoint `localhost:1234` is rewritten to `127.0.0.1` in `core/llm.py` (IPv6 blackhole avoidance); `api_key: dummy`.
- `kokoro>=0.9.2` pip package is declared for provenance, but synthesis goes through `kokoro_onnx.Kokoro(...)`.
