# Minimal agent registry/factory
from agents.orchestrator import OrchestratorAgent
from agents.perception import PerceptionAgent
from agents.pet_ux import PetUXAgent
from agents.safety import SafetyAgent
from agents.memory_agent import MemoryAgent
from agents.planner import PlannerAgent
from agents.tool_control import ToolControlAgent
from agents.vision import VisionAgent
from agents.voice_tts import VoiceTTSAgent
from agents.spawner import SpawnerAgent


AGENTS = {
    "orchestrator": OrchestratorAgent,
    "perception": PerceptionAgent,
    "pet_ux": PetUXAgent,
    "safety": SafetyAgent,
    "memory_agent": MemoryAgent,
    "planner": PlannerAgent,
    "tool_control": ToolControlAgent,
    "vision": VisionAgent,
    "voice_tts": VoiceTTSAgent,
    "spawner": SpawnerAgent,
}
