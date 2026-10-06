from pathlib import Path
import os
import shutil
import sys
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
BUNDLED_CONFIG_DIR = BASE_DIR / "config"

if getattr(sys, "frozen", False):
    CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet" / "config"
    if not CONFIG_DIR.exists():
        try:
            shutil.copytree(BUNDLED_CONFIG_DIR, CONFIG_DIR)
        except Exception:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
else:
    CONFIG_DIR = BUNDLED_CONFIG_DIR

# runtime state (memory, tasks, onboarding marker) lives next to the config:
# %APPDATA%\JarvisDesktopPet\data when frozen, <pkg>/data in development
DATA_DIR = CONFIG_DIR.parent / "data"


def load_yaml(p: Path) -> dict:
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config():
    return {
        "agents": load_yaml(CONFIG_DIR / "agents.yaml"),
        "config": load_yaml(CONFIG_DIR / "config.yaml"),
        "permissions": load_yaml(CONFIG_DIR / "permissions.yaml"),
        "skills": load_yaml(CONFIG_DIR / "skills.yaml"),
        "personality": load_yaml(CONFIG_DIR / "personality.yaml"),
    }


def save_yaml(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
