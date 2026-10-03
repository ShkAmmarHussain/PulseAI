# Registry helpers
from pathlib import Path
import json


def load_registry(path: Path):
    if not path.exists():
        return {"registered": [], "disabled": [], "versioning": True}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
