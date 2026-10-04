"""jarvis-hook named-pipe relay (spec 29, section 4 + 7.2).

Listens on \\\\.\\pipe\\jarvis-hook for newline-JSON messages from the
``bin/jarvis-hook.exe`` CLI client, republishes them on the event bus
(``agent.hook.session`` / ``agent.hook.diff``), and runs the terminal approval
gate: risky Bash commands raise the standard Approval Card; the answer is
relayed back over the pipe in real time. Safe commands and session-level
"always allow" grants are answered instantly without a card.

Also hosts the one-click hook installers for Claude Code
(``~/.claude/settings.json``, with backup) and Antigravity
(``~/.gemini/config/hooks.json``), plus the "Open Terminal" focus helper.
"""

import ctypes
import json
import logging
import os
import re
import shutil
import sys
import threading
import time
import uuid
from pathlib import Path

from core.bus import create_event

logger = logging.getLogger("hook_bridge")

PIPE_NAME = r"\\.\pipe\jarvis-hook"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
AGY_HOOKS = Path.home() / ".gemini" / "config" / "hooks.json"
APPROVAL_TIMEOUT_S = 30
ALWAYS_TTL_S = 8 * 3600

# ---- bash risk heuristic -------------------------------------------------

_DEADLY = re.compile(
    r"\b(rm|rmdir|rd|del|erase|format|mkfs|sudo|su|shutdown|reboot|stop-computer|restart-computer|"
    r"remove-item|remove-itemproperty|taskkill|diskpart|truncate|dd|reg\s+delete|reg\s+add|"
    r"git\s+push|git\s+reset|git\s+clean|git\s+checkout\s+--|curl|wget|Invoke-WebRequest|iwr|"
    r"Stop-Process|Out-File|set-executionpolicy)\b",
    re.IGNORECASE,
)
_READONLY = {
    "ls", "dir", "pwd", "cd", "echo", "cat", "type", "head", "tail", "wc", "whoami",
    "date", "hostname", "ver", "uname", "which", "where", "whereis", "man", "help",
    "file", "stat", "du", "df", "free", "ps", "tasklist", "systeminfo", "ipconfig",
    "ifconfig", "findstr", "select-string", "get-childitem", "get-content", "gci",
    "get-location", "gl", "tree", "whoami.exe", "hostname.exe", "git", "diff", "cmp",
}
_READONLY_GIT = {
    "status", "log", "diff", "branch", "show", "remote", "blame", "describe", "shortlog",
    "stash", "list", "help", "--version", "-v",
}


def bash_risk(cmd: str) -> int:
    t = " ".join((cmd or "").strip().split()).lower()
    if not t:
        return 1
    if _DEADLY.search(t):
        return 9
    parts = t.split()
    if parts[0] in _READONLY and not re.search(r"[;&|`$]", t):
        if parts[0] == "git":
            if len(parts) >= 2 and not parts[1].lstrip("-").split("=")[0] in {
                s.lstrip("-") for s in _READONLY_GIT
            }:
                return 4
        return 1
    return 4


# ---- installers ----------------------------------------------------------


def _source_exe() -> Path:
    # dev: <project>/bin/jarvis-hook.exe ; frozen: <exe dir>/bin (spec datas)
    return Path(__file__).resolve().parent.parent / "bin" / "jarvis-hook.exe"


def _ensure_exe() -> Path:
    dst = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Jarvis" / "bin" / "jarvis-hook.exe"
    src = _source_exe()
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and (not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime):
            shutil.copy2(src, dst)
    except Exception:
        logger.exception("hook exe install failed")
    return dst if dst.exists() else src


def _cmd_for(exe: Path, flavor: str) -> str:
    return f'"{exe}" relay {flavor}'


def _load_json(path: Path):
    if not path.exists():
        return {}, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), True
    except Exception:
        return None, True


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _has_hook(node, needle: str) -> bool:
    if isinstance(node, dict):
        cmd = node.get("command")
        if isinstance(cmd, str) and needle in cmd:
            return True
        return any(_has_hook(v, needle) for v in node.values())
    if isinstance(node, list):
        return any(_has_hook(v, needle) for v in node)
    return False


def _prune_hooks(node, needle: str):
    """Remove every hook object that invokes jarvis-hook; drop emptied parents."""
    if isinstance(node, dict):
        if isinstance(node.get("command"), str) and needle in node["command"]:
            return None
        out = {}
        for k, v in node.items():
            nv = _prune_hooks(v, needle)
            if nv is None:
                continue
            if isinstance(nv, dict) and "hooks" in nv and not nv.get("hooks"):
                continue
            if isinstance(nv, list) and not nv and k not in ("matcher",):
                continue
            out[k] = nv
        # a hook entry that lost all of its commands is dead weight
        # (matcher-only shells like {"matcher": "Bash"}) - drop it entirely
        if "hooks" in node and not out.get("hooks"):
            return None
        return out
    if isinstance(node, list):
        return [x for x in ( _prune_hooks(v, needle) for v in node) if x is not None]
    return node


def install_hook(target: str) -> dict:
    exe = _ensure_exe()
    if target == "claude":
        path = CLAUDE_SETTINGS
        cmd = _cmd_for(exe, "claude")
        data, exists = _load_json(path)
        if data is None:
            return {"ok": False, "error": "settings.json is not valid JSON - fix it first", "path": str(path)}
        backup = None
        if exists:
            bak = path.with_name(path.name + ".jarvis-backup")
            if not bak.exists():
                shutil.copy2(path, bak)
            backup = str(bak)
        hooks = data.setdefault("hooks", {})
        entry = lambda: [{"hooks": [{"type": "command", "command": cmd}]}]  # noqa: E731
        plan = {
            "PostToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": cmd}]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": cmd}]}],
            "SessionStart": entry(),
            "Stop": entry(),
            "Notification": entry(),
        }
        added = 0
        for event, entries in plan.items():
            bucket = hooks.setdefault(event, [])
            if _has_hook(bucket, "jarvis-hook"):
                continue
            bucket.extend(entries)
            added += 1
        _write_json(path, data)
        return {"ok": True, "path": str(path), "backup": backup, "added": added, "already": added == 0}
    elif target == "agy":
        path = AGY_HOOKS
        cmd = _cmd_for(exe, "agy")
        data, exists = _load_json(path)
        if data is None:
            return {"ok": False, "error": "hooks.json is not valid JSON - fix it first", "path": str(path)}
        backup = None
        if exists:
            bak = path.with_name(path.name + ".jarvis-backup")
            if not bak.exists():
                shutil.copy2(path, bak)
            backup = str(bak)
        hooks = data.setdefault("hooks", {})
        added = 0
        for event in ("tool_call", "tool_result", "session_start", "session_end"):
            bucket = hooks.setdefault(event, [])
            if _has_hook(bucket, "jarvis-hook"):
                continue
            bucket.append({"type": "command", "command": cmd})
            added += 1
        _write_json(path, data)
        return {"ok": True, "path": str(path), "backup": backup, "added": added, "already": added == 0}
    return {"ok": False, "error": "unknown target"}


def uninstall_hook(target: str) -> dict:
    path = CLAUDE_SETTINGS if target == "claude" else AGY_HOOKS if target == "agy" else None
    if path is None:
        return {"ok": False, "error": "unknown target"}
    data, exists = _load_json(path)
    if data is None:
        return {"ok": False, "error": "file is not valid JSON", "path": str(path)}
    if not exists:
        return {"ok": True, "path": str(path), "removed": 0, "absent": True}
    before = _has_hook(data, "jarvis-hook")
    hooks = data.get("hooks")
    if isinstance(hooks, dict):
        pruned = _prune_hooks(hooks, "jarvis-hook")
        empty = [k for k, v in pruned.items() if isinstance(v, list) and not v]
        for k in empty:
            del pruned[k]
        if pruned:
            data["hooks"] = pruned
        else:
            data.pop("hooks", None)
    removed = before and not _has_hook(data, "jarvis-hook")
    if data:
        _write_json(path, data)
    else:
        # hooks-only file (agy) - the pristine state was "absent"
        path.unlink(missing_ok=True)
    return {"ok": True, "path": str(path), "removed": int(removed)}


def hook_state() -> dict:
    exe = _ensure_exe()
    return {
        "pipe": PIPE_NAME,
        "exe": str(exe),
        "exe_exists": Path(exe).exists(),
        "installed_claude": _has_hook(_load_json(CLAUDE_SETTINGS)[0] or {}, "jarvis-hook"),
        "installed_agy": _has_hook(_load_json(AGY_HOOKS)[0] or {}, "jarvis-hook"),
    }


# ---- terminal focus ("Open Terminal") ------------------------------------

_user32 = ctypes.windll.user32
_user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
_user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
_user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
_user32.SetForegroundWindow.restype = ctypes.c_int
_user32.IsWindowVisible.argtypes = [ctypes.c_void_p]


def focus_pid(pid: int) -> bool:
    """Bring a window owned by pid to the foreground (spec 4.2 terminal jump)."""
    try:
        pid = int(pid)
    except Exception:
        return False
    if pid <= 0:
        return False
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _lparam):
        wpid = ctypes.c_ulong()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and _user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return 1

    _user32.EnumWindows(cb, 0)
    if not found:
        return False
    hwnd = found[0]
    fg = _user32.GetForegroundWindow()
    fg_tid = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
    my_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    _user32.AttachThreadInput(my_tid, fg_tid, True)
    _user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    ok = _user32.SetForegroundWindow(hwnd)
    _user32.AttachThreadInput(my_tid, fg_tid, False)
    return bool(ok) or _user32.GetForegroundWindow() == hwnd


# ---- the bridge ----------------------------------------------------------


class HookBridge:
    def __init__(self, bus):
        self.bus = bus
        self.loop = None
        self._pending = {}  # cid -> {"handle", "key", "expire_at"}
        self._always = {}  # "agent:pid:tool" -> ts
        self._write_lock = threading.Lock()
        self._stop = threading.Event()
        self.sessions = {}
        self.stats = {"events": 0, "approvals": 0, "auto_allowed": 0, "denied": 0}
        self._alive = False

    # -- lifecycle --

    def start(self, loop):
        self.loop = loop
        self.bus.subscribe("ui.approval.response", self._on_response)
        t = threading.Thread(target=self._serve, name="jarvis-hook-pipe", daemon=True)
        t.start()

    def stop(self):
        self._stop.set()

    @property
    def alive(self):
        return self._alive

    # -- bus: approval answers from the UI --

    async def _on_response(self, ev):
        import asyncio

        cid = ev.correlation_id
        entry = self._pending.pop(cid, None) if cid else None
        if entry is None:
            return
        payload = ev.payload or {}
        allow = bool(payload.get("allow"))
        if payload.get("remember") and allow and entry.get("key"):
            self._always[entry["key"]] = time.time()
        # write OFF the event loop, and only with the pipe thread parked
        # outside ReadFile (a pending server read blocks WriteFile - OS rule)
        await asyncio.to_thread(
            self._reply, cid, {"correlation_id": cid, "allow": allow, "remember": bool(payload.get("remember"))},
            entry["handle"],
        )
        ev2 = entry.get("event")
        if ev2 is not None:
            ev2.set()
        if not allow:
            self.stats["denied"] += 1
        await self.bus.publish(
            create_event(
                "ui.chat", "chat",
                {"role": "system", "text": "Terminal approval: " + ("allowed." if allow else "denied.")},
                correlation_id=cid,
            )
        )

    # -- pipe plumbing --

    def _reply(self, cid, obj, handle):
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with self._write_lock:
            try:
                import win32file

                win32file.WriteFile(handle, data)
                return True
            except Exception as e:
                logger.info("hook client gone (cid=%s): %r", cid, e)
                return False

    def _publish(self, topic, payload, cid=None):
        if self.loop is None:
            return
        import asyncio

        ev = create_event(topic, "hook", payload, correlation_id=cid)
        asyncio.run_coroutine_threadsafe(self.bus.publish(ev), self.loop)

    def _serve(self):
        import pywintypes
        import win32pipe

        while not self._stop.is_set():
            try:
                h = win32pipe.CreateNamedPipe(
                    PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    1, 65536, 65536, 0, None,
                )
            except pywintypes.error as e:
                if getattr(e, "winerror", None) == 231:  # ERROR_PIPE_BUSY
                    time.sleep(0.5)
                    continue
                logger.warning("CreateNamedPipe failed: %r", e)
                time.sleep(1.0)
                continue
            self._alive = True
            try:
                import win32file

                try:
                    win32pipe.ConnectNamedPipe(h, None)
                except pywintypes.error as e:
                    if getattr(e, "winerror", None) != 535:  # ERROR_PIPE_CONNECTED
                        win32file.CloseHandle(h)
                        continue
                self._client(h)
            finally:
                try:
                    import win32file

                    win32file.CloseHandle(h)
                except Exception:
                    pass

    def _client(self, h):
        import pywintypes
        import win32file

        try:
            while not self._stop.is_set():
                try:
                    _hr, data = win32file.ReadFile(h, 65536)
                except pywintypes.error:
                    break
                if not data:
                    break
                for line in data.decode("utf-8", "replace").split("\x00"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue
                    try:
                        waiting = self._handle(msg, h)
                    except Exception:
                        logger.exception("hook message failed")
                        waiting = None
                    if waiting is not None:
                        # approval awaiting a UI answer: park WITHOUT a pending
                        # ReadFile so the reply write can go through. Afterwards
                        # re-enter ReadFile: disconnecting before the client has
                        # read the reply would discard it (DisconnectNamedPipe
                        # drops unread data), and the client always closes once
                        # it has the answer.
                        waiting.wait(130)
                        continue
        finally:
            try:
                import win32pipe

                win32pipe.DisconnectNamedPipe(h)
            except Exception:
                pass

    # -- message handling --

    def _handle(self, msg, handle):
        topic = str(msg.get("topic") or "")
        payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
        cid = msg.get("correlation_id")
        self.stats["events"] += 1

        if topic == "agent.hook.approval_request":
            return self._approval(payload, cid, handle)

        if topic == "agent.hook.session":
            agent = str(payload.get("agent") or "cli-agent")
            self.sessions[agent] = dict(payload, ts=int(time.time() * 1000))
            # a fresh session start clears that agent's "always" grants
            if str(payload.get("status")) == "running":
                for k in [k for k in self._always if k.startswith(agent + ":")]:
                    self._always.pop(k, None)

        self._publish(topic, payload, cid)

        if topic == "agent.hook.diff":
            f = str(payload.get("file") or "file")
            added = int(payload.get("added") or 0)
            removed = int(payload.get("removed") or 0)
            # live ticker: bubble + chat + activity (spec 4.2)
            self._publish(
                "ui.chat",
                {"role": "system", "text": f"Editing {f} (+{added} -{removed})"},
                cid,
            )

    def _approval(self, payload, cid, handle):
        import asyncio

        agent = str(payload.get("agent") or "cli-agent")
        pid = int(payload.get("pid") or 0)
        tool = str(payload.get("tool") or "Bash")
        command = str(payload.get("command") or "")
        cid = cid or ("hook-" + uuid.uuid4().hex)
        key = f"{agent}:{pid}:{tool}"
        risk = bash_risk(command)
        timeout_s = min(120, max(5, int(payload.get("timeout_s") or APPROVAL_TIMEOUT_S)))

        # instant answers: session grant or safe command (no card, no stall)
        granted = self._always.get(key)
        auto = bool(granted and time.time() - granted < ALWAYS_TTL_S)
        if auto or risk <= 1:
            self.stats["auto_allowed"] += 1
            self._reply(cid, {"correlation_id": cid, "allow": True, "auto": True, "remember": bool(granted)}, handle)
            return None

        self.stats["approvals"] += 1
        ev = threading.Event()
        entry = {"handle": handle, "key": key, "expire_at": time.time() + timeout_s, "event": ev}
        self._pending[cid] = entry

        def expire():
            time.sleep(timeout_s)
            if self._pending.pop(cid, None) is None:
                return
            self._reply(cid, {"correlation_id": cid, "allow": False, "timeout": True}, handle)
            ev.set()
            self._publish("ui.approval_cancelled", {"reason": "timeout"}, cid)
            self._publish(
                "ui.chat",
                {"role": "system", "text": "Terminal approval timed out - treated as denied."},
                cid,
            )

        threading.Thread(target=expire, name=f"hook-timeout-{cid}", daemon=True).start()

        card = {
            "action": {"action": "terminal_command", "cmd": command[:46], "agent": agent, "tool": tool},
            "message": f"{agent} wants to run: {command[:160]}",
            "risk": risk,
            "hook": True,
            "agent": agent,
            "tool": tool,
            "command": command,
            "pid": pid,
        }
        self._publish("agent.hook.approval_request", dict(payload, risk=risk), cid)
        self._publish("ui.approval", card, cid)
        return ev
