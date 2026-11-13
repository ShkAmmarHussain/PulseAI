# 36. VISION: THE MINI WORLD (3D multi-agent workspace)

Status: **vision / design, waiting on approval. No code yet.** Visual design canvas: World tab looks, the building cutaway and the chibi sheet (claude.ai artifact, private to the owner). Next step after approval: an implementation plan per milestone (§17).

Decided with the owner (2026-11-14):
- The world exists so you can **see what Jarvis is doing**, have **more control**, **extend it** with new agents and skills, and have it **look new and interesting**.
- **Approach A:** the world is a new **World** tab and the **home screen** of the main window. Memory, Activity and Settings stay as tabs. Pip and the top-edge island are unchanged.
- The **main agent never does work itself**, thinking included. It only routes, creates and deletes agents, and hands out tasks.
- The main agent has **default agents** under it, and can **create or delete agents and skills** when needed.
- Agents **appear in the 3D world while working** and are **removed by the main agent** when their task is done.

Everything else in this doc is a proposal. Each call made without the owner is marked *(call)*. The full list is in §19.

---

## 1. The idea in one paragraph

The world is a small 3D office building, PulseAI HQ, cut open so you can see every floor and room. In the Director's office sits the **Director**, the main agent (Pip). You talk to the Director by voice or chat. The Director does not think or act. It sends every request to a **Thinker** agent, gets back a plan, and gives each piece to an agent in their room. You watch them work: someone in the research lab browsing, someone in the archive searching memory, someone in the watch room looking at the screen. When the job needs a specialist that does not exist, the Director asks the **Builder** to create one. A new chibi with its own unique look walks in through the lobby, takes the lift to a spare room, works, reports, and walks out when the Director dismisses it. You can click any agent to see what it is doing, stop it, edit it or delete it, and you can create your own agents and skills.

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
- No user-built buildings or level editor. The building and its themes ship with the app (§11.4 keeps the door open).
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
| **World** | The 3D scene in the World tab. Set inside the building. |
| **Building** | PulseAI HQ: the 3D cutaway of floors and rooms the world is set in, defined by a modular kit plus `building.json` (§11). |
| **Director** | The main agent, shown as Pip. Routes only. Never calls an LLM and never runs a tool. |
| **Agent** | A worker with a role, a model tier, allowed skills and a look. It is **default** (ships with the app, never removed), **custom** (made by the user, persistent) or **temp** (made by the Director for one job, removed when done). |
| **Skill** | A callable capability (Python), for example `web_search`, `file_ops`. Agents use skills. Skills have permissions and a risk level. |
| **Job** | One user request, from what you said to the final answer. |
| **Task** | One piece of a job, given to one agent. A job is a small graph of tasks. |
| **Room** | A room in the building where an agent works (Planning room, Research lab, ...). Spare rooms hold new agents. |

## 6. Architecture

```
┌──────────────── Tauri UI (main window) ─────────────────────────────┐
│ World tab (home)                                                    │
│   world/scene.js      three.js renderer, building loader, camera   │
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

They are always present, sitting in their rooms when idle. None can be deleted. Each can be disabled and edited (name, look, model tier, prompt additions).

| Agent | Room | Does | Skills | Tier |
|---|---|---|---|---|
| **Director** (Pip, amber egg) | Director's office, F3 | routes, staffs, tracks. No LLM. | none | none |
| **Thinker** | Planning room, F3 | turns a request into a plan. Fast path first. | none (plan only) | heavy |
| **Researcher** (Rhea) | Research lab, F2 | web search, read pages | `web_search`, `browser` (read) | fast |
| **Operator** (Otto) | Ops room, F2 | files, apps, shell, keyboard and mouse | `file_ops`, `app_control`, `shell`, `input_control` | fast |
| **Watcher** (Vee) | Watch room, F2 | screen and image understanding | `screen_vision` | vision |
| **Archivist** (Ada) | Archive, F1 | recall and store memories | `memory_skills` | fast |
| **Reporter** (Remy) | Lobby front desk, F1 | writes the final answer for chat and voice | none | fast |
| **Builder** (Bodie) | Workshop, F3 | creates temp and custom agents and drafts new skills | `create_agent`, `draft_skill` | heavy |

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
look: {seed: 7f3a, skin: 3, hair_style: bob, hair_color: blue, outfit: lilac, accessory: glasses}
room: auto                # a room id, or auto (free spare room)
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
- Budget: building at most 60k triangles, at most 12 avatars on screen, `pixelRatio` capped at 1.5, **render loop paused** when the tab or window is hidden or minimised, and 30 fps when nothing is moving.
- WebGL failure (`onContextCreationError` already exists): fall back to a **2D flat cutaway** (same floors and rooms, chibi icons) so the feature still works.

### 11.2 The building (decided 2026-11-14)

The world is **one building, PulseAI HQ, cut away like a dollhouse**: floors stacked vertically, each split into rooms, with a lift shaft on the side. three.js renders it in 3D. The default camera looks at the cut face with a slight tilt, and the user can orbit, zoom or click a floor number to focus one floor. *(Owner: "a building divided by floors and rooms, like an office". This replaces the earlier idea of separate Office and House scenes.)*

Default layout (3 floors x 3 rooms) *(call)*:

| Floor | Rooms |
|---|---|
| 3 | Planning room (Thinker), Director's office (Pip), Workshop (Builder) |
| 2 | Research lab (Researcher), Ops room (Operator), Watch room (Watcher) |
| 1 | Lobby with the front door and front desk (Reporter), Archive (Archivist), Studio (spare) |

- New agents enter through the **lobby door**, take the **lift** if their room is on another floor, and leave the same way.
- **Spare rooms** hold temporary and custom agents. When every room is full, the building **grows a floor** (a new floor of spare rooms slides in on top). Empty extra floors are removed after a while. The concurrency cap (§12) bounds this.
- Each room has its own lamp colour and props matching the role. A room's lamp turns amber when someone inside needs approval.
- The building is described by a manifest instead of free-placed stations:

```
ui_pet/src/world/building/
  kit.glb            # modular room shell, slab, lift, props (own or CC0 art)
  building.json      # floors, rooms, lift, camera presets, lighting
```

```json
{
  "floors": [
    {"num": 3, "rooms": [
      {"id": "planning", "name": "Planning room", "for": "thinker", "props": ["whiteboard"], "lamp": "#818cf8"},
      {"id": "director", "name": "Director's office", "for": "director", "props": ["desk"]},
      {"id": "workshop", "name": "Workshop", "for": "builder", "props": ["bench"]}
    ]}
  ],
  "lift": {"side": "right"},
  "lobby": {"floor": 1, "room": "lobby", "door": "left"},
  "grow": {"rooms_per_floor": 3, "max_floors": 6}
}
```

- Themes (Night Studio by default: dark shell, warm amber lights, matching the doc 34 tokens) are swapped by lighting and materials, not by new models. The environment picker becomes a **theme picker** for the same building.

### 11.3 Characters (decided 2026-11-14)
- **Pip stays the amber egg**, so the Director is always recognisable *(call)*.
- **Every other agent is a chibi**: a big head, a small body and stubby legs, built from a small modular kit (head, hair, outfit, accessory meshes) on one shared rig.
- **Default agents have fixed looks and names** (Thinker, Bodie the Builder, Rhea the Researcher, Otto the Operator, Vee the Watcher, Ada the Archivist, Remy the Reporter). The user can restyle them.
- **Every new agent that is not in that list gets a unique generated look** *(owner)*. The look is seeded from the agent id. Parts: skin (6), hair style (5), hair colour (8), outfit (10, tinted toward the role), accessory (5), which gives about 12,000 combinations. The generator rerolls if an active agent already has the same combination. The inspector offers **Reroll look** and **Customise**. **Keep as custom** keeps the look, the name and a room.
- `AgentSpec.look` becomes `{seed, skin, hair_style, hair_color, outfit, accessory}`, so the same agent always looks the same.
- Temporary agents wear a **dashed name tag** until they leave.
- Animation is still procedural on one rig: walk, ride the lift, sit and type, think (bubble), wait for the model (hourglass), raise a hand (approval), hop (done), grey puff (failed), wave goodbye at the door.
- Work handed between agents shows as a glowing paper carried along the corridor or up the lift.
- The 2D fallback (WebGL failure) draws the same building as a flat cutaway with chibi icons.

### 11.4 Later (not v1)
- Building themes and room kits loaded from `%APPDATA%` with the same manifest, which opens the door to user-made rooms.
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
│ [World] Activity  Memory  Settings            Floor All 3 2 1  ⌂  ■ Stop all
├──────────┬─────────────────────────────────────────┬───────────┤
│ ROSTER   │                                         │ INSPECTOR │
│ ● Pip    │            3D scene                     │ Wren      │
│ ● Thinker│     (agents in rooms, name tags,      │ writer·tmp│
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
- **+ Agent** form: name, role description, look (generated, with reroll and customise, live preview), model tier, skills (checkboxes, risky ones flagged), room.
- **Skills drawer:** list with status (Draft, Enabled, Disabled), risk badge, versions. Draft review shows code, permissions and test output with Enable / Reject.
- **Floor buttons** (All, 3, 2, 1) focus the camera on a floor. A **theme picker** swaps lighting and materials. Switching keeps all agents and jobs.
- **Camera:** orbit and zoom with the mouse, `⌂` returns home, double-click an agent to follow it.
- **Onboarding:** a new step after "Meet Pip": "Meet your team" (the building tour, then a theme).
- The **Activity tab** shows the same jobs and tasks as a list (from the same events) for people who prefer text.
- Style follows the doc 34 tokens (`--card`, `--hairline`, amber accent, state glows).

## 15. Data and persistence

| What | Where | Format |
|---|---|---|
| Selected theme, camera, world flags, caps | `config/config.yaml` → `world:` | yaml |
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
| **M2** | **World tab, the building.** 3-floor cutaway, lift, chibi kit with the default team, walking, state animations, roster, inspector, chat bar, job strip. | Live jobs are shown correctly. Under 2 ms of render work per idle frame on the target iGPU, paused when hidden, 2D fallback works. |
| **M3** | **Create and delete agents.** Builder temp agents (arrive, work, leave), + Agent form, edit, delete, archive, caps. | The Director spawns and dismisses a temp agent in a real job. The user creates a custom agent and it gets work. Caps and the loop guard are tested. |
| **M4** | **Skills.** Draft, static check, sandbox, review drawer, enable, versions, delete. | A generated skill is drafted, reviewed, enabled and used. A malicious draft (subprocess, network without permission) is rejected in tests. |
| **M5** | **Growth + polish.** Look generator (reroll, customise), floors that grow, theme picker, onboarding step, day/night, paper hand-offs, sounds. | Ten generated agents in a row all look different. The building grows and shrinks. The visual checklist passes. |
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
6. **Pip stays an egg**, every other agent is a chibi on one modular rig, procedural animation.
7. **One building** with 3 floors x 3 rooms by default, growing a floor when full. The environment picker becomes a theme picker.
8. Caps: 6 extra active agents, 8 tasks per job, 3 temp agents per job, 300 s per task.
9. three.js (vendored) over Babylon, Unity or Godot.
10. Built behind a `world.enabled` flag, with the old pipeline removed only in M6.

## 20. Left to the builder

Exact prompts, the plan JSON schema file, sqlite schema details, the colour and accessory per role, the waypoint layouts, the AST allow-list contents, and the exact latency budget numbers (set in M1 from measurements).
