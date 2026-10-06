# 18. IPC & MESSAGE BUS

Three transports, one vocabulary. Exact strings below match `core/bus.py`, `backend/ws_bridge.py`, `ui_pet/src/ws.js`, `backend/hook_bridge.py`.

## 18.1 Transports

| Layer | Tech | Endpoint | Code |
|---|---|---|---|
| In-process bus | asyncio pub/sub, per-topic queues | — (`ipc.use_inproc: true`) | `core/bus.py` |
| UI ⇄ backend | aiohttp WebSocket | `ws://127.0.0.1:8765/ws` | `backend/app.py`, `backend/ws_bridge.py` |
| CLI-agent hooks | Win32 named pipe (message mode) | `\\.\pipe\jarvis-hook` | `backend/hook_bridge.py` |
| LLM | OpenAI-compatible HTTP | `http://127.0.0.1:1234/v1` | `core/llm.py` |

Test-only: Edge CDP `http://127.0.0.1:9334/json` (visual gates), `:9335` (debugging the real app).

## 18.2 Envelopes

**Bus event** (`core/bus.py::Event`): `id` (uuid4), `topic`, `type`, `payload`, `timestamp`, `correlation_id?`, `ttl_ms` (60 000), `source?`, `target?`, `priority` (5). Wildcard topic `"#"`. Expired events are dropped on publish.

**Client → server** (JSON over WS):
```json
{ "type": "<command>", "payload": { }, "correlation_id": "abc" }
```

**Server → client** (two shapes, dispatched by `data.topic || data.type` in `ws.js`):
```json
{ "type": "<direct reply>", "payload": { }, "correlation_id": "abc" }
{ "topic": "<bus topic>",    "payload": { }, "correlation_id": "abc" }
```

## 18.3 WS Commands (client → backend, 26)

`text_input`, `approval_response`, `file_ingest`, `get_settings`, `save_settings`, `ping`, `test_lm_studio`, `set_pet`, `state`, `voice_listen`, `voice_wake`, `voice_devices`, `voice_device`, `tts_test`, `wake_test`, `autostart`, `autostart_state`, `rm_state`, `hook_state`, `hook_install`, `hook_uninstall`, `hook_terminal`, `dictation`, `dictation_history`, `vocabulary_get`, `vocabulary_save`

Direct reply types: `file_ingest`, `settings`, `settings_saved`, `pong`, `lm_test`, `voice_devices`, `voice_device_set`, `wake_test_ack`, `autostart_state`, `rm_state`, `hook_state`, `hook_install`, `hook_uninstall`, `hook_terminal`, `dictation_history`, `vocabulary`, `dictation_ack`.

**Settings flow (critical):** `save_settings` **replaces the whole YAML file** for each allowed key (`config`, `agents`, `permissions`, `personality`, `skills`) — clients must always send the full payload, never a partial subtree. Reply `settings_saved` → direct; then bus `settings.updated` and broadcast `ui.state {settings_saved: true}` to refresh other windows.

## 18.4 Bus Topics Forwarded to All UIs (20)

```
ui.pet_state  ui.chat  ui.approval  ui.state  ui.pet_visibility  ui.voice_state
ui.mic_level  ui.wake_test  ui.approval_cancelled  ui.file_ingest
tts_state  rm_state  tool.result  intent.fast_path
dictation.start  dictation.result  dictation.stop
agent.hook.session  agent.hook.diff  agent.hook.approval_request
```

Other published topics (internal, not forwarded): `input.text`, `input.voice`, `audio.input.voice`, `orchestrator.input`, `planner.request|result`, `safety.check|decision`, `tool.execute`, `memory.request|result|store`, `voice.say|interrupt`, `pet.state`, `ui.approval.response`, `settings.updated`, `spawner.result`, `ui.input.text`, `vision.request`.

## 18.5 Subscribers (by module)

| Subscriber | Subscribes |
|---|---|
| `backend/app.py` | `input.text`, `input.voice`, `settings.updated` |
| `backend/voice_service.py` | `tts_state`, `settings.updated` |
| `backend/hook_bridge.py`, `core/fast_router.py` | `ui.approval.response` |
| `agents/orchestrator.py` | `orchestrator.input`, `tool.result`, `safety.decision`, `memory.result`, `planner.result`, `ui.approval.response`, `orchestrator.handoff.orchestrator` |
| `agents/safety.py` / `planner.py` / `tool_control.py` / `memory_agent.py` / `vision.py` / `pet_ux.py` / `spawner.py` | `safety.check` / `planner.request` / `tool.execute` / `memory.request`, `memory.store` / `vision.request` / `pet.state` / `spawner.request` |
| `agents/voice_tts.py` | `voice.say`, `voice.interrupt`, `settings.updated` |
| `agents/perception.py` | `ui.input.text`, `audio.input.voice` |
| `backend/ws_bridge.py` | the 20 forwarded topics above |

Frontend `Jarvis.on(...)` usage: `pet.js`, `chat.js`, `settings.js`, `main.js`, `dock_standalone.js` (wildcard `*`), `activity.js` (wildcard, filtered).

## 18.6 Tauri Layer (separate from the bus)

- Commands (`window.__TAURI__.tauri.invoke`): `set_pet {visible}`, `set_companion {mode}`, `open_chat`, `open_settings`.
- Window events: `tauri://file-drop`, `tauri://file-drop-hover`, `tauri://file-drop-cancelled`, `tauri://move`.
- Rust → JS evals: `window.showTab(tab)`, `window.togglePetFromTray()`, `window.onCompanionChanged(mode)`.

## 18.7 Config Knobs (`ipc:` in `config.yaml`)

`max_queue_size: 1000`, `event_ttl_ms: 60000`, `use_inproc: true`.
