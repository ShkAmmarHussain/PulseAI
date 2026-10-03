# 15. CONFIG

YAML configs, validation, defaults.

## 15.1 Config Files
- config/agents.yaml – Roles, models, prompts, always-on
- config/skills.yaml – Registered skills, versions, enabled
- config/permissions.yaml – Whitelists, allowlists, session policy
- config/personality.yaml – Jarvis personality, mood
- config/system.yaml – Bus, VRAM, timeouts, paths
- config/voice.yaml – WakeWord/STT/TTS
- config/vision.yaml – Capture regions, lazy-load
- config/memory.yaml – Chroma, consolidation

## 15.2 Validation
Pydantic/dataclass + startup validation. Defaults safe.

## 15.3 Hot Reload
Watch config (selective), non-destructive.
