# Jarvis Desktop Pet - Documentation Index

> **Purpose:** Complete, exhaustive documentation covering every aspect of building a local multi-agent Jarvis-like desktop pet from start to end. Nothing skipped.

This project is designed to run 100% locally using your 3060 12GB GPU with LM Studio.

## Quick Navigation

### Core Understanding
- [01. Overview](./01-OVERVIEW.md) - Project goals, vision, philosophy, success criteria
- [02. Architecture](./02-ARCHITECTURE.md) - High-level system design, layers, principles
- [03. Pipeline](./03-PIPELINE.md) - End-to-end data flow, request lifecycle, execution pipeline
- [26. Glossary](./26-GLOSSARY.md) - Terms, definitions, acronyms

### Agents & Orchestration
- [04. Agents](./04-AGENTS.md) - All agents, roles, responsibilities, prompts, behaviors
- [05. Orchestration](./05-ORCHESTRATION.md) - Supervisor, delegation, handoffs, task routing
- [07. Dynamic Agents & Skills](./07-DYNAMIC_AGENTS_SKILLS.md) - Auto-spawning, dynamic skill creation, self-expansion

### Capabilities
- [06. Skills](./06-SKILLS.md) - Complete skill registry, schemas, parameters, safety per skill
- [11. Vision](./11-VISION.md) - Screen capture, OCR, VLM, UI grounding, on-demand loading
- [10. Voice](./10-VOICE.md) - Wake word, STT, TTS, Kokoro, streaming, latency
- [12. Memory](./12-MEMORY.md) - Episodic, semantic, procedural, ChromaDB, learning
- [13. PC Control](./13-PC_CONTROL.md) - Mouse/kb, apps, shell, files, browser, safety

### Technical Details
- [08. Models](./08-MODELS.md) - LM Studio models, quantization, role-split, VRAM strategy
- [09. Hardware](./09-HARDWARE.md) - 3060 12GB analysis, headroom, optimization, thermal
- [18. IPC & Message Bus](./18-IPC_MESSAGE_BUS.md) - Async pub/sub, events, schemas, protocols
- [14. Safety & Guardrails](./14-SAFETY_GUARDRAILS.md) - Approvals, whitelists, risk scoring, vetoes

### Configuration & Structure
- [15. Config](./15-CONFIG.md) - YAML configs, defaults, validation, environment
- [16. Personality](./16-PERSONALITY.md) - Jarvis personality, emotions, mood engine
- [17. File Structure](./17-FILE_STRUCTURE.md) - Complete repo layout, purpose of every file
- [19. Dependencies](./19-DEPENDENCIES.md) - All packages, versions, rationale, install notes

### Implementation & Operations
- [20. Setup](./20-SETUP.md) - Windows setup, LM Studio, models, first run, verification
- [21. Implementation](./21-IMPLEMENTATION.md) - Step-by-step build instructions, code patterns, checkpoints
- [22. Timeline](./22-TIMELINE.md) - Phased roadmap, milestones, effort, buffers
- [23. Testing](./23-TESTING.md) - Unit/integration/e2e, safety tests, performance, regression
- [24. Troubleshooting](./24-TROUBLESHOOTING.md) - Issues, fixes, logs, diagnostics
- [25. Roadmap](./25-ROADMAP.md) - Future work, enhancements, research

### Product Revamp & Competitive Strategy
- [27. UI Revamp](./27-UI-REVAMP.md) - Master UI specification, command center, component system
- [28. Competitive Comparison](./28-COMPETITIVE-COMPARISON-COUCOU-HEYJEV.md) - Deep comparative analysis: PulseAI vs Coucou vs Hey Jev
- [29. Hybrid Revamp Spec](./29-HYBRID-REVAMP-IMPLEMENTATION-SPEC.md) - Implementation blueprint adopting Coucou & Hey Jev strengths + product-grade pet revamp
- [30. Opencode UI Revamp Master Plan](./30-OPENCODE-UI-REVAMP-MASTER-PLAN.md) - Master fix & implementation blueprint for opencode: pet overhaul, dynamic island, and workspace polish

---

## Reading Order (Recommended)

**First-time reader (understand full system):** 00 → 01 → 02 → 03 → 08 → 09 → 04 → 05 → 07 → 06 → 14 → 10/11/12/13 → 15–19 → 20–25

**Implementer (build phase-by-phase):** 20 → 21 (follow phase order) + reference docs as needed.

**Nothing is skipped.** Every design decision, trade-off, schema, command, and rationale is documented.
