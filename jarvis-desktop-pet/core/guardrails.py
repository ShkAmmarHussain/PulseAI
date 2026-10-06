from enum import Enum


class RiskLevel(Enum):
    AUTO = 0
    LOW = 1
    MEDIUM = 3
    HIGH = 6
    CRITICAL = 8


EXPLICIT_RISK = {
    "launch_app": 2,
    "open_url": 2,
    "open_app": 2,
    "close_app": 5,
    "web_search": 0,
    "list_dir": 0,
    "vision_describe": 0,
    "vision_file": 0,
    "summarize_file": 0,
    # input automation is always 7/10 (medium-high): approval card required
    # unless the permission policy is autonomous (spec 32, section 4)
    "type_text": 7,
    "press_hotkey": 7,
    "click": 7,
    "move_mouse": 7,
    "move_file": 4,
    "create_file": 4,
    "delete_file": 9,
    "run_shell": 8,
    "respond": 0,
}


def risk_score(action: str, params: dict) -> int:
    a = action.lower().strip()
    if a in EXPLICIT_RISK:
        return EXPLICIT_RISK[a]
    if any(k in a for k in ["read", "list", "search", "capture_read_only"]):
        return 0
    if any(k in a for k in ["launch", "open_app", "focus"]):
        return 2
    if any(k in a for k in ["type", "keyboard", "hotkey"]):
        return 6
    if any(k in a for k in ["click", "move_mouse", "input_control"]):
        return 7
    if any(k in a for k in ["write", "create", "move"]):
        return 4
    if any(k in a for k in ["delete", "remove", "overwrite", "rm", "del"]):
        return 9
    if any(k in a for k in ["shell", "run", "exec", "powershell", "cmd"]):
        return 8
    return 5
