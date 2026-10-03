from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SkillSpec:
    name: str
    version: str = "0.1.0"
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[str] = field(default_factory=list)
    risk_level: int = 3
    enabled: bool = False
