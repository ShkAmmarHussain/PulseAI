# 24. TROUBLESHOOTING (Known Issues & Fixes)

Field notes from real incidents. Check `backend.log` first: `%APPDATA%\JarvisDesktopPet\backend.log` (rotating, 1 MB).

## 24.1 Backend / IPC

| Symptom | Cause | Fix |
|---|---|---|
| Settings don't stick, YAMLs vanish/corrupt | `save_settings` **replaces the whole file** — a partial payload (e.g. `{"config": {"runtime": …}}` merged wrongly by a probe) wipes other keys | Always send the FULL settings object (clone `lastSettings`, mutate one key). Repair from `%APPDATA%\JarvisDesktopPet\config\config.yaml.corrupt-backup` |
| UI stuck "Connecting" | Backend not running | `Invoke-WebRequest http://127.0.0.1:8765/` → HTTP 404 = **up** (no root route); connection refused = down → run `backend\main.py` or relaunch the app (it spawns `jarvis-backend.exe`) |
| Killing the app also kills the backend | Backend is a child process | Expected; `taskkill /F /IM JarvisDesktopPet.exe /T` then relaunch respawns it |
| Two backends / port in use | Orphaned process after a crash | `Get-Process jarvis-backend` → kill extras; only one may own `:8765` |
| Replies missing for one window | Per-client 0.5 s send timeout dropped a slow client | Check that window reconnected (backoff ≤ 5 s); `jarvis:connected` event on `document` |
| LLM timeouts / error bubbles | LM Studio not running on `:1234` | Start LM Studio's local server; fast-path commands still work without it |
| `localhost` resolves to IPv6, LM Studio unreachable | IPv6 blackholing | Already handled: `core/llm.py` rewrites `localhost→127.0.0.1` — keep new clients doing the same |

## 24.2 Voice / Dictation

| Symptom | Cause | Fix |
|---|---|---|
| Mic dead after speaking | TTS echo guard | By design — `tts_state` mutes input until playback ends |
| No dictation into target app | Focus stolen or clipboard fallback failed | Click the target first; injector tries SendInput then Ctrl+V; history: `%LOCALAPPDATA%\Jarvis\dictation_history.jsonl` |
| Hotkey does nothing | Registered hotkey conflict (`Ctrl+Alt+J` id 1, `Ctrl+Alt+D` id 2) | Close the conflicting app; restart backend (hotkeys register at boot) |
| `CoInitialize`/COM crash in hotkey thread | Python COM apartment on reused thread | Fixed with `CoInitialize` wrap in `fast_router` volume control (commit `4bb6103`) — don't call `pycaw` from raw threads without it |
| Wake word too eager / deaf | Threshold drift | `voice.wake.threshold` (default 0.35), re-arm at 0.5×, 2 s cooldown |

## 24.3 UI / Tauri

| Symptom | Cause | Fix |
|---|---|---|
| Changed CSS/JS but app unchanged | Tauri embeds `distDir: ../src` at build time | `cargo build --release` in `ui_pet/src-tauri`, then copy **`target\release\jarvis-pet.exe`** → `test_install\JarvisDesktopPet.exe` (note: the build product is `jarvis-pet.exe`; a stale `JarvisDesktopPet.exe` may also sit in `target\release` — don't copy that one) |
| Dock window 0×0 / never renders | Dock declared but not visible / host size bug | Windows are declared in `tauri.conf.json` (`dock` starts `visible:false`, shown by `set_companion`); spec 30 fixed the standalone-host sizing |
| Pet invisible after mode switch | 3D layer booted hidden; renderer sized to fallback 176 px | `Pet3D.resize()` + `ResizeObserver` on `#pet` (doc 31) — if regressed, check console for resize errors |
| CDP `9335` empty | App launched without debug args | Set `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335 --allow-file-access-from-files` before launch |
| `Page.captureScreenshot` fails on mirror tabs | Inactive-tab capture limitation in this WebView2 | Verify visuals via `scripts\inspect_ui.ps1` on the real windows |
| Mirror tabs stale after edits | Mirror loads `file:///…/src/*` | Reload them (`revive_mirror.py`) or re-open |
| Settings bleed across sections | Regression of strict single-tab | `showSettingsTab` must set `display ""`/`"none"` only; fade-in class restarts animation |

## 24.4 Hooks / Safety

| Symptom | Cause | Fix |
|---|---|---|
| `jarvis-hook` no response | Pipe not up or exe missing | Backend creates `\\.\pipe\jarvis-hook` at boot; `_ensure_exe()` copies `bin/jarvis-hook.exe` → `%LOCALAPPDATA%\Jarvis\bin\`; check `hook_state` reply (`listening`, `exe_exists`) |
| Approval cards duplicated/stuck | Two settle paths racing | Settling is single-shot per cid (`_settle_approval`); timeouts: 45 s pipeline, 30 s hook (clamp 5–120 s) |
| Hook installer clobbered user config | Edit of `~/.claude/settings.json` | Installer writes `settings.json.jarvis-backup` first; `hook_uninstall` prunes only commands containing `jarvis-hook` |
| Unexpected auto-allow on shell | `bash_risk` read-only tier | Risk ≤1 answers instantly (`auto:true`); deadly regex (rm/format/sudo/…) → 9 → always card |

## 24.5 Repo / Git

| Symptom | Cause | Fix |
|---|---|---|
| Dozens of `M` files I never edited | LF/CRLF stat-only diffs | Stage explicit paths (`git add <file>`); never `git add -A` blindly |
| Wrong author on commits | Fresh clone without identity | Repo-local config: `Ammar Hussain <ammarhussain2199@gmail.com>` — never change it |
| `.commandcode/` keeps appearing | Local tool state | Leave untracked |
| Tests pass locally, fail in automation | Automation `python` missing / wrong env | Use `jarvis-desktop-pet\.venv\Scripts\python.exe` explicitly |

## 24.6 Diagnostics Toolkit

```powershell
Get-Content "$env:APPDATA\JarvisDesktopPet\backend.log" -Tail 100
Get-Process JarvisDesktopPet, jarvis-backend -ErrorAction SilentlyContinue
Invoke-WebRequest http://127.0.0.1:9335/json          # real windows (if debug args set)
& .venv\Scripts\python.exe tests\ws_ping.py           # fastest health check
```
