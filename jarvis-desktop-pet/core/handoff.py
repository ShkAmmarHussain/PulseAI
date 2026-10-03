from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import time
import uuid


@dataclass
class HandoffEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    task_id: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    deps: list = field(default_factory=list)
    ttl_ms: int = 60000
    expected_outputs: list = field(default_factory=list)
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
