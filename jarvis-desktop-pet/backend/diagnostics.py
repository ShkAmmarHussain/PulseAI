"""Diagnostics bundle (spec 34 section 7.5): one zip a user can attach to a bug report.

Contents: backend log (+ its rotated copy), every settings YAML with secrets
redacted, the resource manager snapshot, and version/platform facts. API keys
never appear: values under any key/token/secret/password field are replaced.
"""

import datetime
import io
import json
import os
import platform
import re
import sys
import zipfile
from pathlib import Path

import yaml

from core.config import CONFIG_DIR

SECRET_FIELD = re.compile(r"(api_?key|token|secret|password|passwd|auth)", re.I)
REDACTED = "<redacted>"
YAMLS = ("config.yaml", "agents.yaml", "permissions.yaml", "personality.yaml", "skills.yaml")
KEY_PATTERN = re.compile(r"\b(sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{12,})")


def log_dir() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home()))) / "JarvisDesktopPet"


def out_dir() -> Path:
    return log_dir() / "diagnostics"


def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if SECRET_FIELD.search(str(k)) and isinstance(v, str) and v:
                out[k] = REDACTED
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def scrub_text(text: str) -> str:
    """Belt and braces for logs: mask anything shaped like a cloud API key."""
    return KEY_PATTERN.sub(lambda m: m.group(1)[:6] + "…" + REDACTED, text)


def export_bundle(app_version: str, rm_state: dict) -> str:
    out = out_dir()
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out / f"pulseai-diagnostics-{stamp}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        info = {
            "app_version": app_version,
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0],
            "frozen": bool(getattr(sys, "frozen", False)),
            "platform": platform.platform(),
            "machine": platform.machine(),
        }
        z.writestr("about.json", json.dumps(info, indent=2))
        z.writestr("rm_state.json", json.dumps(rm_state, indent=2, default=str))
        for name in YAMLS:
            p = CONFIG_DIR / name
            if not p.exists():
                continue
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                buf = io.StringIO()
                yaml.safe_dump(redact(data), buf, sort_keys=False, allow_unicode=True)
                z.writestr("config/" + name, buf.getvalue())
            except Exception as e:
                z.writestr("config/" + name + ".error.txt", str(e))
        for name in ("backend.log", "backend.log.1"):
            p = log_dir() / name
            if p.exists():
                z.writestr("logs/" + name, scrub_text(p.read_text(encoding="utf-8", errors="replace")))
    return str(path)


def reveal(path: str) -> bool:
    """Open Explorer on a bundle this module wrote (and nothing else)."""
    try:
        p = Path(path).resolve()
        if p.parent != out_dir().resolve() or not p.exists():
            return False
        if os.name == "nt":
            import subprocess

            subprocess.Popen(["explorer", "/select,", str(p)])
            return True
    except Exception:
        return False
    return False
