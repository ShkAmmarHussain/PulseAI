# Agent spec template for dynamic spawning
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class AgentSpec:
    name: str
    role: str = ""
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    model_tier: str = "small"  # small|reasoning
    system_prompt: str = ""
    max_turns: int = 10
    self_terminate: bool = True
    cleanup_on_exit: bool = True
