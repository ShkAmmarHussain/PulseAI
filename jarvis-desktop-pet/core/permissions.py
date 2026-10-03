import time
from typing import Dict, Optional, Set


class SessionGrants:
    def __init__(self):
        self._grants: Dict[str, float] = {}
        self._denied: Set[str] = set()

    def grant(self, key: str, ttl_minutes: int = 30):
        self._grants[key] = time.time() + ttl_minutes * 60

    def is_granted(self, key: str) -> bool:
        exp = self._grants.get(key)
        if not exp:
            return False
        if time.time() > exp:
            del self._grants[key]
            return False
        return True

    def deny(self, key: str):
        self._denied.add(key)

    def is_denied(self, key: str) -> bool:
        return key in self._denied
