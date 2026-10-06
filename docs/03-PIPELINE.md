# 03. PIPELINE (End-to-End Data Flow)

How an utterance travels from input to response, as shipped in `backend/`, `core/`, `agents/`.

## 3.1 Transport Layers

```
 Tauri Windows (WebView2)                Python Backend (jarvis-backend.exe)
 ┌──────────────────────────┐            ┌──────────────────────────────────────────┐
 │ main  "Jarvis"           │  WebSocket │ backend/app.py  (composition root)       │
 │ pet   "Jarvis Pet"       │◄──────────►│   ws://127.0.0.1:8765/ws                │
 │ dock  "Dynamic Island"   │  :8765     │ core/bus.py     (asyncio pub/sub)        │
 └──────────────────────────┘            │ agents/*        (10 registered agents)   │
                                          │ skills/*        (tool executors)        │
 Terminal CLIs (claude/antigravity)       └───────────────┬──────────────────────────┘
   jarvis-hook.exe ── named pipe ──► backend/hook_bridge.py│
                                                            ▼
                                            LM Studio  http://127.0.0.1:1234/v1
```

Two event layers: the **in-process bus** (`core/bus.py`, asyncio per-topic queues, TTL 60 s) and the **WS bridge** (`backend/ws_bridge.py`) which forwards 20 bus topics to every UI client and dispatches 26 client commands back onto the bus.

## 3.2 Text / Voice Request Lifecycle

1. **Entry**
   - Chat: WS `text_input` → bus `ui.input.text`.
   - Voice: `backend/voice_service.py` mic stream (16 kHz, 80 ms frames) → VAD (RMS 0.012, 1.2 s end-silence, 15 s cap) → **faster-whisper** (`base`, cpu int8) → `core/stt.py::apply_vocabulary()` phonetic fixups → bus `audio.input.voice`.
   - Wake: **openWakeWord** `hey jarvis`, threshold 0.35, 2 s cooldown, hotkey fallback `Ctrl+Alt+J`.
2. **Perception** (`agents/perception.py`): normalizes both into `input.text` / `input.voice`.
3. **Fast path** (`backend/app.py::on_input` → `core/fast_router.py`): deterministic rules (`CONFIDENCE_MIN = 0.9`) for volume/media/power/timer/app-launch, compound splitting on `and|then|;`. If handled → publishes `intent.fast_path` + `ui.chat` + `voice.say` and **never touches the LLM**. Shutdown requests open an approval card (risk 9) first.
4. **Orchestrator** (`agents/orchestrator.py`): echoes the user bubble (`ui.chat`), decides plan-vs-remember (>8 words or action keywords → `planner.request`, else `memory.request`), and emits the cached *"Working on that now."* ack.
5. **Planner** (`agents/planner.py`, regex rules, no LLM): emits steps (`launch_app`, `run_shell`, `summarize_file`, `vision_describe`, `type_text`, `respond`, …).
6. **Safety** (`agents/safety.py` + `core/guardrails.py`): `risk = max(risk_score(step))`; **allow iff risk < 6**, else `safety.decision = deny`.
7. **Approval branch**: orchestrator publishes `ui.approval` (45 s timeout, single in-flight) and stashes steps; WS `approval_response` → bus `ui.approval.response` settles it once (Allow → `tool.execute`, Deny → refusal chat). Fast-path shutdown and the terminal hook run the same card path with their own cids.
8. **Execution** (`agents/tool_control.py` → `skills/{app_control,browser,file_ops,screen_vision,shell,web_search}.py`) → `tool.result {ok, summary, steps}`.
9. **Result fan-out**: orchestrator stores to memory (`memory.store`, ChromaDB at `memory/chroma`), renders the reply (`ui.chat`), and speaks it (`voice.say`).
10. **TTS** (`agents/voice_tts.py`): `pet.state {type:"speak"}` first (bubble), then audio-cache hit (`core/audio_cache.py`, 11 pre-rendered WAVs) → **Kokoro ONNX** (`af_heart`) → SAPI fallback; publishes `tts_state` which mutes the mic (echo suppression).

## 3.3 Side Paths

- **Hook relay**: `jarvis-hook.exe` → `\\.\pipe\jarvis-hook` → `backend/hook_bridge.py` → `agent.hook.session|diff|approval_request` (+ mirrored `ui.chat` diff lines and `ui.approval` cards; replies travel back over the pipe). Shell risk: deadly regex → 9, read-only → 1 (auto-allow), else 4.
- **Dictation**: `Ctrl+Alt+D` or voice phrase → `tools/dictation_injector.py` (SendInput UNICODE, clipboard Ctrl+V fallback) → `dictation.start|result|stop` + JSONL history.
- **File drop**: `tauri://file-drop` on pet/dock → WS `file_ingest` → `ui.file_ingest` → composer prefill.

## 3.4 Failure & Timing Behavior

- LLM call: `openai` client, 30 s timeout, 3 retries; LM Studio down → error bubble, fast path still works.
- WS client drop: server keeps broadcasting (per-client 0.5 s send timeout); frontend reconnects with `min(1000·retry, 5000)` ms backoff and a bounded outbox.
- Events expire after `ipc.event_ttl_ms` (60 000); queue capped at `ipc.max_queue_size` (1000).
- Boot order: config → bus → agents → voice → WS bridge → hotkeys → fast router → bus start → WS listen.
