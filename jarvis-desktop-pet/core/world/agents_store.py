"""Persistence for custom agents (doc 36 §9.3, §15).

Custom agents survive restarts; deleted ones are archived for 30 days so a
delete can be undone. Temp agents are never written here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

ARCHIVE_DAYS = 30


class AgentStore:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            from core.config import DATA_DIR

            path = DATA_DIR / "world_agents.json"
        self.path = Path(path)

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("agents", [])
                data.setdefault("archive", [])
                return data
        except (OSError, ValueError):
            pass
        return {"agents": [], "archive": []}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def load(self) -> List[dict]:
        return list(self._read()["agents"])

    def save(self, agent: dict) -> None:
        data = self._read()
        rec = {k: agent.get(k) for k in ("id", "name", "role", "room", "description", "look_seed")}
        data["agents"] = [a for a in data["agents"] if a.get("id") != rec["id"]] + [rec]
        self._write(data)

    def archive(self, agent_id: str) -> Optional[dict]:
        data = self._read()
        rec = next((a for a in data["agents"] if a.get("id") == agent_id), None)
        if rec is None:
            return None
        data["agents"] = [a for a in data["agents"] if a.get("id") != agent_id]
        cutoff = time.time() - ARCHIVE_DAYS * 86400
        data["archive"] = [a for a in data["archive"] if a.get("archived_at", 0) >= cutoff] + [dict(rec, archived_at=time.time())]
        self._write(data)
        return rec

    def archived(self) -> List[dict]:
        cutoff = time.time() - ARCHIVE_DAYS * 86400
        return [a for a in self._read()["archive"] if a.get("archived_at", 0) >= cutoff]

    def restore(self, agent_id: str) -> Optional[dict]:
        data = self._read()
        rec = next((a for a in data["archive"] if a.get("id") == agent_id), None)
        if rec is None:
            return None
        data["archive"] = [a for a in data["archive"] if a.get("id") != agent_id]
        rec = {k: v for k, v in rec.items() if k != "archived_at"}
        data["agents"].append(rec)
        self._write(data)
        return rec
