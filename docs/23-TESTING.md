# 23. TESTING (Suites, Gates, Visual Inspection)

## 23.1 Conventions

- **Plain scripts, no pytest.** Each test in `jarvis-desktop-pet/tests/` prints `PASS`/`FAIL` lines and exits `0` on success — automation runs them directly:
  ```powershell
  & .venv\Scripts\python.exe tests\fast_router_test.py; "exit=$LASTEXITCODE"
  ```
- Tests expect a **running backend** (`ws_ping.py` first) unless they boot `App` themselves.
- Browser-driven tests use **Edge CDP on :9334** (a "mirror" instance opened at `file:///…/ui_pet/src/*.html`); the real Tauri app is debuggable on `:9335` when launched with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9335 --allow-file-access-from-files`.
- Static "revamp marker" checks grep shipped files for required strings (`sheen`, `SUPER_N = 2.5`, `Allow once`, `showSettingsTab`, …) and forbidden ones (`#8e8cff`, `id="global-search"`, `dock-island`).

## 23.2 Suite Inventory (18 files)

| Test | Verifies |
|---|---|
| `smoke_test.py` | Imports: `MessageBus`, `load_config`, `ResourceTransitionManager`, `risk_score` |
| `ws_ping.py` | WS roundtrip `ping → pong` on `:8765` |
| `chat_e2e.py` | `text_input` → assistant `ui.chat` reply (60 s) |
| `agent_e2e.py` | Full pipeline: planner web-search reply; "open notepad" auto-allow (risk 2) + process check |
| `fast_router_test.py` | Rule table (volume/media/power/timer/app/compound) + WS e2e incl. shutdown approval, `rm_state` metrics |
| `vocab_test.py` | Phonetic vocabulary replacement engine (spec 29) |
| `injector_test.py` | Win32 dictation injector into a tkinter target |
| `dictation_flow_test.py` | Dictation e2e over WS: vocabulary, start/stop, injection, history, hotkey |
| `dictation_ui_test.py` | Settings dictionary/history UI via CDP |
| `audio_cache_test.py` | Pre-rendered acknowledgment cache (spec 29 §3.1) |
| `hotkey_e2e.py` | Synthesized `Ctrl+Alt+J` → `ui.voice_state` |
| `voice_e2e.py` | SAPI → WAV → faster-whisper transcript → TTS |
| `wake_e2e.py` | Drives wake model frames manually, asserts `voice_state` |
| `tts_wake_test.py` | Kokoro ONNX load/synthesize + voice id validation |
| `hook_e2e.py` | Named-pipe relay: session/diff events, PreToolUse approvals, installers + backup/restore |
| `phase5_e2e.py` | Pet file drag-drop → ingestion → composer prefill |
| `phase5_dock_check.py` | Dynamic Island wiring + CDP geometry/hover/drop |
| `phase5_visual_check.py` | Renderer: superellipse n=2.5, eye z-depth, RK4 poke/taffy, particles, FPS budget |
| `pet_springs_test.mjs` | Node unit checks for `pet_springs.js` (run with `node`) |

*(Phases 1–31 additionally used mirrored static checks — `revamp2_check.py`, `revamp2_interact.py`, `approval_flow_test.py` — kept beside the runner logs; `revamp2_interact` walks 56 DOM checks over CDP.)*

## 23.3 Visual Inspection (doc 30 §3 / §7)

```powershell
# 8 states across the three real windows → artifacts/ui_inspection/*.png
& .venv\Scripts\python.exe scripts\inspect_states.py      # expect: 16/16 inspection steps PASS
# single state
powershell -ExecutionPolicy Bypass -File scripts\inspect_ui.ps1 -State pet_idle
```
States: `pet_idle | pet_hover | pet_speech | pet_approval | dock_collapsed | dock_expanded | main_app_expanded | main_app_collapsed`. The driver parks the real cursor at the screen corner for clean idles, then captures with `CopyFromScreen`. **Always read the PNGs** — pixel-level review questions are in doc 30 §3.

Render-mode captures: flip `runtime.pet_render_mode` (full-settings save!), run `inspect_ui.ps1 -State pet_idle -OutputDir artifacts\ui_inspection\pet3d`, restore `2d`.

## 23.4 Gate Practice

- Run the whole suite after any change to `backend/`, `agents/`, or UI markers; target is **all 18 exit 0**.
- Known-flaky classes: CDP screenshot of inactive tabs (`Page.captureScreenshot` breaks — verify on real windows instead), single-shot reads against 10 FPS idle rendering (use peak sampling), approval cids (capture the cid from the bus, don't hardcode).
- Frontend syntax gate: `node --check` each edited `.js` (modules: copy to a `.mjs` temp file first).

## 23.5 Performance/Safety Assertions

- Idle render throttling: 60 FPS active / 10 FPS static / 1 FPS hidden (`renderBudget` in `pet3d.js`).
- Risk gate: allow iff `max(risk_score) < 6`; approval timeout 45 000 ms (hook cards 30 s).
- Offline/privacy: kill the network — voice, STT, local inference, PC actions, dictation must keep working (spec 29 §9).
