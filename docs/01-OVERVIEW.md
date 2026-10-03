# 01. OVERVIEW

## 1.1 Project Name
**Jarvis Desktop Pet** - A fully local, multi-agent AI assistant with a living desktop pet interface.

## 1.2 Vision
Create a true Jarvis-like assistant that feels alive: a floating digital pet that stays on-screen, converses naturally, learns continuously, and can actually control the PC to accomplish tasks. All while running 100% locally with no cloud dependencies.

## 1.3 Core Goals

1. **Local-First & Private** - Everything runs on-device. No API calls to external services. User data never leaves the machine.
2. **Living Digital Pet** - Animations, moods, emotions, idle behavior, reactions. Feels like a companion, not a window.
3. **True Multi-Agent System** - Not a single monolithic LLM call. Specialized agents divide work, coordinate, spawn sub-agents, and create new Skills dynamically.
4. **Advanced Enough to Make Proper Decisions** - Capable of planning, reasoning, self-correction, handling ambiguity, and multi-step task execution.
5. **PC Control That Actually Works** - Safe, controllable desktop automation (apps, files, mouse/kb, CLI, UI interaction via vision).
6. **Jarvis-Like Voice** - Wake word "Hey Jarvis", natural conversational STT/TTS with emotion-aware speech.
7. **Learns & Grows** - Long-term memory across sessions. Builds understanding of user, habits, projects, preferences over time.
8. **Safe By Design** - Explicit approvals, whitelists, risk scoring, parallel guardrails, veto system. Never destructive without consent.
9. **Resource-Aware (3060 12GB)** - Role-based model splitting, lazy-loading, on-demand vision, VRAM-conscious design.
10. **Modular & Extensible** - Skill system, dynamic agent creation, self-expanding capabilities.

## 1.4 Problem Statement Recap
You want: AI assistant like a short bot that stays active on PC, chats with you, controls PC, does what told. Like digital pets. Multi-agent, divides tasks, creates skills/agents if needed. LM Studio installed. Full detailed docs, no skipping.

## 1.5 Success Criteria

| Criterion | Definition | Success Metric |
|---|---|---|
| **Pet Feel** | Lives, reacts, has personality | Pet exhibits moods, animations change with state, feels alive |
| **Latency (Voice)** | Wake→response feels natural | Wake→first response < 1.5s (target < 1.0s) |
| **Reliability (Tool Use)** | Executes correctly | Tool call success rate ≥ 95% on structured tasks |
| **Safety** | No unintended destructive actions | 100% of high-risk actions gated by approval/veto |
| **Multi-Agent Division** | Actually splits work | Orchestrator decomposes ≥90% of complex requests into sub-tasks |
| **Dynamic Expansion** | Creates skills/agents when needed | Successfully registers new Skills on first encounter of novel task type |
| **VRAM Stability** | Stays within 12GB | Peak VRAM < 11.5GB, no OOM under normal workflows |
| **Local-Only** | No external calls | Zero outbound network calls during normal operation (offline-capable) |
| **Learning** | Retains across sessions | Recalls facts after restart, builds persistent user model |

## 1.6 Non-Goals
- Cloud sync/multi-device (intentional local-first)
- Subscription/API dependency
- Generic chatbot UI (must be pet-first)
- Maximal VRAM usage (efficiency prioritized)

## 1.7 Design Philosophy
- **Pragmatic over perfect** - Working MVP first, polish iteratively
- **Safety > Autonomy** - Autonomy increases gradually with session trust
- **Pet-first UX** - Assistant lives as character, not app window
- **Explainable** - Actions traceable, decisions inspectable
- **Self-Extending** - System can grow its own capabilities safely
