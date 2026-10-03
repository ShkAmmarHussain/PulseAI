# 04. AGENTS

Complete specification of all agents. Each includes: ID, role, purpose, goals, inputs/outputs, tools/skills, model tier, prompt philosophy, behavior, lifecycle, failure handling.

## 4.1 Agent Overview Matrix

| Agent ID | Type | Always-On | Lazy/On-Demand | Model Tier | Core Responsibility |
|---|---|---|---|---|---|
| orchestrator | Supervisor | Yes | No | Reasoning (Qwen3-8B Q5) | Routing, delegation, coordination, arbitration |
| pet_ux | UX/Personality | Yes | No | Small (Llama-3.2-3B Q5) | Emotions, mood, animations, reactions, banter |
| perception | Input | Yes | No | Small (Llama-3.2-3B Q5) | WakeWord, STT, normalize inputs, event emission |
| planner | Strategy | No (spawned or called) | On-Demand/Co-loaded | Reasoning (Qwen3-8B Q5) | Decomposition, DAG, dependencies, replanning |
| 	ool_control | Execution | No | On-Demand when acting | Tool-Coder (Qwen2.5-Coder-7B Q5) | Safe PC control, tool execution, validation |
| ision | Sight | No | **On-Demand (Lazy-Load)** | VLM (Qwen2.5-VL-7B Q5) | UI grounding, OCR+reasoning, click targets |
| memory_agent | Knowledge | Yes | No | Small (Llama-3.2-3B Q5) | Episodic/semantic/procedural, recall, consolidation |
| oice_tts | Output | Yes (process) | No | Tiny (CPU/Kokoro) | Natural TTS, emotion-aware, interruptible |
| safety | Guardrails | Yes (parallel) | No | Small (Llama-3.2-3B Q5) | Risk scoring, approvals, whitelist, veto |
| spawner | Factory | No | On-Demand | Small/Reasoning (3B or Qwen3-8B) | Dynamic agents+skills, validation, registration |

## 4.2 Detailed Agent Specs

### 4.2.1 ORCHESTRATOR (Supervisor)
- **ID:** orchestrator
- **Role:** Lead router/arbitrator
- **Always-On:** Yes
- **Model:** Qwen3-8B Q5_K_M (Reasoning)
- **Purpose:** Single source of delegation truth. Breaks ambiguity, assigns specialists, prevents loops, merges results, enforces safety routing.

**Inputs:** NormalizedIntent + ContextBundle + SystemState
**Outputs:** RoutingPlan, DelegationMap, TaskStatus, OrchestrationDecision
**Skills:** planning, task_manager
**Behavior:** Concise, decisive, structured JSON. Never executes risky actions directly (routes to tool_control + safety).

**System Prompt Focus:** Hub-and-spoke, tool-use only via delegation, prioritize safety, minimal token output.

### 4.2.2 PET_UX (Personality/Emotions)
- **ID:** pet_ux
- **Always-On:** Yes
- **Model:** Llama-3.2-3B Q5_K_M
- **Purpose:** Drives living pet. Mood/emotion engine, animations, reactions, idle personality.
**Drives:** valence/arousal, mood states, animation triggers, speech tone.

### 4.2.3 PERCEPTION
- **ID:** perception
- **Always-On:** Yes
- **Model:** Llama-3.2-3B Q5_K_M (routing/classification only)
- **Purpose:** WakeWord (openWakeWord), streaming STT (faster-whisper), VAD, hotkey/text normalization. Emits structured InputEvent.

### 4.2.4 PLANNER
- **ID:** planner
- **On-Demand:** Yes
- **Model:** Qwen3-8B Q5_K_M
- **Purpose:** Multi-step decomposition → DAG (nodes+deps), critical path, rollback points, replan on failure.

### 4.2.5 TOOL_CONTROL (Execution)
- **ID:** 	ool_control
- **On-Demand:** When actions required
- **Model:** Qwen2.5-Coder-7B-Instruct Q5_K_M
- **Purpose:** Structured tool calls (JSON/function), validation pre-exec, deterministic parameterization. Requires Safety clearance.

### 4.2.6 VISION (On-Demand, Lazy-Load)
- **ID:** ision
- **On-Demand + Lazy-Load + Unload:** Yes (critical)
- **Model:** Qwen2.5-VL-7B-Instruct-GGUF Q5_K_M
- **Purpose:** Screenshot → understand UI, identify elements, generate click coordinates/targets, action grounding, OCR+reasoning. **Lifecycle:** Load→Execute→Unload (VRAM reclaimed).

### 4.2.7 MEMORY_AGENT
- **ID:** memory_agent
- **Always-On:** Yes
- **Model:** Llama-3.2-3B Q5_K_M
- **Purpose:** Episodic/semantic/procedural, recall with recency+relevance, consolidation, decay.

### 4.2.8 VOICE_TTS
- **ID:** oice_tts (process)
- **Always-On:** Yes
- **Engine:** Kokoro (CPU/GPU <400MB), no LLM needed for speech gen
- **Emotion-aware prosody, interruptible, streaming chunks.

### 4.2.9 SAFETY (Parallel Guardrail)
- **ID:** safety
- **Always-On (parallel):** Yes
- **Model:** Llama-3.2-3B Q5_K_M
- **Purpose:** Risk scoring (0–10), destructive detection, whitelist, session trust, can **VETO**. Runs in parallel with Tool Agent pre-exec.

### 4.2.10 SPAWNER (Dynamic Factory)
- **ID:** spawner
- **On-Demand:** Yes
- **Model:** 3B Q5 or Qwen3-8B (select by complexity)
- **Purpose:** Create sub-agents + Skills dynamically, validate JSON schemas, register in registry, lifecycle mgmt, self-terminate.

## 4.3 Agent Communication Contract
All agents emit/consume typed events via Message Bus (JSON Schema). Strict I/O contracts, deterministic handoffs. See 18. IPC.
