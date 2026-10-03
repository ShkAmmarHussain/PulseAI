# 05. ORCHESTRATION

## 5.1 Orchestrator Philosophy
Hub-and-spoke supervisor. Decisive router, never micromanages specialists. Delegation-first, execution-second.

## 5.2 Core Responsibilities
- Request classification (chat/action/complex/multi-step/vision-needed)
- Task decomposition, DAG construction (via Planner or direct)
- Delegation mapping, specialist selection
- Handoff management, state synchronization
- Merge results, conflict resolution
- Loop prevention, timeout, retry policy
- Resource gating (VRAM: trigger lazy-load/unload)
- Arbitration between agents

## 5.3 Delegation Rules (Priority Order)

| Condition | Primary | Secondary | Notes |
|---|---|---|---|
| Ambiguity | Orchestrator→Planner | Memory | Clarify before acting |
| UI elements, click, read dialog | Vision (on-demand) | OCR fallback | Lazy-load VLM |
| File/app/mouse/kb/shell | Tool_Control + Safety (parallel) | — | High-risk gated |
| Needs new capability | Spawner | Planner | Dynamic create |
| Memory recall/store | Memory_Agent | — | Single source |
| Voice output | Voice_TTS | Pet_UX | Emotion-aware |
| Mood/animations | Pet_UX | — | Personality owner |

## 5.4 Task Routing Matrix

| User Intent | Type | Agents Involved | Flow |
|---|---|---|---|
| "How are you?" | Chat | Orchestrator, Pet_UX, Voice_TTS | Fast path |
| "Open Notepad" | Action (single) | Orchestrator→Tool+Safety | Gated |
| "Organize Downloads by type" | Multi-step | Orchestrator→Planner→Spawner(sub-agent?) or Tool | DAG, parallel safe |
| "Click Save in that dialog" | Vision+Action | Orchestrator→Vision(load)→Tool+Safety→Vision(unload) | Lazy-load |
| "Remember I prefer dark theme" | Memory | Orchestrator→Memory_Agent | Store |
| "Complex research+execute" | Dynamic | Orchestrator→Spawner (create worker) | Auto-spawn sub-agents+skills |

## 5.5 Orchestration Loop
1. Intake → Classify
2. Recall context
3. Plan (if complex)
4. Risk assess (Safety pre)
5. Delegate (specialists)
6. Monitor (events)
7. Aggregate results
8. Verify (outcome)
9. Respond + Memorize
10. Cleanup (unload on-demand)

## 5.6 Handoff Protocol
Typed HandOffEvent: {from,to,task_id,context,deps,ttl,expected_outputs}. Idempotent, traceable.

## 5.7 Loop Prevention
- Task depth limit (max recursion/depth 6)
- Sub-agent spawn cap (max active 3–4)
- Plan revision cap (max 3 replans)
- Deterministic task IDs, dedupe recent

## 5.8 Resource Orchestration (VRAM)
Orchestrator enforces: if vision_needed → unload non-essential heavy (Orchestrator/Tool may role-swap to 3B), load VLM, run, unload, restore. See 09.

## 5.9 Multi-Agent Coordination Guarantees
- Single active executor per high-risk action (mutex)
- Parallel read-only safe, sequential for side-effects
- Safety Agent runs in parallel (read-only veto path)
