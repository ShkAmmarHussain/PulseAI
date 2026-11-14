# 37. Mini World: Sprint Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Mini World from doc 36 in eight shippable sprints, starting with a headless agent runtime and ending with the World tab released by default.

**Architecture:** A new `core/world/` package owns all world truth (agents, jobs, tasks) and talks to the rest of the backend only through `core.bus`. The Director is a deterministic state machine. Every model call goes through one queued gateway. The UI only draws `world.snapshot` plus `world.*` diffs.

**Tech Stack:** Python 3.10+ asyncio, existing `core.bus` / `core.llm` / `core.guardrails`. Tauri UI with plain JS modules and the vendored three.js. Tests are standalone scripts in `tests/` run with `.venv/Scripts/python tests/<name>.py` (exit 0 = pass), matching the existing `check()` style in `tests/fast_router_test.py`.

**Spec:** `docs/36-MINI-WORLD-MULTI-AGENT-VISION.md`. Visual reference: `docs/prototypes/36-world-hq.html`.

## Global Constraints

- The Director never calls an LLM and never runs a skill (doc 36 §7).
- Every model call goes through `core/world/brain.py`. Local LM Studio concurrency is 1 by default (doc 36 §12).
- Caps, defaults from doc 36 §12: 6 active agents besides the Director and defaults, 8 tasks per job, 3 temp agents per job, depth 1 (only the Director spawns), 300 s per task.
- Loop guard: the same skill call with the same arguments 3 times stops the task (doc 36 §12).
- Every `world.*` event carries `job_id` (and `task_id` / `agent_id` where relevant) and an increasing `seq`. `correlation_id` = `job_id` (doc 36 §13).
- Approvals keep using `ui.approval` / `ui.approval.response` unchanged (doc 36 §13, §16).
- The whole feature sits behind `world.enabled` in `config/config.yaml`, default `false` until Sprint 8 (doc 36 §7.3).
- The building is **3 floors x 3 x 3 rooms = 27 rooms** (owner, 2026-11-14). Defaults keep the rooms in doc 36 §11.2. Every other room is spare.
- Commits author Ammar Hussain <ammarhussain2199@gmail.com> only, no co-author trailers.

## Review Focus

1. **Stop all during a running job:** every task is cancelled, the brain queue is emptied, temp agents are removed, and no task result arrives afterwards. Pinned in Task 1.4 and Task 1.5.
2. **A plan that names a role nobody has, or has a cycle:** the job fails visibly with a reason. Nothing hangs. Pinned in Task 1.2 and Task 1.5.
3. **A worker that raises or times out:** that task fails, its dependents are skipped, and the job still closes. Pinned in Task 1.4 and Task 1.5.
4. **Two jobs at once:** the queue serves interactive before background, and the results never mix between jobs. Pinned in Task 1.3 and Task 1.5.
5. **A UI that reconnects mid-job:** `snapshot()` plus later diffs rebuild the same state. A `seq` gap is detectable. Pinned in Task 1.1.

---

## Sprint overview

| Sprint | Doc 36 milestone | Ships | Exit criteria |
|---|---|---|---|
| **1** | M0 | `core/world/` runtime, headless, with fake agents | All Sprint 1 tests pass. Stop all works. Snapshot plus diffs reproduce the state. Nothing is wired into the app yet. |
| 2 | M1 (part 1) | Thinker (regex fast path plus LLM plan), WorkerAgent tool-use loop over existing skills, Reporter | Real plans from LM Studio validate. A worker runs a real skill through Safety. |
| 3 | M1 (part 2) | Wiring behind `world.enabled`: input goes to the Director, approvals move over, `ws_bridge` forwards `world.*` | Every doc 35 voice and chat flow passes with the flag on. Fast-path latency is no worse than today. |
| 4 | M2 | World tab in `ui_pet` from the prototype: 3x3x3 building, chibi kit, roster, inspector, job strip, chat bar, driven by real events | Live jobs show correctly. Rendering pauses when hidden. The 2D fallback works. |
| 5 | M3 | Create and delete agents: Builder temp agents, + Agent form, edit, delete, archive, caps in the UI | The Director spawns and dismisses an agent in a real job. A user-made agent gets work. |
| 6 | M4 | Skills: draft, AST check, sandbox, review drawer, enable, versions | A generated skill is reviewed, enabled and used. An unsafe draft is rejected. |
| 7 | M5 | Growth and polish: look generator persisted, floors grow, theme picker, onboarding step, sounds | Ten generated agents all look different. The building grows and shrinks. |
| 8 | M6 | QA and release: doc 35 style pass on the installed build, flag on by default, old pipeline removed | Results table green. README and docs updated. |

Each later sprint gets its own task-level section here when it starts, written against the code as it stands then. Only Sprint 1 is broken into tasks now.

---

## Sprint 1: World runtime (headless)

**Files:**
- Create: `jarvis-desktop-pet/core/world/__init__.py` (exports only)
- Create: `jarvis-desktop-pet/core/world/state.py`
- Create: `jarvis-desktop-pet/core/world/plan.py`
- Create: `jarvis-desktop-pet/core/world/brain.py`
- Create: `jarvis-desktop-pet/core/world/runtime.py`
- Create: `jarvis-desktop-pet/core/world/director.py`
- Modify: `jarvis-desktop-pet/config/config.yaml` (add the `world:` block)
- Tests: `jarvis-desktop-pet/tests/world_state_test.py`, `world_plan_test.py`, `world_brain_test.py`, `world_runtime_test.py`, `world_director_test.py`

### Task 1.1: WorldState with snapshot and diffs

**Interfaces:**
- Produces:
  - `AgentInfo` dataclass: `id: str, name: str, role: str, kind: str ("default"|"custom"|"temp"), room: str, state: str = "idle", task_id: str | None = None, label: str = ""`
  - `TaskInfo` dataclass: `id, job_id, role, goal, needs: list[str], agent_id: str | None = None, state: str = "queued", result: str = "", error: str = ""`. States: `queued|working|done|failed|skipped|stopped`.
  - `JobInfo` dataclass: `id, text, status: str = "open", answer: str = "", task_ids: list[str]`
  - `class WorldState(on_change: Callable[[dict], None] | None = None)` with `add_agent(AgentInfo)`, `update_agent(agent_id, **fields)`, `remove_agent(agent_id)`, `open_job(job_id, text)`, `add_task(TaskInfo)`, `update_task(task_id, **fields)`, `close_job(job_id, status, answer="")`, `snapshot() -> dict`, `seq: int`.
  - Each mutation calls `on_change({"topic": <world.* topic>, "seq": n, ...payload})` with topics `world.agent.added|updated|removed`, `world.job.opened|closed`, `world.task.created|updated`.

- [ ] **Step 1: Write the failing test** `tests/world_state_test.py`:
  - `seq` starts at 0 and goes up by exactly 1 per mutation.
  - `update_agent` on an unknown id raises `KeyError`.
  - Replay: apply every diff from a fresh `apply_diff(snapshot: dict, diff: dict) -> dict` helper (defined in `state.py`) to an empty snapshot, and the result equals `state.snapshot()` after a 10-mutation script (2 agents, 1 job, 3 tasks, 1 removal).
  - `snapshot()["seq"] == state.seq`.
- [ ] **Step 2: Run** `.venv/Scripts/python tests/world_state_test.py`. Expected: exit 1, `ModuleNotFoundError: core.world`.
- [ ] **Step 3: Implement** `state.py` (dataclasses plus `asdict`. `apply_diff` is a pure function keyed by topic).
- [ ] **Step 4: Run the test.** Expected: all PASS, exit 0.
- [ ] **Step 5: Commit** `feat(world): world state with snapshot and diffs`.

### Task 1.2: Plan validation

**Interfaces:**
- Consumes: none.
- Produces: `validate_plan(plan: dict, known_roles: set[str], caps: dict) -> tuple[list[dict], list[str]]` returns `(tasks_in_run_order, errors)`. `caps` keys: `max_tasks` (8) and `max_new_agents` (3). A plan is `{"intent": str, "tasks": [{"id","role","goal","needs"}], "new_agents": [{"role","why"}]}`.

- [ ] **Step 1: Write the failing test** `tests/world_plan_test.py` with cases:
  - The doc 36 §7.1 example plan with `known_roles={"researcher","operator"}` returns `t1,t2` before `t3` before `t4`, with no errors.
  - An unknown role not listed in `new_agents` gives the error `unknown role: <role>`.
  - A cycle `t1 needs t2, t2 needs t1` gives the error `cycle in tasks`.
  - `needs` naming a missing task id gives `unknown dependency: <id>`.
  - 9 tasks gives `too many tasks (9 > 8)`. 4 new agents gives `too many new agents (4 > 3)`.
  - An empty `tasks` list gives `plan has no tasks`.
  - Duplicate task ids give `duplicate task id: <id>`.
- [ ] **Step 2: Run it.** Expected: FAIL on import.
- [ ] **Step 3: Implement** `plan.py` (Kahn's topological sort, stable by input order).
- [ ] **Step 4: Run it.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(world): plan validation`.

### Task 1.3: Brain gateway (queued model calls)

**Interfaces:**
- Produces: `class Brain(concurrency: int = 1)` with:
  - `async submit(fn: Callable[[], Awaitable[T]], *, job_id: str, priority: int = 1) -> T` (0 = interactive, 1 = background. Lower runs first. FIFO within a priority).
  - `cancel_job(job_id) -> int`: removes the job's queued calls (their `submit` raises `asyncio.CancelledError`) and cancels its running calls. Returns how many were cancelled.
  - `cancel_all() -> int`.
  - `waiting(job_id=None) -> int`: queued calls, not running.
  - `on_wait: Callable[[str, bool], None] | None`: called with `(job_id, True)` when a call is queued behind others and `(job_id, False)` when it starts. Agents use this to show `waiting_brain`.

- [ ] **Step 1: Write the failing test** `tests/world_brain_test.py`:
  - With concurrency 1, 3 background calls plus 1 interactive call submitted while the first runs: the run order is `bg1, inter, bg2, bg3`.
  - With concurrency 2, two 0.2 s calls finish in under 0.35 s.
  - `cancel_job("j1")` while `j1` has 1 running and 2 queued: all 3 `submit`s raise `CancelledError`, and `j2`'s queued call still completes.
  - An exception inside `fn` propagates from `submit` and does not stall the queue (the next call runs).
- [ ] **Step 2: Run it.** Expected: FAIL on import.
- [ ] **Step 3: Implement** `brain.py` (`asyncio.PriorityQueue` of `(priority, counter, item)` with N worker tasks started lazily on first submit).
- [ ] **Step 4: Run it.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(world): brain gateway with priorities and cancel`.

### Task 1.4: Agent runtime

**Interfaces:**
- Consumes: `WorldState`, `AgentInfo`, `TaskInfo` (Task 1.1).
- Produces: `class AgentRuntime(state: WorldState, caps: dict)` with:
  - `register_default(info: AgentInfo)`: defaults never count against caps.
  - `spawn_temp(role: str, job_id: str) -> str`: returns the new agent id. Raises `CapError` (defined here) past `max_active_temp` (6) total, or past `max_temp_per_job` (3) for that job. The room is the first free spare room id from `SPARE_ROOMS` (a constant list of the 19 spare room ids of the 3x3x3 building, `f{floor}r{row}c{col}` minus the 8 default rooms).
  - `async run(agent_id, task_id, worker: Callable[[TaskInfo], Awaitable[str]], timeout_s: float) -> str`: sets agent `working`, task `working`, awaits the worker, then sets task `done` with the result, or `failed` with `error` on an exception or timeout (`timeout after <n>s`). The agent goes back to `idle` either way.
  - `dismiss(agent_id)`: removes temp agents only (a `ValueError` for defaults).
  - `stop(task_id=None, all=False) -> int`: cancels running workers. Their tasks become `stopped`.
  - `LoopGuard` class: `check(agent_id, skill, args: dict) -> None`, raises `LoopError` on the 3rd identical consecutive call.

- [ ] **Step 1: Write the failing test** `tests/world_runtime_test.py`:
  - Spawning 3 temp agents for job `j1` works, and the 4th raises `CapError`. Seven temp agents across 3 jobs raise on the 7th.
  - `run` with a worker returning `"ok"` gives task `done`, result `"ok"`, and the agent `idle`.
  - A worker raising `RuntimeError("boom")` gives task `failed` with error `boom`.
  - A worker sleeping 2 s with `timeout_s=0.1` gives task `failed` with error `timeout after 0.1s`.
  - `stop(all=True)` during 2 running workers gives both tasks `stopped`, and neither later sets `done`.
  - `dismiss` on a default agent raises `ValueError`.
  - `LoopGuard`: 3 identical calls raise on the 3rd. A different call in between resets the count.
  - Spare room ids are unique, 19 in total, and never one of the 8 default rooms.
- [ ] **Step 2: Run it.** Expected: FAIL on import.
- [ ] **Step 3: Implement** `runtime.py`.
- [ ] **Step 4: Run it.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(world): agent runtime with caps, timeouts, stop and loop guard`.

### Task 1.5: Director (deterministic job state machine)

**Interfaces:**
- Consumes: Tasks 1.1–1.4. `core.bus.MessageBus`, `create_event`.
- Produces: `class Director(bus, state, runtime, brain, *, thinker, workers, reporter, caps)` where
  - `thinker: Callable[[str], Awaitable[dict]]` returns a plan dict (Task 1.2 shape),
  - `workers: dict[str, Callable[[TaskInfo, dict[str, str]], Awaitable[str]]]` is keyed by role and receives `(task, results_of_needed_tasks)`,
  - `reporter: Callable[[str, dict[str, str]], Awaitable[str]]` takes `(request_text, all_results)` and returns the answer.
  - Methods: `async handle(text: str, job_id: str | None = None, priority: int = 0) -> JobInfo`, `async stop_all() -> None`.
  - Every model-backed call (thinker, workers, reporter) goes through `brain.submit(..., job_id=job_id, priority=priority)`. The Director itself awaits nothing else.
  - Bus events: every `WorldState` diff is published on its `world.*` topic with `correlation_id=job_id`. A closed job also publishes `ui.chat` `{role:"assistant", text: answer}`.
  - Flow: open job, then the thinker. On an invalid plan (after **one** retry with the errors appended to the text), close the job `failed` with answer `I could not plan that: <first error>`. Otherwise spawn the temps from `new_agents`, then run tasks as their `needs` complete (independent tasks start together, and the brain serialises the model calls). A failed task marks its dependents `skipped`. Then the reporter, then dismiss the temps, then close the job `done` (or `partial` if any task failed).

- [ ] **Step 1: Write the failing test** `tests/world_director_test.py` with fake thinker, workers and reporter (each records calls and sleeps 0.05 s):
  - Happy path: the doc 36 §7.1 plan gives the job `done`, workers called in valid order, `t3` received the results of `t1` and `t2`, one temp `writer` spawned and dismissed (no temp agents left), the answer published on `ui.chat`, and the `world.*` events on the bus have strictly increasing `seq`.
  - Invalid plan twice gives the job `failed`, the answer starts with `I could not plan that:`, and the thinker was called exactly 2 times.
  - A worker for `t1` raising gives `t1 failed`, `t3` and `t4 skipped`, `t2 done`, and the job `partial`.
  - `stop_all()` 0.06 s into a job: the job ends `stopped`, no worker is called after the stop, no temp agents remain, and `brain.waiting() == 0`.
  - Two jobs (interactive and background) submitted together: both finish, and each job's answer contains only its own results.
  - The Director module imports nothing from `core.llm` (assert via `ast` over `director.py`).
- [ ] **Step 2: Run it.** Expected: FAIL on import.
- [ ] **Step 3: Implement** `director.py`.
- [ ] **Step 4: Run it.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(world): deterministic Director over runtime and brain`.

### Task 1.6: Config flag and package exports

**Interfaces:**
- Produces: `config/config.yaml` gains:
  ```yaml
  world:
    enabled: false
    brain_concurrency: 1
    caps: {max_active_temp: 6, max_temp_per_job: 3, max_tasks: 8, task_timeout_s: 300}
  ```
  and `core/world/__init__.py` exports `WorldState, Brain, AgentRuntime, Director, validate_plan`.
- [ ] **Step 1:** Add a check to `tests/world_director_test.py`: `load_config()["config"]["world"]["enabled"] is False` and the caps match the values above.
- [ ] **Step 2:** Run it. Expected: FAIL (KeyError).
- [ ] **Step 3:** Add the block and the exports.
- [ ] **Step 4:** Run all five world tests. Expected: all exit 0. Run `tests/smoke_test.py` if it needs no backend, to confirm nothing else broke.
- [ ] **Step 5: Commit** `feat(world): config flag and exports`.

---

## Sprint 2: Thinker, workers and Reporter

**Goal:** real model-backed thinking and work behind the Sprint 1 Director, still unwired (Sprint 3 wires it).

**Files:**
- Modify: `agents/planner.py` (extract `plan_steps(q: str) -> list[dict] | None`; the agent calls it, behaviour unchanged)
- Modify: `agents/tool_control.py` (extract `async execute_step(cfg, rtm, step: dict) -> str`; the agent calls it)
- Modify: `core/world/state.py` (`TaskInfo.params: dict`) and `core/world/director.py` (copies a plan task's `steps` into `params`)
- Create: `core/world/roles.py`, `core/world/thinker.py`, `core/world/worker.py`, `core/world/reporter.py`, `core/world/team.py`
- Tests: `tests/world_thinker_test.py`, `tests/world_worker_test.py`, `tests/world_team_test.py`, `tests/world_live_test.py` (skips when LM Studio is not reachable)

### Task 2.1: Shared planner rules and skill execution
- `plan_steps("open notepad") == [{"action": "launch_app", "target": "notepad", "risk": 2}]`; `plan_steps("what is the capital of France") is None`.
- `execute_step(cfg, None, {"action": "respond", "text": "hi"}) == "hi"`.
- Existing offline tests (`model_router_test`, `vocab_test`, `injector_test`, `smoke_test`) still pass.

### Task 2.2: Thinker
**Interfaces:** `make_thinker(cfg, *, chat, roles: dict[str, list[str]]) -> Callable[[str], Awaitable[dict]]`, where `chat(messages, tier) -> str` is injected.
- Rule match: one task, the role from `ROLE_FOR_ACTION`, `steps` carried, **zero** `chat` calls.
- No rule and `model_router.is_complex(q)` is false: one `archivist` task with goal = q, zero `chat` calls.
- Complex: one `chat(..., "heavy")` call. The JSON plan is parsed even inside a ```json fence or surrounding prose. Unparseable output returns `{}`, which the Director rejects and retries once.
- A retry text (containing "Your last plan was invalid") always goes to the model.

### Task 2.3: Workers
**Interfaces:** `make_worker(role, cfg, *, chat, execute, approve, allowed: list[str], max_steps=6) -> Worker`, where `approve(step: dict, risk: int) -> Awaitable[bool]`.
- A task with `params.steps`: each step is risk-scored with `core.guardrails.risk_score`. Risk >= 6 needs `approve` unless the policy is `autonomous`. A denied step raises `PermissionError("denied: <action>")`. Steps run through `execute`.
- An action not in `allowed` raises `PermissionError("not allowed for <role>: <action>")`.
- Model loop: the model answers JSON `{"action": ..., ...}` or `{"final": "..."}`. Up to `max_steps` actions, then `RuntimeError("no final answer after 6 steps")`. The `LoopGuard` stops repeats. Results from needed tasks are included in the prompt.
- `archivist` answers with recall + web context like `MemoryAgent`.

### Task 2.4: Reporter and team
**Interfaces:** `make_reporter(cfg, *, chat)`. One result is returned as is, with no model call. Several results get one `chat(..., "fast")` call. `build_world(cfg, bus, *, chat=None, execute=None, approve=None) -> World(state, runtime, brain, director)` registers the 8 default agents (doc 36 §8 names and rooms) and uses `world.brain_concurrency` and `world.caps`.
- End to end with fakes: "search the web for pulse oximeters" runs one researcher task, makes 0 model calls, and the answer is the search result.
- A complex request runs the LLM plan through the Director with a temp agent and closes `done`.
- Live (LM Studio up): "what is 2+2" answers, and a complex request yields a plan that validates.

---

## Sprint 3: Wire the world into the app (behind `world.enabled`)

**Goal:** with `world.enabled: true` (or env `PULSEAI_WORLD=1`), typed and spoken requests that the fast path does not take go to the Director. Approvals use the existing cards, and the UI receives `world.*` events. With the flag off, nothing changes.

**Files:**
- Create: `core/world/approvals.py` (`ApprovalBridge`) and `core/world/service.py` (`WorldService`)
- Modify: `backend/app.py` (route `on_input` to the world when enabled), `backend/ws_bridge.py` (forward `world.*`, accept `world_say` / `world_stop` / `world_snapshot`)
- Tests: `tests/world_service_test.py` (offline, real `MessageBus`) and `tests/world_backend_e2e.py` (starts the real backend with `PULSEAI_WORLD=1` on a spare port)

### Task 3.1: ApprovalBridge
`ApprovalBridge(bus, timeout_s)` with `async ask(step, risk, job_id) -> bool`. It publishes `ui.approval` `{action, risk, message}` on a fresh cid and resolves on the first `ui.approval.response` with that cid (`payload.allow`). On timeout it publishes `ui.approval_cancelled {reason: "timeout"}` and returns False. Duplicate answers are ignored. Answers for cids it did not raise are ignored, because the old Orchestrator owns those. `timeout_s` comes from `permissions.approvals.timeout_ms` (45000).

### Task 3.2: WorldService
`WorldService(bus, cfg, rtm=None, chat=None, execute=None)`:
- `start()` subscribes `world.cmd.say` (`{text}`), `world.cmd.stop` and `world.cmd.snapshot`.
- `handle_input(text, cid)` echoes `ui.chat {role:"user"}`, runs `director.handle(text, job_id=cid)` as a task, and on close publishes `voice.say {text: answer}` and `memory.store`.
- `world.cmd.snapshot` publishes `world.snapshot` with `state.snapshot()`.
- `stop_all()` is used by `world.cmd.stop` and returns how many jobs were stopped.

### Task 3.3: Backend wiring
`App.start`: when the world is enabled, build a `WorldService` before the bus starts. `on_input`: the fast path first, as today, then `world.handle_input` instead of `orchestrator.input`. `ws_bridge`: forward the topics `world.agent.*`, `world.job.*`, `world.task.*` and `world.snapshot`, and map the client types `world_say`, `world_stop` and `world_snapshot` to `world.cmd.*`. The port comes from env `PULSEAI_WS_PORT` (default 8765) so the e2e test can run next to a live app.

### Task 3.4: End-to-end
`tests/world_backend_e2e.py` starts `backend/main.py` with `PULSEAI_WORLD=1` and `PULSEAI_WS_PORT=8799`, then checks:
- `text_input` "list files in ." gives `world.job.opened`, `world.task.*`, a `ui.chat` answer and `world.job.closed` done.
- `world_snapshot` returns the 8 agents.
- `world_stop` returns, and no job is left open.
- With the flag off, the same input produces no `world.*` events.

---

## Sprint 4: World tab in the app

**Goal:** a real **World** tab in the main window that draws the live world from the backend: the 3x3x3 building, chibi agents, roster, inspector, job strip, approvals, chat, Stop all and floor focus. Built from `docs/prototypes/36-world-hq.html` and the doc 34 tokens.

**Files:**
- Create: `ui_pet/src/vendor/addons/**` (three r170 add-ons copied unmodified: OrbitControls, CSS2DRenderer, RoundedBoxGeometry, EffectComposer and its passes and shaders), resolved through an import map in `index.html` (`three` maps to `./vendor/three.module.js`, `three/addons/` maps to `./vendor/addons/`).
- Create: `ui_pet/src/world/store.js` (pure state mirror), `ui_pet/src/world/building.js` (rooms, lift, lights), `ui_pet/src/world/chibi.js` (character kit and look generator), `ui_pet/src/world/scene.js` (renderer, camera, actors, walking), `ui_pet/src/world/tab.js` (UI glue)
- Modify: `ui_pet/src/index.html` (World nav item first, `#pane-world`), `ui_pet/src/main.js` (pane list), `ui_pet/src/app.css` (World tab styles on the doc 34 tokens)
- Modify: `backend/ws_bridge.py` (`set_world {enabled}` writes `world.enabled` and publishes `world.toggle`), `backend/app.py` (starts or stops `WorldService` live on `world.toggle`)
- Tests: `tests/world_store_test.mjs` (node), and an addition to `tests/world_backend_e2e.py` (toggle on and off live)

### Task 4.1: Add-ons via import map
Copy the files and add the import map before every module script. Check: `pet3d.js` still loads (it imports `./vendor/three.module.js` directly), and the World tab imports `three/addons/controls/OrbitControls.js` without a 404.

### Task 4.2: Store
`createStore()` returns `{apply(msg) -> "ok"|"gap"|"ignored", state, on(fn)}`. `world.snapshot` replaces the state. A diff with `seq == state.seq + 1` applies, using the same rules as Python `apply_diff`. A diff with `seq <= state.seq` is ignored. A larger jump returns `"gap"`, and the tab then asks for `world_snapshot`. Node test: replaying the Python test's 10-diff script gives the same final state; a gap is detected; duplicates are ignored.

### Task 4.3: Scene
Room ids `f{floor}r{row}c{col}`. The front row (r1) holds the default rooms with the doc 36 §11.2 names, and the rows behind it are spare. Low glass partitions between rows keep every room visible. The lift is on the right, and the lobby door is on f1 at the left. Agents walk from the door along the front corridor, take the lift, and walk up the room's centre lane to their slot. Scene objects are created and removed only from store events. Rendering pauses when the tab is hidden or the window is minimised. If WebGL fails, a flat floor plan replaces the scene.

### Task 4.4: Tab UI
- Roster: Team and Temporary groups, a portrait for each agent, and its state.
- Inspector: the selected agent's state, task, recent log, skills and actions.
- Job strip: the newest open job's tasks.
- Composer: sends `world_say`.
- Stop all: sends `world_stop`.
- Floor buttons All/3/2/1.
- An approval card for any `ui.approval` whose cid starts with `world-`; Allow and Deny send `approval_response`.

### Task 4.5: Live on/off
When the world is off, the World tab shows an empty state with **Turn on Mini World**, which sends `set_world {enabled: true}`. The backend writes `world.enabled`, starts the `WorldService` without a restart, and broadcasts `world.status {enabled}`. Turning it off stops all jobs first.

### Task 4.6: Checks
- The node store test passes.
- The backend e2e test adds: live toggle on, then a job runs; toggle off, then no world events.
- A browser pass on the real backend: the desktop size and a 900 px wide window show the building, the eight regulars and a live job. The detector (`impeccable detect`) is clean or explained.

---

## Sprint 5: Create and delete agents (done)

- `core/world/agents_store.py`: custom agents are kept in `data/world_agents.json`. Deleted ones are archived for 30 days and can be restored.
- `AgentRuntime.spawn_custom / keep / remove` and the cap `max_custom` (6). `AgentInfo` gains `description` and `look_seed`.
- `WorldService` handles `world.cmd.agent {op: create | keep | update | delete | restore | archived}`. Bodie is shown working while he builds. Customs come back after a restart.
- The Thinker plans with custom roles (listed with their descriptions). A custom agent's worker prompt carries its description.
- World tab:
  - New agent form with presets and an optional name.
  - Inspector actions: Reroll look, Edit, Keep as custom, Dismiss or Delete with an inline confirm.
  - Recently deleted list with Bring back.
  - New agents walk in, and a reroll rebuilds the chibi.
- Tests: `tests/world_agents_test.py` (26 checks), plus every earlier suite.
