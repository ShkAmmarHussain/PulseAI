from enum import Enum
from typing import Dict, Any


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    SPEAKING = "speaking"
    ERROR = "error"


class GlobalState:
    def __init__(self):
        self.agent_state: Dict[str, AgentState] = {}
        self.shared: Dict[str, Any] = {}
