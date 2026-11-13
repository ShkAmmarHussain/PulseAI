"""Who is who in the world: default team, allowed actions, model tiers (doc 36 §8)."""

from __future__ import annotations

from typing import Dict, List

# (id, name, role, room key in runtime.DEFAULT_ROOMS)
DEFAULT_TEAM = [
    ("pip", "Pip", "director", "director"),
    ("thinker", "Thinker", "thinker", "planning"),
    ("bodie", "Bodie", "builder", "workshop"),
    ("rhea", "Rhea", "researcher", "research"),
    ("otto", "Otto", "operator", "ops"),
    ("vee", "Vee", "watcher", "watch"),
    ("ada", "Ada", "archivist", "archive"),
    ("remy", "Remy", "reporter", "lobby"),
]

# actions each role may run (``respond`` is always allowed); temp roles get none
ROLE_ACTIONS: Dict[str, List[str]] = {
    "researcher": ["web_search", "summarize_file", "list_dir"],
    "operator": [
        "launch_app", "close_app", "open_url", "create_file", "move_file", "delete_file",
        "list_dir", "run_shell", "type_text", "press_hotkey", "click", "move_mouse",
    ],
    "watcher": ["vision_describe", "vision_file"],
    "archivist": [],
}

ROLE_FOR_ACTION: Dict[str, str] = {}
for _role, _acts in ROLE_ACTIONS.items():
    for _a in _acts:
        ROLE_FOR_ACTION.setdefault(_a, _role)

ROLE_TIER = {"thinker": "heavy", "researcher": "fast", "operator": "fast", "watcher": "vision", "archivist": "fast", "reporter": "fast"}
TEMP_TIER = "heavy"

# roles the Thinker may hand work to (the director, thinker, builder and reporter never take tasks)
WORKING_ROLES = ["researcher", "operator", "watcher", "archivist"]
