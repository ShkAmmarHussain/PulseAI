# 07. DYNAMIC AGENTS & SKILLS

Core requirement: Multi-agent divides tasks, creates skills and agents if needed.

## 7.1 Philosophy
Self-extending system. Safe dynamic creation with validation, registration, versioning, lifecycle.

## 7.2 Dynamic Agent Creation (Spawner)
**Trigger:** Novel task, exceeds single agent scope, needs specialization, repeated pattern emerges.

**Process:**
1. Orchestrator detects need → calls Spawner
2. Spawner analyzes task, extracts role, required skills, tools, model tier
3. Generate AgentSpec (JSON): id, role, goal, backstory, tools[], model_tier, lifecycle, termination_condition
4. Validate (schema, safety, no recursion, resource budget)
5. Instantiate sub-agent (Smolagents) with isolated context
6. Register in active_agents, run, self-terminate on done/timeout
7. Cleanup, log

**Constraints:** max depth 6, max active 3–4, no self-recursion, resource cap.

## 7.3 Dynamic Skill Creation
When capability missing:
1. Task analysis → identify missing function
2. Generate SkillSpec: name, description, params JSON Schema, returns, safety, approvals
3. Safety validation (high-risk flagged, sandboxed)
4. Code scaffold (thin wrapper, validation, errors)
5. Register in registry (versioned, enabled/disabled)
6. Persist config/skills.yaml (append, non-destructive)
7. Reload, expose to agents

**Safety Gates:** Schema valid, no arbitrary exec without shell allowlist, L3 requires human approval path, must not bypass guardrails.

## 7.4 Agent Lifecycle (Dynamic)
create → init → register → execute → complete/error → unregister → cleanup (memory trimmed)

## 7.5 Versioning & Idempotency
Skills versioned (semver), agents named worker.<task>-<n>, dedupe similar specs.

## 7.6 Examples
Complex multi-app workflow → spawn worker.file_organizer, can create skill.classify_by_ext if useful, persist for reuse.

## 7.7 Governance
Dynamic creations logged, auditable, never auto-enable dangerous without approval (configurable).
