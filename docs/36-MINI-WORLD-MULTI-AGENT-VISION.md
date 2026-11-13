# 36. VISION: THE MINI WORLD (3D multi-agent workspace)

Status: **vision / design, waiting on approval. No code yet.** Next step after approval: an implementation plan per milestone (§17).

Decided with the owner (2026-11-14):
- The world exists so you can **see what Jarvis is doing**, have **more control**, **extend it** with new agents and skills, and have it **look new and interesting**.
- **Approach A:** the world is a new **World** tab and the **home screen** of the main window. Memory, Activity and Settings stay as tabs. Pip and the top-edge island are unchanged.
- The **main agent never does work itself**, thinking included. It only routes, creates and deletes agents, and hands out tasks.
- The main agent has **default agents** under it, and can **create or delete agents and skills** when needed.
- Agents **appear in the 3D world while working** and are **removed by the main agent** when their task is done.

Everything else in this doc is a proposal. Each call made without the owner is marked *(call)*. The full list is in §19.

---

## 1. The idea in one paragraph

You pick an environment: a house, an office, and later more. PulseAI builds a small 3D version of it. In the middle stands the **Director**, the main agent (Pip). You talk to the Director by voice or chat. The Director does not think or act. It sends every request to a **Thinker** agent, gets back a plan, and gives each piece to an agent at a desk. You watch them work: someone at the computer browsing, someone at the bookshelf searching memory, someone at the window watching the screen. When the job needs a specialist that does not exist, the Director asks the **Builder** to create one. The new agent walks in, works, reports, and walks out when the Director dismisses it. You can click any agent to see what it is doing, stop it, edit it or delete it, and you can create your own agents and skills.

## 2. Goals, non-goals, anti-goals

**Goals**
1. **Visibility.** Every task, every agent and every step is visible in the world and inspectable with one click.
2. **Control.** Stop, pause, retry, delete and approve from the world. One "Stop all" button always works.
3. **Extensibility.** The user and the Director can add agents (config only) and skills (code, sandboxed, approved).
4. **Delight.** The world feels alive (idle animations, small reactions, day/night light) without slowing work down.
5. **No regressions.** Voice, the fast path ("open notepad"), approvals, Pip and the island keep working as today.

**Non-goals (v1)**
- No multiplayer or shared worlds.
- No free-roam game controls (WASD, physics, inventory). The camera orbits and focuses; agents walk on fixed paths.
- No user-built environments or level editor. Environments ship with the app (§11.4 keeps the door open).
- No agents creating agents. Only the Director spawns (depth 1).
- No marketplace for agents or skills.

**Anti-goals (a failure even if it technically works)**
- The world is a **slow toy**: simple requests take longer than today because of the extra hops.
- The world **lies**: an animation shows "working" when nothing is running, or hides a failed step.
- **Runaway agents**: the Director keeps spawning, or an agent loops and burns the GPU or a cloud budget.
- **Unsafe extensibility**: a generated skill runs code the user never approved.
- The 3D view makes the laptop hot or the app laggy when you are not even looking at it.

## 3. Constraints

- **Stack:** Tauri (Rust) UI with plain JS modules, Python asyncio backend, WebSocket `ws://127.0.0.1:8765/ws`, in-process `core.bus` (topics + events with `correlation_id`).
- **3D:** three.js is already vendored (`ui_pet/src/vendor/three.module.js`, used by `pet3d.js`). Pip's rig (springs, eyes, moods) already exists.
- **Models:** local LM Studio by default, so in practice **one model call runs at a time**. `core/model_router.py` already picks fast / heavy / vision tiers. Cloud (OpenAI, Anthropic) is optional, with the user's key.
- **Safety:** `core.guardrails.risk_score`, `SafetyAgent` and the approval flow (`ui.approval` and `ui.approval.response` with timeout and dedupe) must stay the only path to risky actions.
- **Platform:** Windows 11, iGPU laptops count. Everything stays under `%APPDATA%\JarvisDesktopPet\`.

## 4. Approaches considered

| | Where the world lives | Trade-off |
|---|---|---|
| **A (picked)** | New **World** tab, home of the main window. Chat bar over the scene, drawers for agents, skills and approvals. | Reuses the window, the tabs and three.js. Least new plumbing. The world shares the screen with forms. |
| B | Separate full-screen World window. | More immersive. Two big windows, and the chat and approval UI duplicated. |
| C | World replaces the main window, Settings included. | Most striking. Settings and forms become hard to use, and it is the most rework. |

The owner picked **A**. For the 3D engine, three.js (already shipped) beats Babylon.js (a second engine for the same job) and Unity or Godot (a heavy second runtime, IPC, bigger installer) *(call)*.

## 5. Vocabulary

| Term | Meaning |
|---|---|
| **World** | The 3D scene in the World tab. One environment loaded at a time. |
| **Environment** | A themed place (House, Office, ...) defined by a 3D model plus a manifest of stations and paths (§11). |
| **Director** | The main agent, shown as Pip. Routes only. Never calls an LLM and never runs a tool. |
| **Agent** | A worker with a role, a model tier, allowed skills and a look. It is **default** (ships with the app, never removed), **custom** (made by the user, persistent) or **temp** (made by the Director for one job, removed when done). |
| **Skill** | A callable capability (Python), for example `web_search`, `file_ops`. Agents use skills. Skills have permissions and a risk level. |
| **Job** | One user request, from what you said to the final answer. |
| **Task** | One piece of a job, given to one agent. A job is a small graph of tasks. |
| **Station** | A spot in the environment where an agent works (desk, bookshelf, window, workbench). |

## 6. Architecture

```
┌──────────────── Tauri UI (main window) ─────────────────────────────┐
│ World tab (home)                                                    │
│   world/scene.js      three.js renderer, environment loader, camera │
│   world/actors.js     agent avatars (Pip rig variants), animations  │
│   world/paths.js      waypoint graph, walking                       │
│   world/hud.js        chat bar, roster, inspector, create forms     │
│   world/store.js      world state mirror (from world.snapshot+diffs)│
│ Activity / Memory / Settings tabs (existing)                        │
│ Pip pet + island (existing, unchanged)                              │
└──────────────────────────── ws ─────────────────────────────────────┘
┌──────────────── Python backend ─────────────────────────────────────┐
│ ws_bridge  (forwards world.* to UI, world.cmd.* to bus)             │
│                                                                     │
│ core/world/                                                         │
│   director.py     Director: deterministic job/task state machine    │
│   runtime.py      AgentRuntime: spawn, run, stop, remove agents     │
│   agent.py        WorkerAgent: LLM loop with allowed skills         │
│   brain.py        LLM gateway: queue, priorities, budgets, cancel   │
│   registry.py     agent + skill registry (default/custom/temp)      │
│   state.py        WorldState: agents, jobs, tasks; snapshot + diffs │
│   store.py        persistence (yaml + sqlite)                       │
│   sandbox.py      runs custom skills in a subprocess                │
│                                                                     │
│ existing: bus, guardrails, SafetyAgent, approvals, model_router,    │
│           skills/*, memory, voice_service                           │
└─────────────────────────────────────────────────────────────────────┘
```

Rule: **the backend owns the truth.** The UI only draws `WorldState` and sends commands. If the UI closes, jobs keep running. When it reopens it gets a `world.snapshot` and catches up. That is how the world never lies (anti-goal 2).

## 7. The Director

The Director is a **deterministic state machine with no LLM** *(call: this is the strict reading of "even thinking is delegated")*. It does exactly five things:

1. **Receive** a request (voice, chat bar, island) and open a **job**.
2. **Delegate the thinking:** send the request to the **Thinker** and wait for a **plan**.
3. **Staff the plan:** give each task to an existing agent. If the plan says a role is missing, ask the **Builder** for a temp agent (or a skill, §10).
4. **Track** tasks: start them when their inputs are ready, retry or fail them, raise approvals, enforce caps and timeouts.
5. **Close** the job: send the results to the **Reporter** for the final answer, then dismiss temp agents.

### 7.1 The plan the Thinker returns (JSON, validated)

```json
{
  "job_id": "j_81f2",
  "intent": "compare two laptops and save the result",
  "tasks": [
    {"id": "t1", "role": "researcher", "goal": "find specs for X1 Carbon gen 13", "needs": []},
    {"id": "t2", "role": "researcher", "goal": "find specs for XPS 14", "needs": []},
    {"id": "t3", "role": "writer", "goal": "write a comparison table", "needs": ["t1", "t2"]},
    {"id": "t4", "role": "operator", "goal": "save it to Documents/laptops.md", "needs": ["t3"]}
  ],
  "new_agents": [{"role": "writer", "why": "no default agent writes long documents"}],
  "new_skills": [],
  "answer_style": "short"
}
```

The Director checks it against a schema. Roles must exist or be listed in `new_agents`. The graph must have no cycles and stay within the caps (§12). If the plan is invalid, the Thinker gets one retry with the error, then the job fails visibly.

### 7.2 The fast path stays

Today `OrchestratorAgent` and `PlannerAgent` route short commands ("open notepad", "search X", "describe my screen") with regex, with no LLM. Sending every one of those through a Thinker LLM call would make simple things slower (anti-goal 1). So the **regex router moves into the Thinker as its first step**: if a rule matches, the Thinker returns a one-task plan instantly with no model call. The Director still never thinks, and the user still sees the Thinker "decide" for a split second *(call)*.

### 7.3 Where today's code goes

| Today | Becomes |
|---|---|
| `agents/orchestrator.py` (keyword routing + approval handling) | `core/world/director.py`. Approval timers and dedupe move over as they are. The keyword routing moves to the Thinker. |
| `agents/planner.py` (regex plans) | Thinker fast path, plus an LLM plan when no rule matches |
| `agents/tool_control.py` | Operator agent's skill executor |
| `agents/memory_agent.py` | Archivist agent |
| `agents/vision.py`, `perception.py` | Watcher agent |
| `agents/safety.py` | stays a **service**, not a world agent. Every skill call passes through it. |
| `agents/spawner.py` (stub) | `core/world/runtime.py` + Builder agent |
| `agents/voice_tts.py`, `pet_ux.py` | stay services. The voice is the Director's voice. |
| `skills/templates/agent_spec.py`, `skill_spec.py` | extended (§9) |

Migration happens behind a flag (`world.enabled`) so the old pipeline can be switched back on during the rollout.

## 8. Default agents

They are always present, sitting at their stations when idle. None can be deleted. Each can be disabled and edited (name, look, model tier, prompt additions).

| Agent | Station (office / house) | Does | Skills | Tier |
|---|---|---|---|---|
| **Director** (Pip) | centre desk / living-room sofa | routes, staffs, tracks. No LLM. | none | none |
| **Thinker** | whiteboard / kitchen table | turns a request into a plan. Fast path first. | none (plan only) | heavy |
| **Researcher** | computer desk / study desk | web search, read pages | `web_search`, `browser` (read) | fast |
| **Operator** | workstation / home PC | files, apps, shell, keyboard and mouse | `file_ops`, `app_control`, `shell`, `input_control` | fast |
| **Watcher** | window / TV | screen and image understanding | `screen_vision` | vision |
| **Archivist** | filing cabinet / bookshelf | recall and store memories | `memory_skills` | fast |
| **Reporter** | mail desk / armchair | writes the final answer for chat and voice | none | fast |
| **Builder** | workshop bench / garage | creates temp and custom agents and drafts new skills | `create_agent`, `draft_skill` | heavy |

"Writer", "Coder", "Translator" and others are **not** defaults. They are what the Builder creates on demand, so the "new agent walks in" moment happens often enough to be part of the experience *(call)*.

## 9. Agents: data and lifecycle

### 9.1 AgentSpec (extends `skills/templates/agent_spec.py`)

```yaml
id: a_writer_3            # stable id; default agents use their role name
name: Wren                # shown on the name tag
role: writer
kind: temp                # default | custom | temp
created_by: director      # director | user | system
model_tier: heavy         # fast | heavy | vision (model_router)
skills: [file_ops.read]   # allow-list; a skill outside it is refused
system_prompt: "You write clear, structured documents..."
look: {body: pip, color: "#7dd3fc", accessory: glasses}
station: auto             # a station id, or auto (free spare desk)
limits: {max_steps: 12, timeout_s: 300, max_tokens: 20000}
version: 1
```

### 9.2 States

```
requested ─► validating ─► (approval if custom/risky) ─► arriving ─► idle
idle ─► assigned ─► working ─┬─► done ─► idle (default/custom)
                             │         └► leaving ─► removed (temp)
                             ├─► waiting_brain   (queued for the model)
                             ├─► waiting_approval(hand raised)
                             ├─► blocked         (needs another task)
                             └─► failed ─► idle / leaving
any ─► stopping (user Stop / Stop all / timeout) ─► idle / removed
```

Each state maps to exactly one animation (§11.3), so what you see always matches the backend.

### 9.3 Who may create and delete

| Action | Director | User |
|---|---|---|
| Create temp agent | yes, within caps, no prompt | n/a |
| Create custom (persistent) agent | proposes only, the user confirms | yes |
| Delete temp agent | yes, after its task ends | yes (stops it) |
| Delete custom agent | no | yes (archived for 30 days, can be restored) |
| Delete default agent | no | no (disable only) |

### 9.4 How an agent runs

`WorkerAgent` is an asyncio task running a small tool-use loop: prompt (role + task goal + inputs from earlier tasks), then a model call through `brain.py`, then either a skill call (through Safety, and the approval flow if needed) or a final result. Limits come from the spec. Every step emits a `world.task.progress` event with a short human line ("Reading dell.com spec page"), so the inspector shows a live log. Temp agents start with an empty memory and leave nothing behind except their task log.

## 10. Skills: creating and deleting

Skills are code, so they get a much stricter path than agents.

1. **Need:** the Thinker marks `new_skills` in a plan, or the user clicks **+ Skill** and describes it.
2. **Draft:** the Builder writes a `SkillSpec` (name, description, JSON-Schema params, returns, `required_permissions`, risk) plus a Python module from a fixed template.
3. **Static check:** an AST check allows only listed imports. `exec`, `eval`, `subprocess`, `ctypes` and network or file access are refused unless the matching permission is declared. The risk level is computed from the permissions, never taken from the model.
4. **Test:** the Builder writes 1 to 3 example calls. They run in `sandbox.py` (separate process, timeout, temp working folder).
5. **Review:** the skill appears in the Skills drawer as **Draft**, with code, permissions, risk and test output. **It is never enabled without the user clicking Enable.** If the job is waiting for it, the agent waits with its hand raised.
6. **Use:** enabled skills always run in the sandbox process, through Safety, with the normal approvals for their risk level.
7. **Delete:** disable plus archive to `skills/custom/.archive/`. Agents that list the skill lose it, with a warning on their card.

Files go to `%APPDATA%\JarvisDesktopPet\skills\custom\<name>\v<n>\` with `skill.yaml`, `skill.py` and `tests.json`. Versions are semver, and editing a skill creates a new version.

## 11. The 3D world

### 11.1 Rendering *(calls)*
- three.js (vendored), one `WebGLRenderer`, `CSS2DRenderer` for name tags, speech bubbles and progress chips (crisp text, cheap).
- Stylised low-poly, warm lighting, the amber accent from doc 34. Baked lighting plus one soft shadow light.
- Budget: environment at most 60k triangles, at most 12 avatars on screen, `pixelRatio` capped at 1.5, **render loop paused** when the tab or window is hidden or minimised, and 30 fps when nothing is moving.
- WebGL failure (`onContextCreationError` already exists): fall back to a **2D top-down board** (same stations, flat icons) so the feature still works.

### 11.2 Environments

v1 ships **Office** and **House** *(call)*. Later candidates: Lab, Café, Space station. Each environment is a folder:

```
ui_pet/src/world/envs/office/
  scene.glb          # model, CC0 or own assets, credited in ATTRIBUTIONS.md
  manifest.json
  thumb.webp         # picker card
```

```json
{
  "id": "office",
  "name": "Office",
  "camera": {"home": [8, 7, 8], "target": [0, 0.5, 0]},
  "director": {"pos": [0, 0, 0], "facing": 180},
  "door": [6, 0, -4],
  "stations": [
    {"id": "whiteboard", "for": "thinker", "pos": [-3, 0, -2], "pose": "stand"},
    {"id": "desk_1", "for": "researcher", "pos": [2, 0, 1], "pose": "sit_type"},
    {"id": "spare_1", "for": "any", "pos": [3, 0, 3], "pose": "sit_type"}
  ],
  "waypoints": {"nodes": [[6, 0, -4], [3, 0, -1], [0, 0, 2]], "edges": [[0, 1], [1, 2]]},
  "lighting": {"day": "office_day", "night": "office_night"}
}
```

Spare stations are where temp and custom agents sit. With no spare left, extra agents stand in a "waiting area". That matches the concurrency cap.

### 11.3 Characters and animation
- Every agent is a **Pip-family character**: the same egg body and spring rig as Pip (reused from `pet3d.js`), with a per-role colour and one accessory (headset, glasses, hard hat, ...). On brand, one rig, cheap to animate *(call)*.
- The Director is Pip itself, slightly larger.
- Procedural animation, no skeletal clips at first: walk (bob plus lean), sit and type, think (a bubble with dots), wait for the model (a small hourglass over the head), hand raised (approval), celebrate (hop on done), fail (puff of grey smoke, sad face), arrive and leave through the door.
- Walking follows the waypoint graph (A* over a tiny graph), with no physics.
- When a job has steps that hand data along, a short **glowing paper** flies from one agent to the next. That makes the task graph visible.

### 11.4 Later (not v1)
- Environment packs loaded from `%APPDATA%` with the same manifest, which opens the door to user environments.
- Desk props that react to skills (the monitor shows the page being read).

## 12. Concurrency, the model and limits

- `brain.py` is the **only** way agents reach a model. It keeps a queue with priorities: **interactive** (the current voice or chat job) beats **background**. It runs one call at a time for local LM Studio, configurable to N for cloud.
- Agents waiting in the queue show **waiting_brain** (the hourglass), so the world explains slowness honestly instead of looking stuck.
- **Caps** (config, with defaults *(call)*): 6 active agents besides the Director and defaults, 8 tasks per job, 3 temp agents per job, depth 1, 300 s per task, and a cloud token budget per job and per day.
- **Stop all**, always visible: cancels every task, empties the queue, temp agents leave. Also bound to the existing global hotkey family.
- Loop guard: an agent repeating the same skill call with the same arguments 3 times is stopped and the task fails with a clear reason.

## 13. Protocol

All new topics live under `world.*`. Every event carries `job_id` and, where relevant, `task_id` and `agent_id`. `correlation_id` = `job_id`, so the existing chat, approval and island code keeps matching events.

**Backend to UI (via `ws_bridge`)**

| Topic | Payload (main fields) |
|---|---|
| `world.snapshot` | `env`, `agents[]`, `jobs[]` (open), `skills[]`. Sent on connect and on demand. |
| `world.agent.added` / `.updated` / `.removed` | `agent` (spec + `state` + `task_id`) |
| `world.job.opened` / `.closed` | `job_id`, `text`, `status`, `answer` |
| `world.task.created` | `task` (id, role, goal, needs, agent_id) |
| `world.task.progress` | `task_id`, `line`, `state` |
| `world.task.done` / `.failed` | `task_id`, `result` summary or `error` |
| `world.skill.draft` / `.updated` | skill spec, code, test output, status |

**UI to backend**

| Topic | Payload |
|---|---|
| `world.cmd.say` | `text` (the chat bar; same as `orchestrator.input` today) |
| `world.cmd.stop` | `task_id` / `agent_id` / `all: true` |
| `world.cmd.agent.create` / `.update` / `.delete` | spec / id |
| `world.cmd.skill.create` / `.enable` / `.disable` / `.delete` | description / id |
| `world.cmd.env.set` | `env_id` |

**Internal (bus only)**: `director.plan.request`, `director.plan.result`, `agent.<id>.assign`, `agent.result`, `brain.request`, `brain.result`, `builder.request`, `builder.result`. Approvals keep using `ui.approval` and `ui.approval.response` unchanged, so Pip and the island keep showing approval cards with no change.

Events are diffs on top of the snapshot. Every event carries an increasing `seq`. If the UI sees a gap, it asks for a new snapshot.

## 14. UI (World tab)

```
┌ titlebar ─────────────────────────────────────────────── ─ □ × ┐
│ [World] Activity  Memory  Settings            Office ▾  ⌂  ■ Stop all
├──────────┬─────────────────────────────────────────┬───────────┤
│ ROSTER   │                                         │ INSPECTOR │
│ ● Pip    │            3D scene                     │ Wren      │
│ ● Thinker│     (agents at stations, name tags,     │ writer·tmp│
│ ◐ Resear.│      bubbles, hourglass, hand raised)   │ Task t3   │
│ ○ Watcher│                                         │ "Writing  │
│ ◐ Wren ✦ │                                         │  table…"  │
│ + Agent  │                                         │ log ▸     │
│ Skills ▸ │                                         │ [Stop]    │
│          │                                         │ [Edit][Del]│
├──────────┴─────────────────────────────────────────┴───────────┤
│ 🎤  Ask Pip anything…                                 [Send] ⌄ │
└────────────────────────────────────────────────────────────────┘
```

- **Roster** (left, collapsible): every agent with a state dot, temp agents marked. Click to focus the camera and open the inspector.
- **Inspector** (right drawer): role, kind, model tier, skills, the current task, a live progress log, and Stop / Edit / Delete (as allowed by §9.3).
- **Chat bar** (bottom): the same composer as Chat. `⌄` expands the transcript over the scene. Voice works as today.
- **Job strip** (above the chat bar, only while jobs run): a mini graph of the job's tasks with states. Click a task to focus its agent.
- **+ Agent** form: name, role description, look (colour, accessory, live preview), model tier, skills (checkboxes, risky ones flagged), station.
- **Skills drawer:** list with status (Draft, Enabled, Disabled), risk badge, versions. Draft review shows code, permissions and test output with Enable / Reject.
- **Environment picker** (`Office ▾`): cards with thumbnails. Switching keeps all agents and jobs and only reloads the scene.
- **Camera:** orbit and zoom with the mouse, `⌂` returns home, double-click an agent to follow it.
- **Onboarding:** a new step after "Meet Pip": "Pick your world" (Office / House).
- The **Activity tab** shows the same jobs and tasks as a list (from the same events) for people who prefer text.
- Style follows the doc 34 tokens (`--card`, `--hairline`, amber accent, state glows).

## 15. Data and persistence

| What | Where | Format |
|---|---|---|
| Selected environment, camera, world flags, caps | `config/config.yaml` → `world:` | yaml |
| Default agent overrides + custom agents | `config/agents.yaml` (existing file, new schema) | yaml, `AgentSpec` |
| Custom skills | `skills/custom/<name>/v<n>/` + entries in `config/skills.yaml` | yaml + py + json |
| Jobs, tasks, progress logs | `data/world.db` | sqlite, tables `jobs`, `tasks`, `task_log`; logs kept 30 days |
| Archived agents and skills | `config/.archive/`, `skills/custom/.archive/` | as above |

All paths are under `%APPDATA%\JarvisDesktopPet\`. Temp agents are never written to `agents.yaml`, only to the task history.

## 16. Safety

- Every skill call goes through `SafetyAgent` and `risk_score`. Agents cannot skip it, because `WorkerAgent` has no other way to run a skill.
- The approval UX is unchanged (island and pet cards, timeout = deny), plus the agent's raised hand in the world. Clicking the hand opens the same approval.
- An agent's skill allow-list is enforced by the runtime, not by the prompt.
- Generated skills: static check, sandbox, user Enable (§10). Nothing generated runs in the main backend process.
- The Director can create temp agents only with **existing** skills. A new skill always needs the user.
- Audit: every create, delete, enable and approval goes to `task_log` with who did it (user / director).
- Web content and file content read by agents are data. Prompts tell agents this, and the Director never acts on text found by an agent, only on the Thinker's validated plan.

## 17. Milestones

Each milestone ends with tests in the doc 23/35 style and a short results section added to this doc.

| # | Milestone | Done when |
|---|---|---|
| **M0** | **Runtime, headless.** `core/world/` (state, runtime, brain queue, director, worker loop), protocol events, `world.enabled` flag, old pipeline still the default. | A scripted job ("search X and save it to a file") runs end to end with fake agents in tests. Snapshot plus diffs reproduce the state. Stop all works. |
| **M1** | **Director + default agents for real.** Thinker with the fast path + LLM plans, Researcher, Operator, Watcher, Archivist, Reporter on the new runtime. Approvals moved over. | Every doc 35 voice/chat flow passes with `world.enabled=true`. Fast-path commands are no slower than today (measured). |
| **M2** | **World tab, Office.** Scene, Pip-family avatars, stations, walking, state animations, roster, inspector, chat bar, job strip. | Live jobs are shown correctly. Under 2 ms of render work per idle frame on the target iGPU, paused when hidden, 2D fallback works. |
| **M3** | **Create and delete agents.** Builder temp agents (arrive, work, leave), + Agent form, edit, delete, archive, caps. | The Director spawns and dismisses a temp agent in a real job. The user creates a custom agent and it gets work. Caps and the loop guard are tested. |
| **M4** | **Skills.** Draft, static check, sandbox, review drawer, enable, versions, delete. | A generated skill is drafted, reviewed, enabled and used. A malicious draft (subprocess, network without permission) is rejected in tests. |
| **M5** | **House + polish.** House environment, environment picker, onboarding step, day/night, paper hand-offs, sounds. | Both environments pass the visual checklist. Switching keeps running jobs. |
| **M6** | **QA and release.** Full doc 35 style pass on the installed build, perf on low-end hardware, then `world.enabled=true` by default and the old pipeline removed. | Results table green. README and docs index updated. |

M0 and M1 carry most of the risk and no visuals. M2 is the first point where the world can be seen. M3 to M5 can be reordered if something feels more important once it is visible.

## 18. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Extra hops (Director, Thinker, worker, Reporter) make answers slow on a local model | Anti-goal 1 | Thinker fast path with no LLM. The Reporter is skipped for one-task jobs (the worker's result is the answer). Measured in M1 with a latency budget. |
| One local GPU, many agents | Agents mostly wait | Priority queue, honest "waiting" state, and cloud parallelism when the user has a key. |
| Small local models write bad plans | Failed jobs | JSON schema + one retry. Few-shot plan examples. Heavy tier for the Thinker. |
| Generated skill code is unsafe | Security | AST allow-list, sandbox process, the user must Enable, no auto-enable ever. |
| Runaway spawning or loops | GPU or cloud cost | Hard caps, loop guard, per-job and per-day budgets, Stop all. |
| 3D is slow or hot on laptops | Anti-goal 5 | Triangle and agent budgets, paused loop, 30 fps idle, 2D fallback, quality setting. |
| Asset licences | Release blocker | Own assets or CC0 only, listed in ATTRIBUTIONS.md (lesson from doc 34 §1.1). |
| Scope creep into a game | Never ships | Non-goals in §2. Every milestone ships something usable. |

## 19. Calls made without the owner (please check)

1. The Director has **no LLM at all**. Routing rules live in the Thinker.
2. The **regex fast path stays**, inside the Thinker, so simple commands are not slower.
3. **Default agents:** Thinker, Researcher, Operator, Watcher, Archivist, Reporter, Builder. Safety and voice stay services, not visible agents.
4. **Writer, Coder and similar** are created on demand, not defaults.
5. **Only the Director spawns** (depth 1). Temp agents need no prompt. Persistent agents and every new skill need the user.
6. **Pip-family characters** for all agents, procedural animation, no new rigs.
7. **Office and House** in v1.
8. Caps: 6 extra active agents, 8 tasks per job, 3 temp agents per job, 300 s per task.
9. three.js (vendored) over Babylon, Unity or Godot.
10. Built behind a `world.enabled` flag, with the old pipeline removed only in M6.

## 20. Left to the builder

Exact prompts, the plan JSON schema file, sqlite schema details, the colour and accessory per role, the waypoint layouts, the AST allow-list contents, and the exact latency budget numbers (set in M1 from measurements).
