# 06. SKILLS

Complete skill registry. Every skill: ID, category, purpose, description, parameters (JSON Schema), returns, preconditions, postconditions, safety level, required approvals, examples, error handling.

## 6.1 Skill Taxonomy

| Category | Skills | Purpose |
|---|---|---|
| Files | file_ops | FS read/write/move/delete/search/copy/backup |
| Apps | app_control | Launch/focus/close/list windows/processes |
| Input | input_control | Mouse/kb/hotkeys/scroll (high-risk) |
| Shell | shell | CLI/PowerShell/cmd, safe execution |
| Web/Browser | browser | URLs, search, navigate, extract |
| Perception | screen_vision | Capture/OCR/VLM elements |
| Memory | memory_store, memory_search | RAG/episodic/semantic/procedural |
| Reasoning | planning | Decomposition/DAG |
| UX | notify | Bubbles/speech/status |
| Audio | wakeword, stt, tts | Voice I/O |
| Workflow | task_manager | Multi-step tracking/resume/rollback |
| System | system_info | Safe diagnostics (read-only) |

## 6.2 Safety Levels Per Skill
L0 Safe (read-only), L1 Low, L2 Medium, L3 High (destructive/moves input). See 14.

## 6.3 Core Skill Specs (Detailed)

### 6.3.1 skill.file_ops
- **Safety:** L2–L3 (delete/move/overwrite require confirm)
- **Ops:** read, write, append, copy, move, delete, exists, list, glob, backup, trash
- **Path safety:** Root allowlist, no traversal above project/user safe dirs by default, realpath validation

### 6.3.2 skill.app_control
- **Safety:** L1
- **Focus/launch/close, window list, PID, is_running

### 6.3.3 skill.input_control (HIGH RISK)
- **Safety:** L3
- **mouse_move(x,y,relative), mouse_click(btn), mouse_scroll, key_type, key_press, hotkey**
- **Approvals:** Always require approval unless session_grant + whitelist app/region

### 6.3.4 skill.shell
- **Safety:** L3
- **Allowlist commands, timeout, cwd, capture stdout/stderr, no shell injection, block dangerous (format, rm -rf wildcards) by default

### 6.3.5 skill.browser
- **Safety:** L1–L2

### 6.3.6 skill.screen_vision
- **Safety:** L0 (read-only capture)
- **capture(region), ocr(region), find_elements(query), ground_action(desc) → coords

### 6.3.7 skill.memory_store/search
- **Safety:** L0

### 6.3.8 skill.planning
- **Safety:** L0 (DAG, deps, risks)

### 6.3.9 skill.notify
- **Safety:** L0

### 6.3.10 skill.wakeword/stt/tts
- **Safety:** L0

### 6.3.11 skill.task_manager
- **Safety:** L0 (tracking)

## 6.4 Skill Schema Format (JSON Schema)
All skills expose: name, description, version, parameters (JSON Schema), returns, required_approvals[], safety_level, preconditions[], postconditions[], examples[].

## 6.5 Skill Registry
Stored config/skills.yaml + runtime skills/registry.py (discoverable, versioned, can be disabled).
