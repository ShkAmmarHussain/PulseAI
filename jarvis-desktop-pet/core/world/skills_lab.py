"""Skills lab: draft, check, sandbox and store new skills (doc 36 §10).

A skill is a small Python module with ``def run(**params) -> str``. It is
drafted by the Builder's model, statically checked (imports and calls are
allow-listed; files and network need declared permissions), test-run in a
separate isolated Python process, and only ever runs after the user enables
it - and then always in that sandbox, never in the backend process.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

SAFE_MODULES = {
    "json", "math", "re", "datetime", "statistics", "collections", "itertools", "string", "textwrap",
    "random", "decimal", "fractions", "unicodedata", "html", "urllib.parse", "functools", "operator", "calendar",
}
FILE_MODULES = {"pathlib", "os.path", "csv", "glob", "shutil"}
NET_MODULES = {"urllib.request", "http.client", "requests", "httpx"}
BANNED_CALLS = {"exec", "eval", "compile", "__import__", "globals", "locals", "vars", "breakpoint", "input", "getattr", "setattr", "delattr"}
BANNED_MODULES = {"subprocess", "ctypes", "socket", "importlib", "sys", "builtins", "multiprocessing", "threading", "signal", "pickle", "marshal", "winreg", "os"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
PERMS = ("files", "network")


def risk_of(permissions: List[str]) -> int:
    p = set(permissions or [])
    if {"files", "network"} <= p:
        return 7
    if "files" in p:
        return 5
    if "network" in p:
        return 3
    return 1


def check_code(code: str, permissions: List[str]) -> List[str]:
    """Problems that stop a skill from being enabled. Empty list = passes."""
    perms = set(permissions or [])
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"syntax error on line {e.lineno}: {e.msg}"]
    errors: List[str] = []

    def module_ok(name: str) -> Optional[str]:
        top = name.split(".")[0]
        if name in SAFE_MODULES or top in {"json", "math", "re", "datetime", "statistics", "collections", "itertools", "string", "textwrap", "random", "decimal", "fractions", "unicodedata", "html", "functools", "operator", "calendar"}:
            return None
        if name in FILE_MODULES or top in {"pathlib", "csv", "glob", "shutil"} or name == "os.path":
            return None if "files" in perms else f"'{name}' needs the files permission"
        if name in NET_MODULES or top in {"requests", "httpx"} or name.startswith("urllib.request") or name.startswith("http."):
            return None if "network" in perms else f"'{name}' needs the network permission"
        if top in BANNED_MODULES:
            return f"'{name}' is not allowed in skills"
        return f"'{name}' is not on the allowed list"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                msg = module_ok(a.name)
                if msg:
                    errors.append(msg)
        elif isinstance(node, ast.ImportFrom):
            msg = module_ok(node.module or "")
            if node.module == "os" and all(a.name == "path" for a in node.names):
                msg = None if "files" in perms else "'os.path' needs the files permission"
            if msg:
                errors.append(msg)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
            if name in BANNED_CALLS:
                errors.append(f"'{name}()' is not allowed in skills")
            if name == "open" and isinstance(fn, ast.Name) and "files" not in perms:
                errors.append("'open()' needs the files permission")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr.endswith("__"):
            errors.append(f"'{node.attr}' is not allowed in skills")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "run" for n in tree.body):
        errors.append("the skill must define run(**params)")
    return sorted(set(errors))


RUNNER = r"""
import json, sys
src = open("skill.py", encoding="utf-8").read()
ns = {"__name__": "skill"}
exec(compile(src, "skill.py", "exec"), ns)
import inspect
params = json.loads(sys.stdin.read() or "{}")
sig = inspect.signature(ns["run"])
if not any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
    params = {k: v for k, v in params.items() if k in sig.parameters}  # drop extras the model added
out = ns["run"](**params)
sys.stdout.write("\n__RESULT__" + json.dumps({"result": str(out)[:8000]}))
"""


def run_sandboxed(code: str, params: dict, timeout_s: float = 10.0) -> str:
    """Run a skill in a separate isolated Python process in a throwaway folder."""
    with tempfile.TemporaryDirectory(prefix="pulseai-skill-") as tmp:
        Path(tmp, "skill.py").write_text(code, encoding="utf-8")
        Path(tmp, "runner.py").write_text(RUNNER, encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "PYTHONIOENCODING": "utf-8"}
        try:
            p = subprocess.run(
                [sys.executable, "-I", "runner.py"], cwd=tmp, input=json.dumps(params or {}), capture_output=True,
                text=True, timeout=timeout_s, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"skill timed out after {timeout_s:g}s")
        if "__RESULT__" in p.stdout:
            return json.loads(p.stdout.split("__RESULT__", 1)[1])["result"]
        err = (p.stderr or "").strip().splitlines()
        raise RuntimeError(err[-1] if err else f"skill exited with code {p.returncode}")


DRAFT_PROMPT = (
    "You write one small, safe Python skill for a desktop assistant.\n"
    "Reply with ONLY a JSON object: {\"name\": \"snake_case_name\", \"description\": \"one line\", "
    "\"params\": {\"param\": \"what it is\"}, \"permissions\": [], \"code\": \"...\", \"example\": {\"param\": \"value\"}}\n"
    "Rules: the code defines def run(...) -> str with one keyword argument per param and returns plain text; "
    "every argument may arrive as a string, so convert numbers inside run() with float() or int(); "
    "the example must use exactly the param names; use only the Python standard "
    "library (json, math, re, datetime, statistics, collections, textwrap, urllib.parse ...); add \"files\" to "
    "permissions only if it must read or write files, \"network\" only if it must fetch from the internet; "
    "no subprocess, eval, exec, os.system, sockets or imports outside that list."
)


class SkillStore:
    """data/world_skills/index.json + one folder per skill version."""

    def __init__(self, root: Optional[Path] = None):
        if root is None:
            from core.config import DATA_DIR

            root = DATA_DIR / "world_skills"
        self.root = Path(root)

    def _index(self) -> Dict[str, dict]:
        try:
            return json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_index(self, idx: Dict[str, dict]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "index.json").write_text(json.dumps(idx, indent=2), encoding="utf-8")

    def list(self) -> List[dict]:
        return sorted(self._index().values(), key=lambda s: s["name"])

    def get(self, name: str) -> Optional[dict]:
        return self._index().get(name)

    def code(self, name: str, version: Optional[int] = None) -> str:
        s = self.get(name)
        if not s:
            raise KeyError(name)
        return (self.root / name / f"v{version or s['version']}" / "skill.py").read_text(encoding="utf-8")

    def add_draft(self, spec: dict, errors: List[str], test_output: str) -> dict:
        idx = self._index()
        name = spec["name"]
        prev = idx.get(name)
        version = (prev["version"] + 1) if prev else 1
        folder = self.root / name / f"v{version}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "skill.py").write_text(spec["code"], encoding="utf-8")
        meta = {
            "name": name, "description": spec.get("description", ""), "params": spec.get("params") or {},
            "permissions": [p for p in spec.get("permissions") or [] if p in PERMS], "risk": risk_of(spec.get("permissions") or []),
            "example": spec.get("example") or {}, "version": version, "status": "draft",
            "check": errors, "test_output": test_output, "updated_at": time.time(),
        }
        (folder / "skill.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        idx[name] = meta
        self._save_index(idx)
        return meta

    def set_status(self, name: str, status: str) -> dict:
        idx = self._index()
        if name not in idx:
            raise KeyError(name)
        if status == "enabled" and idx[name].get("check"):
            raise ValueError("this skill did not pass the safety check, so it cannot be enabled")
        idx[name]["status"] = status
        self._save_index(idx)
        return idx[name]

    def delete(self, name: str) -> None:
        idx = self._index()
        if name not in idx:
            raise KeyError(name)
        archive = self.root / ".archive"
        archive.mkdir(parents=True, exist_ok=True)
        src = self.root / name
        if src.exists():
            src.rename(archive / f"{name}-{int(time.time())}")
        del idx[name]
        self._save_index(idx)

    def enabled(self) -> Dict[str, dict]:
        return {s["name"]: s for s in self._index().values() if s["status"] == "enabled"}
