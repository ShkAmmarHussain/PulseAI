import os
import shutil
from pathlib import Path


def _resolve(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser((p or "").strip().strip('"'))))


def delete_path(target: str) -> str:
    p = _resolve(target)
    if not str(p).strip():
        return "Failed: no path specified."
    if not p.exists():
        return f"Failed: '{p}' does not exist."
    if str(p).lower().rstrip("\\") in (str(Path(p.anchor)).lower().rstrip("\\"), "c:\\", "c:"):
        return "Failed: refusing to delete a drive root."
    if p.is_dir():
        shutil.rmtree(p)
        return f"Deleted folder {p} and its contents."
    p.unlink()
    return f"Deleted file {p}."


def list_dir(target: str = ".") -> str:
    p = _resolve(target)
    if not p.exists():
        return f"Failed: '{p}' does not exist."
    if p.is_file():
        return str(p)
    entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    lines = [f"{'[DIR] ' if e.is_dir() else ''}{e.name}" for e in entries[:40]]
    more = f"\n... and {len(entries) - 40} more" if len(entries) > 40 else ""
    return f"Contents of {p}:\n" + "\n".join(lines) + more


def move_file(src: str, dst: str) -> str:
    s, d = _resolve(src), _resolve(dst)
    if not s.exists():
        return f"Failed: '{s}' does not exist."
    if d.is_dir():
        d = d / s.name
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"Moved {s} -> {d}."


def create_file(path: str, content: str = "") -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created {p}."
