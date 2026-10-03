# Quick smoke test (structure)
from core.bus import MessageBus, create_event
from core.config import load_config
from core.resources import ResourceTransitionManager
from core.guardrails import risk_score

cfg = load_config()
bus = MessageBus()
rtm = ResourceTransitionManager()
assert risk_score('delete file', {}) >= 8
print('Smoke OK')
