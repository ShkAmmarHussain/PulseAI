# 32. SPECIFICATION: TASKS, MEMORY & EXPANDED PRODUCT SURFACES

**Document:** `docs/32-TASKS-MEMORY-AND-PRODUCT-SURFACES.md`  
**Target Agent:** `opencode` / `Claude Code`  
**Purpose:** Implementation blueprint to transition Jarvis from a conversational desktop pet into a full-featured personal AI command center by implementing:
1. **Persistent Memory & Memory Studio UI** (storing, browsing, editing, and deleting learned facts).
2. **Tasks, Reminders & Automations** (scheduled routines, timers, background job tracking).
3. **PC Input Automation** (`skills/input_control.py` keyboard/mouse execution with safety gating).
4. **First-Run Onboarding Flow** (warm introductory setup modal for companion, audio, and models).  
**Parent Documentation:** [02-ARCHITECTURE.md](file:///d:/Personal_projects/2/Personal_AI/docs/02-ARCHITECTURE.md), [12-MEMORY.md](file:///d:/Personal_projects/2/Personal_AI/docs/12-MEMORY.md), [13-PC_CONTROL.md](file:///d:/Personal_projects/2/Personal_AI/docs/13-PC_CONTROL.md), [27-UI-REVAMP.md](file:///d:/Personal_projects/2/Personal_AI/docs/27-UI-REVAMP.md), [29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md](file:///d:/Personal_projects/2/Personal_AI/docs/29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md)

---

## 1. Executive Summary & Missing Surfaces Analysis

With the **Revamp Line (Docs 27–31)** complete, Jarvis possesses an Apple-grade presentation:
* A responsive **2D Vector Mochi** and **3D WebGL** dual companion with live switching.
* A retractable **Dynamic Island** top-edge dock.
* A centered, comfortable **820px Chat Stream** with rich approval dialogs and Mochi avatars.
* A strictly isolated **Settings Pane**.

### The Remaining Gap
While the presentation layer is complete, the following core capabilities from `00-README.md` and `27-UI-REVAMP.md` remain stubs or placeholders:
```
┌───────────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────────────┐
│     1. MEMORY ENGINE & STUDIO         │     2. TASKS & AUTOMATIONS            │     3. PC INPUT AUTOMATION            │
├───────────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────────────┤
│ • skills/memory_skills.py is empty.   │ • skills/task_manager.py is empty.    │ • skills/input_control.py is empty.   │
│ • No persistent storage of facts      │ • No reminders or scheduled cron jobs.│ • No mouse click / key typing skills. │
│   (user prefs, projects, habits).     │ • Activity tab only shows live logs.  │ • Safety guardrails exist, but skills │
│ • No UI to inspect or forget memory.  │ • No visual queue of background jobs. │   aren't wired for mouse/keyboard.    │
└───────────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Component 1: Persistent Memory & Memory Studio UI

### 2.1 Backend Memory Store (`core/memory_store.py` & `skills/memory_skills.py`)
Replace the placeholder with a lightweight, robust JSON/SQLite-backed memory store located at `data/memory.json`.

#### Schema
```json
{
  "profile": {
    "user_name": "Ammar",
    "preferred_language": "Python",
    "timezone": "Asia/Karachi"
  },
  "facts": [
    {
      "id": "mem_1740001",
      "category": "preferences",
      "content": "Prefers dark mode, concise explanations, and minimal sci-fi metaphors.",
      "created_at": "2026-10-06T20:00:00Z",
      "confidence": 0.95
    },
    {
      "id": "mem_1740002",
      "category": "projects",
      "content": "Working on Jarvis Desktop Pet in d:\\Personal_projects\\2\\Personal_AI.",
      "created_at": "2026-10-06T20:05:00Z",
      "confidence": 0.98
    }
  ]
}
```

#### Memory Operations & Events:
* `memory.list` (Request: `{}` $\rightarrow$ Response: `{ "profile": {...}, "facts": [...] }`)
* `memory.add` (Request: `{ "category": "preferences", "content": "..." }`)
* `memory.delete` (Request: `{ "id": "mem_1740001" }`)
* `memory.clear` (Request: `{}`)
* **Auto-Extraction:** After a chat turn, the `MemoryAgent` can optionally extract long-term facts using a lightweight 1-token check, proposing them via `memory.add`.

### 2.2 Memory Studio UI (`#pane-memory`)
Add a dedicated **Memory** tab to the primary desktop sidebar between `Activity` and `Settings`:

```html
<nav id="nav" aria-label="Primary">
  <button class="nav-item active" data-tab="chat"><svg class="ic"><use href="#i-chat"/></svg><span class="nav-label">Chat</span></button>
  <button class="nav-item" data-tab="memory"><svg class="ic"><use href="#i-brain"/></svg><span class="nav-label">Memory</span></button>
  <button class="nav-item" data-tab="activity"><svg class="ic"><use href="#i-activity"/></svg><span class="nav-label">Activity</span></button>
  <button class="nav-item" data-tab="settings"><svg class="ic"><use href="#i-sliders"/></svg><span class="nav-label">Settings</span></button>
</nav>
```

#### Memory Studio View Layout:
* **Header:** Search filter input + "Add Fact" button + "Export / Clear All" actions.
* **Category Filters:** `All`, `Preferences`, `Projects`, `Workflows`, `People`.
* **Memory Cards:** Clean cards displaying:
  - Category badge (e.g. `[Preferences]` in subtle purple).
  - Fact content.
  - Timestamp.
  - Quick action: "Forget / Delete" trash icon with instant undo toast.

---

## 3. Component 2: Tasks, Reminders & Scheduled Automations

### 3.1 Backend Scheduler (`skills/task_manager.py` & `skills/notify.py`)
Implement the scheduler engine using `asyncio` background tasks with persistent state saved in `data/tasks.json`.

#### Supported Task Types:
1. **Reminders / Timers:**
   - Command: *"Remind me in 15 minutes to take a break."*
   - Execution: Sleeps asynchronously, triggers high-priority floating bubble on the Pet window, plays `snd_wake` audio chime, and raises a Windows tray toast.
2. **Recurring Automations (Cron-style):**
   - Command: *"Check my system memory every 30 minutes."*
   - Execution: Periodic task execution that logs results to the Activity pane.
3. **Background Shell / Tool Jobs:**
   - Multi-step tasks that run in the background without blocking the chat loop.

#### WebSocket Events:
* `tasks.list` $\rightarrow$ Returns active, scheduled, and past tasks.
* `tasks.create` $\rightarrow$ `{ "type": "reminder", "title": "...", "due_timestamp": 1740000000 }`
* `tasks.cancel` $\rightarrow$ `{ "task_id": "tsk_01" }`

### 3.2 Tasks & Activity UI (`#pane-activity` Expansion)
Enhance the existing `#pane-activity` to feature a dual-view:
* **Tab 1: Active Tasks & Reminders:** Live countdown pills (e.g. `[Break Reminder - 12m remaining] [Cancel]`).
* **Tab 2: Execution History / Logs:** Chronological timeline of tools executed, files modified, and approvals granted.

---

## 4. Component 3: PC Input Automation (`skills/input_control.py`)

### 4.1 Safe Native Input Execution
Implement mouse and keyboard automation via `pyautogui` / `pynput` with strict safety boundaries.

#### Capabilities:
* `type_text(text: str)`: Types text into currently focused input field.
* `press_hotkey(keys: list[str])`: Executes system combinations (e.g., `["ctrl", "c"]`).
* `click(x: int, y: int, button: str = "left", clicks: int = 1)`: Clicks coordinates on screen.
* `move_mouse(x: int, y: int)`: Smooth cursor movement.

#### Safety Guardrails (Spec 14 §3):
* **Failsafe:** Moving the mouse to the top-left screen corner (`(0, 0)`) immediately aborts execution.
* **Risk Score:** Any input automation has an automatic risk score of **7/10** (Medium-High) and requires explicit approval via the interactive approval card unless policy is set to `autonomous`.

---

## 5. Component 4: First-Run Onboarding Flow

When `runtime.first_run: true` (or on initial start), display a polished 3-step setup modal over `index.html`:

```
┌─────────────────────────────────────────────────────────────────┐
│                      WELCOME TO JARVIS                          │
│                                                                 │
│   [ 2D / 3D Animated Mochi Mascot Preview ]                     │
│                                                                 │
│   Step 1: Meet Your Companion                                   │
│   Choose your pet style: [ 2D Vector Mochi ]  [ 3D WebGL ]      │
│                                                                 │
│   Step 2: Microphone & Audio Check                              │
│   Speak "Hey Jarvis" -> Live visualizer pulse check             │
│                                                                 │
│   Step 3: Local Model Verification                              │
│   LM Studio endpoint: [ http://127.0.0.1:1234/v1 ]  (Connected) │
│                                                                 │
│   [ Start Exploring Jarvis -> ]                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Checklist for `opencode`

| Order | Subsystem | Target Files | Key Actions |
| :---: | :--- | :--- | :--- |
| **1** | **Memory Engine** | `core/memory_store.py`<br>`skills/memory_skills.py` | Implement JSON-backed store (`data/memory.json`), recall injection into `ContextBundle`, and event listeners. |
| **2** | **Memory Studio UI**| `ui_pet/src/index.html`<br>`ui_pet/src/app.css`<br>`ui_pet/src/memory.js` | Add `#pane-memory` tab, search filter, category chips, and delete/add cards. |
| **3** | **Task & Timer Engine**| `skills/task_manager.py`<br>`skills/notify.py` | Async timer loop, persistence in `data/tasks.json`, Windows toast fallback. |
| **4** | **Tasks UI Surface** | `ui_pet/src/index.html`<br>`ui_pet/src/activity.js` | Add active timer pills with live countdowns and cancel buttons inside Activity pane. |
| **5** | **Input Control** | `skills/input_control.py` | Implement `type_text`, `press_hotkey`, `click` with screen boundary checks and failsafe. |
| **6** | **Onboarding Modal** | `ui_pet/src/onboarding.js`<br>`ui_pet/src/app.css` | First-launch wizard greeting user and verifying mic + model connection. |

---

## 7. Verification & Acceptance Criteria

1. **Memory Persistence:** Telling Jarvis *"Remember that my primary coding language is Python"* creates a new fact visible in the Memory Studio UI; restarting the backend preserves the memory.
2. **Memory Studio Interaction:** Clicking "Forget" on a card removes the fact from `data/memory.json` with an immediate UI update.
3. **Timers & Reminders:** Saying *"Remind me in 10 seconds to stretch"* schedules a timer, shows a live countdown in the Activity pane, and triggers the pet bubble and audio chime when expired.
4. **Input Control Safety:** Requesting a keyboard automation prompts the in-stream approval card before firing.
5. **Quality Gates:** All 15 existing test gates remain 100% green without regressions.

---

## 8. As-Built Implementation Notes (shipped 2026-10-06)

Implementation landed against the checklist in section 6 with these deliberate deviations:

1. **Navigation order** — the Memory tab sits between Activity and Settings: nav is `chat / activity / memory / settings` (`main.js` `PANES`, `index.html` nav button, `revamp2_interact.py` assertion updated accordingly).
2. **Timers surface** — instead of dual-view sub-tabs, active timers render as a dedicated `#task-timers` section inside the Activity pane (countdown chips with title, live `<span>` countdown, Cancel button). One glance, zero extra navigation.
3. **Input automation without extra deps** — `skills/input_control.py` is implemented with pure `ctypes`/`SendInput` (Unicode typing, key events, absolute mouse moves with screen clamp, 20 actions/sec rate limit, cursor `(0,0)` failsafe, `FailsafeError` raised on violation). `pyautogui`/`pynput` stay in `requirements.txt` for PyInstaller collection only; the runtime path has no third-party input dependency.
4. **WS wire format** — new commands are dot-namespaced to match the existing envelope: `memory.list / memory.add / memory.delete / memory.clear`, `tasks.list / tasks.create / tasks.cancel`, `onboarding_state / onboarding_done`. `task_manager.notify()` publishes `ui.chat` + `voice.say` + `task.fired`; `voice.say` was added to the `wire_bus` forward list so all clients see spoken lines.
5. **Onboarding gating** — shown when config `runtime.first_run` is not `false` **and** the `data/onboarded.json` marker is absent. Finish writes the marker always, and writes `first_run: false` back to config only when running frozen (dev and bundled configs are identical, so the marker file is the dev/prod split). Step 3 only persists `runtime.pet_render_mode` when the chosen style differs from the current one, so a same-style completion leaves `config.yaml` untouched.
6. **Memory routing case fidelity** — `core/fast_router.py` matches on lowercased text; `_restore_case()` re-applies the original casing to stored facts and reminder titles so "Python" does not become "python" in `data/memory.json`.
7. **Data location** — `DATA_DIR = CONFIG_DIR.parent / "data"` in `core/config.py` (dev: `jarvis-desktop-pet/data/`, prod: `%APPDATA%\JarvisDesktopPet\data/`); `jarvis-desktop-pet/data/` is gitignored.

### Acceptance run (2026-10-06)

* Spec-32 functional verification: **32/32 PASS** — onboarding wizard (3 steps, mic meter, LM Studio "Connected", marker written, stays dismissed across reload), *"Remember that my preferred language is Python"* → fast-path `memory_remember` (0 ms, LLM bypassed) → Memory Studio card with `Preferences` badge → persisted in `data/memory.json`; search/category filters, Add Fact, Forget + undo toast, WS delete sync; *"Remind me in 10 seconds to stretch"* → active task + Activity countdown chip → `task.fired` → toast + chime + chat entry `Reminder: stretch` + `voice.say` broadcast + chip cleanup; `type "hello world"` → approval card (risk 7/10, "Type text") → deny → `Action denied. No changes made.` Screenshots in `jarvis-desktop-pet/artifacts/ui_inspection/spec32/`.
* Quality gates: **15/15 PASS** (fast_router 71/71, vocab, injector, dictation flow+ui, audio_cache, earcons, approval 9/9, revamp2 static, revamp2 interact 56/56, hotkey e2e, hook e2e 37/37, phase5 e2e 14/14 + dock 27/27 + visual 28/28) plus `tests/smoke_test.py` Smoke OK.
