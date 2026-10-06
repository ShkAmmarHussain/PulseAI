# 21. IMPLEMENTATION (Build Order, Patterns, Checkpoints)

How this codebase is wired and how to extend it without breaking the gates. Read with [03-PIPELINE](./03-PIPELINE.md) and [18-IPC_MESSAGE_BUS](./18-IPC_MESSAGE_BUS.md).

## 21.1 Composition Root

Everything is constructed in `backend/app.py::App.start()` in this order: config → `MessageBus` → resource/model managers → agents (`agents/registry.py::AGENTS`) → `VoiceService` → `WSBridge` (+ `wire_bus()`) → `HookBridge` → `HotkeyService` → `FastRouter` → bus start → aiohttp WS server. New subsystems belong in this sequence; tests assume it.

## 21.2 Extension Patterns

**Add a bus topic**
1. `bus.publish(create_event("topic.name", "type", payload))` in the producer.
2. If a UI must see it: add `"topic.name"` to `WSBridge.wire_bus()` in `backend/ws_bridge.py`.
3. Subscribe in the consumer's `start()`: `bus.subscribe("topic.name", self.on_x)`.
4. Frontend: `Jarvis.on("topic.name", handler)` in the relevant `ui_pet/src/*.js`.
5. Add/extend a gate test (WS-level assertion, not a DOM-only assertion).

**Add a WS command**
- Handle it in `ws_bridge.py::_dispatch` (switch on `type`), reply with `_send({"type": reply, "payload", "correlation_id"})`, and add a `Jarvis.send`/helper in `ws.js`.

**Add a settings key**
- Allowed top-level files for `save_settings`: `config`, `agents`, `permissions`, `personality`, `skills` only. **The whole file is replaced** — the client must clone its last known good settings, mutate one key, and send everything (`settings.js` pattern: `ownSaveAt` guard + `settings_saved` fill).
- Read it in Python via `core/config.py` `load_config()`; broadcast reaches other windows through `settings.updated` → `ui.state {settings_saved: true}`.

**Add a Tauri command**
- `#[tauri::command] fn …` in `ui_pet/src-tauri/src/main.rs` → register in `tauri::generate_handler![…]` → call via `window.__TAURI__.tauri.invoke("name", args)` (helper `tcmd` in `main.js`).

**Add a skill**
- Module in `skills/`, entry in `config/skills.yaml`, route from `agents/tool_control.py` on `tool.execute`; give the action a `core/guardrails.py::risk_score` mapping (≥6 forces the approval card).

## 21.3 Frontend Conventions

- Plain JS, no framework; one shared client (`window.Jarvis`); panes are plain DOM sections toggled by `showTab`.
- Settings sections: strict single-tab via `window.showSettingsTab(tab)` — active section `display: ""`, others `"none"` (no stacked scroll bleed).
- Chat stream: `#msgs > *` centered `min(820px, 100%)`; user = indigo pill (right), assistant = warm card `rgba(26,28,34,.85)` (left) with mochi avatar (`#i-mochi` sprite); approval = `.approval-card chat-approval-card` in-stream.
- Pet: dual layers — `#pet-2d` (SVG default, `window.Pet2D`) and `#pet-3d` (WebGL, `window.Pet3D`); switch with `window.setRenderMode(mode, persist)`; persist via `runtime.pet_render_mode` in config. `Pet3D` self-heals size via `ResizeObserver` (it may boot `display:none`).
- **Forbidden markers (tests assert absence):** `#8e8cff`, `id="global-search"`, `dock-island`.

## 21.4 Checkpoints (what "done" looks like)

| Checkpoint | Command |
|---|---|
| Static revamp markers | `python %TEMP%\opencode\revamp2_check.py` (mirrors: grep markers in shipped files) |
| Bus behavior | `tests/fast_router_test.py`, `tests/chat_e2e.py`, `tests/hook_e2e.py` |
| Voice/dictation | `tests/dictation_flow_test.py`, `tests/dictation_ui_test.py`, `tests/hotkey_e2e.py` |
| Pet/dock visuals | `tests/phase5_visual_check.py`, `tests/phase5_dock_check.py`, `tests/phase5_e2e.py` |
| Render captures | `python scripts\inspect_states.py` (16/16) → review PNGs in `artifacts/ui_inspection/` |
| Full gate | run all 18 `tests/*.py`; exit 0 each (see [23-TESTING](./23-TESTING.md)) |

## 21.5 Rules of Thumb

- Commit with author **Ammar Hussain <ammarhussain2199@gmail.com>** (repo-local config); stage explicit paths — a sea of phantom `M` files is CRLF noise, not real changes.
- Use the venv python (`D:\…\jarvis-desktop-pet\.venv\Scripts\python.exe`); bare `python` may not exist.
- Detached launch helpers via `Popen(creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP)`; avoid `Start-Process -RedirectStandard*` in automation.
- Probe scripts that read settings must use `(payload or {}).get("config")` (envelope shape).
