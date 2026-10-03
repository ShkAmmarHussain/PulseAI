from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ModelRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    TOOL_CONTROL = "tool_control"
    VISION = "vision"
    PET_UX = "pet_ux"
    PERCEPTION = "perception"
    MEMORY = "memory_agent"
    SAFETY = "safety"
    VOICE_TTS = "voice_tts"
    SPAWNER = "spawner"


@dataclass
class ModelSpec:
    role: ModelRole
    model_id: str
    quant: str
    temperature: float
    max_tokens: int
    always_on: bool = False
    tool_calling: bool = False
    on_demand: bool = False
    lazy_load: bool = True
    unload_after_ms: int = 30000
    unload_idle_ms: int = 60000
