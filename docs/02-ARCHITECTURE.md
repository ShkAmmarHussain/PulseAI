# 02. ARCHITECTURE

## 2.1 Overview
Layered, modular, event-driven multi-agent architecture. Hub-and-spoke (Supervisor) with specialist agents, dynamic spawning, skill registry.

## 2.2 Core Architectural Principles

1. **Separation of Concerns** - Perception/Input, Reasoning/Planning, Execution/Tools, Memory, Output/UX isolated.
2. **Hub-and-Spoke Orchestration** - Orchestrator central router, avoids mesh complexity, clear delegation.
3. **Lazy/Eager Hybrid** - Always-on minimal set (3B), heavy (Reasoning/VLM) loaded on-demand.
4. **Role-Based Specialization** - Each agent optimized for task type, can use different model tier.
5. **Safety-in-Depth** - Permission layer + Safety Agent (parallel veto) + guardrails + whitelists.
6. **Event-Driven** - Async pub/sub, non-blocking, loosely coupled.
7. **Self-Extensibility** - Dynamic agent/skill creation with validation + registration.
8. **Resource-Conscious** - VRAM budget enforced, unload on idle, role-swapping.

## 2.3 System Layers

| Layer | Components | Responsibility |
|---|---|---|
| **L0 UI/Overlay** | Pet (Tauri/Desktop Pet fork), Bubbles, Approval UI, Status | Always-on-top pet, visual feedback, human-in-loop UI |
| **L1 Perception** | WakeWord, STT, Screen Capture, OCR | Sensory input normalization → events |
| **L2 Orchestration** | Orchestrator, Bus, State | Routing, decomposition, delegation, coordination |
| **L3 Cognition** | Planner, Memory Agent, Reasoning | Planning, learning, long-term context |
| **L4 Execution** | Tool Agent, Skills, Safety, Guardrails | Safe PC action execution |
| **L5 Vision (On-Demand)** | Vision Agent + VLM | UI understanding/grounding |
| **L6 Voice/Output** | Voice/TTS Agent, Kokoro | Natural speech, emotion-aware |
| **L7 Memory/Storage** | ChromaDB, JSON, Config | Persistence, recall, config |
| **L8 Runtime** | LM Studio (OpenAI), Models, Process Mgmt | LLM inference, lifecycle |

## 2.4 High-Level Diagram (Text)

`	ext
User Voice/Text → Perception → Orchestrator (Supervisor)
                        │
                        ├─→ Pet/UX (animations/mood)
                        ├─→ Planner (decomposition)
                        ├─→ Memory (recall/context)
                        ├─→ Tool/PC-Control (safe exec) ← Safety (parallel veto)
                        ├─→ Vision (on-demand VLM) ← unload after
                        ├─→ Voice/TTS (output)
                        └─→ Spawner (dynamic agents+skills)
All ↔ Message Bus (async pub/sub) + Global State
Models: LM Studio (OpenAI-compatible, role-split, lazy-load)
UI: Desktop Pet (overlay, always-on-top)
`

## 2.5 Data Flow Summary
Request → Event → Normalize → Orchestrate → Plan → Recall → Execute (gated) → Observe → Respond (Voice/UI) → Memorize.

## 2.6 Design Tradeoffs

| Tradeoff | Choice | Rationale |
|---|---|---|
| Mesh vs Hub-Spoke | Hub-Spoke | Deterministic routing, easier debugging, less token churn |
| Monolith vs Multi-Agent | Multi-Agent | Specialization, division of work, dynamic expansion |
| Eager vs Lazy VLM | Lazy (on-demand) | VRAM critical (12GB), only when UI interaction needed |
| Role-Split vs Single Model | Role-Split | VRAM efficient + task-optimized + stability |
| Python vs Tauri UI | Fork Desktop Pet (Python) | Huge time/save, pet logic exists, IPC easy |
| Safety Strict vs Permissive | Conservative default | User safety, trust built gradually (session grants) |
