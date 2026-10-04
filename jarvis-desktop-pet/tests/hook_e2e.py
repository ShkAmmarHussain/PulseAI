"""jarvis-hook relay end-to-end (spec 29, sections 4 + 7.2).

Covers: the Rust named-pipe client (session/edit fire-and-forget, Claude Code
relay mapping, PreToolUse approval roundtrip - deny, allow-with-session-grant,
auto-grant clearing on new session), instant safe-command allow, spec 7.2
event shapes, and the one-click Claude/agy installers with backup + restore.

Run (backend on :8765, bin/jarvis-hook.exe built): .venv/Scripts/python tests/hook_e2e.py
exit 0 = pass
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
HOOK_EXE = ROOT / "bin" / "jarvis-hook.exe"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
AGY_HOOKS = Path.home() / ".gemini" / "config" / "hooks.json"
WS = "ws://127.0.0.1:8765/ws"

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def run_hook(args, stdin=None, timeout=15):
    t0 = time.time()
    p = subprocess.run(
        [str(HOOK_EXE)] + list(args),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=0x08000000,
    )
    return p, (time.time() - t0) * 1000.0


async def spawn_relay(payload, flavor="claude"):
    # asyncio's communicate(input=None) closes stdin with ZERO bytes, which
    # would make the relay see empty JSON and exit silently - feed it here.
    proc = await asyncio.create_subprocess_exec(
        str(HOOK_EXE), "relay", flavor,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    comm = asyncio.create_task(proc.communicate(json.dumps(payload).encode()))
    return proc, comm


class Client:
    def __init__(self, ws):
        self.ws = ws
        self.msgs = []

    async def send(self, obj):
        await self.ws.send_str(json.dumps(obj))

    async def wait_for(self, pred, seconds):
        end = time.time() + seconds
        while time.time() < end:
            for m in self.msgs:
                if pred(m):
                    return m
            try:
                m = await asyncio.wait_for(self.ws.receive(), timeout=max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                break
            if m.type != aiohttp.WSMsgType.TEXT:
                break
            self.msgs.append(json.loads(m.data))
        for m in self.msgs:
            if pred(m):
                return m
        return None


def is_tp(m, topic):
    return m.get("topic") == topic


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def claude_hook_events(data):
    hooks = (data or {}).get("hooks") or {}
    return sorted(k for k, v in hooks.items() if "jarvis-hook" in json.dumps(v))


def agy_hook_events(data):
    hooks = (data or {}).get("hooks") or {}
    return sorted(k for k, v in hooks.items() if "jarvis-hook" in json.dumps(v))


async def main():
    if not HOOK_EXE.exists():
        check("bin/jarvis-hook.exe exists", False, str(HOOK_EXE))
        print(f"== {sum(results)}/{len(results)} PASS ==")
        return 1

    claude_before = read_json(CLAUDE_SETTINGS)
    agy_before = read_json(AGY_HOOKS)

    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(WS, timeout=30) as ws:
                c = Client(ws)

                # --- relay state (spec 4.1) ---
                await c.send({"type": "hook_state"})
                r = await c.wait_for(lambda m: m.get("type") == "hook_state", 5)
                st = (r or {}).get("payload") or {}
                check("hook_state pipe + listening", st.get("pipe") == r"\\.\pipe\jarvis-hook"
                      and st.get("listening") is True, st)
                check("hook_state exe deployed", st.get("exe_exists") is True, st.get("exe"))

                # --- session fire-and-forget (never stalls the agent) ---
                p, ms = run_hook(["session", "claude-code", "HookTest", "running"])
                check("session exits 0 fast", p.returncode == 0 and ms < 1500, f"{ms:.0f}ms")
                r = await c.wait_for(lambda m: is_tp(m, "agent.hook.session")
                                     and (m.get("payload") or {}).get("status") == "running", 5)
                pl = (r or {}).get("payload") or {}
                check("agent.hook.session shape (spec 7.2)",
                      r is not None and pl.get("agent") == "claude-code"
                      and pl.get("project") == "HookTest" and int(pl.get("pid") or 0) > 0, pl)

                # --- edit subcommand -> diff event + live ticker (spec 4.2) ---
                p, ms = run_hook(["edit", "src/auth.ts", "14", "3", "@@ -10,5 +10,14 @@ ..."])
                check("edit exits 0 fast", p.returncode == 0 and ms < 1500, f"{ms:.0f}ms")
                r = await c.wait_for(lambda m: is_tp(m, "agent.hook.diff"), 5)
                pl = (r or {}).get("payload") or {}
                check("agent.hook.diff shape (spec 7.2)",
                      r is not None and pl.get("file") == "src/auth.ts"
                      and pl.get("added") == 14 and pl.get("removed") == 3
                      and "@@" in str(pl.get("patch")), pl)
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and str((m.get("payload") or {}).get("text", "")).startswith("Editing src/auth.ts"), 4)
                check("pet bubble / chat ticker line",
                      r is not None and "(+14 -3)" in (r.get("payload") or {}).get("text", ""),
                      (r or {}).get("payload"))

                # --- Claude Code relay mapping: PostToolUse Edit ---
                hook_in = {
                    "hook_event_name": "PostToolUse",
                    "tool_name": "Write",
                    "tool_input": {"file_path": r"C:\proj\main.rs", "content": "fn main() {}"},
                    "tool_response": {"structuredPatch": [
                        {"oldStart": 1, "oldLines": 1, "newStart": 1, "newLines": 3,
                         "lines": [" fn main() {}", "+    let x = 1;", "+    let y = 2;"]},
                    ]},
                    "cwd": r"C:\proj",
                }
                c.msgs.clear()
                p, ms = run_hook(["relay", "claude"], stdin=json.dumps(hook_in))
                check("relay PostToolUse exits 0", p.returncode == 0 and ms < 2000, f"{ms:.0f}ms")
                r = await c.wait_for(lambda m: is_tp(m, "agent.hook.diff"), 5)
                pl = (r or {}).get("payload") or {}
                check("relay computed diff from structuredPatch",
                      pl.get("file") == r"C:\proj\main.rs" and pl.get("added") == 2
                      and pl.get("removed") == 0, pl)

                # --- safe command: instant allow, no card ---
                await c.send({"type": "hook_state"})
                r0 = await c.wait_for(lambda m: m.get("type") == "hook_state", 5)
                auto0 = ((r0 or {}).get("payload") or {}).get("stats", {}).get("auto_allowed", 0)
                c.msgs.clear()
                safe_in = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                           "tool_input": {"command": "git status"}, "cwd": r"C:\proj"}
                p, ms = run_hook(["relay", "claude"], stdin=json.dumps(safe_in))
                out = json.loads(p.stdout.strip() or "{}")
                check("safe command auto-allowed < 1.5s",
                      p.returncode == 0 and ms < 1500
                      and out.get("hookSpecificOutput", {}).get("permissionDecision") == "allow",
                      f"{ms:.0f}ms {out}")
                card = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 1.2)
                check("safe command raised NO approval card", card is None, card)
                await c.send({"type": "hook_state"})
                r1 = await c.wait_for(lambda m: m.get("type") == "hook_state", 5)
                auto1 = ((r1 or {}).get("payload") or {}).get("stats", {}).get("auto_allowed", 0)
                check("auto_allowed stat incremented", auto1 > auto0, f"{auto0}->{auto1}")

                # --- risky command: DENY roundtrip (unique python pid per run) ---
                c.msgs.clear()
                risky = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                         "tool_input": {"command": "Remove-Item -Recurse -Force build_cache"},
                         "cwd": r"C:\proj"}
                proc, comm = await spawn_relay(risky)
                r = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 6)
                # note: client blocked in ReadFile until we answer
                pl = (r or {}).get("payload") or {}
                check("risky command raises approval card",
                      r is not None and pl.get("hook") is True and pl.get("risk") == 9
                      and "Remove-Item" in str(pl.get("command")), pl)
                check("approval has correlation_id", bool((r or {}).get("correlation_id")),
                      (r or {}).get("correlation_id"))
                r2 = await c.wait_for(lambda m: is_tp(m, "agent.hook.approval_request"), 3)
                check("spec 7.2 approval_request event", r2 is not None and
                      (r2.get("payload") or {}).get("agent") == "claude-code", (r2 or {}).get("payload"))
                await c.send({"type": "approval_response", "payload": {"allow": False},
                              "correlation_id": (r or {}).get("correlation_id")})
                out_b, _ = await asyncio.wait_for(comm, timeout=8)
                dec = json.loads((out_b or b"{}").decode(errors="replace") or "{}")
                check("deny relayed to agent as decision JSON",
                      dec.get("hookSpecificOutput", {}).get("permissionDecision") == "deny", dec)
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and "denied" in str((m.get("payload") or {}).get("text", "")), 4)
                check("denied outcome message", r is not None, (r or {}).get("payload"))

                # --- risky command: ALLOW + always-for-session ---
                c.msgs.clear()
                risky2 = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "npm run build --force-clean"},
                          "cwd": r"C:\proj"}
                proc, comm = await spawn_relay(risky2)
                r = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 6)
                check("second risky command raises card", r is not None, r)
                await c.send({"type": "approval_response", "payload": {"allow": True, "remember": True},
                              "correlation_id": (r or {}).get("correlation_id")})
                out_b, _ = await asyncio.wait_for(comm, timeout=8)
                dec = json.loads((out_b or b"{}").decode(errors="replace") or "{}")
                check("allow relayed as allow decision",
                      dec.get("hookSpecificOutput", {}).get("permissionDecision") == "allow", dec)
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and "allowed" in str((m.get("payload") or {}).get("text", "")), 4)
                check("allowed outcome message", r is not None, (r or {}).get("payload"))

                # --- session grant: next Bash command answers instantly, no card ---
                c.msgs.clear()
                t0 = time.time()
                p3, ms3 = run_hook(["relay", "claude"], stdin=json.dumps(risky2), timeout=10)
                out3 = json.loads(p3.stdout.strip() or "{}")
                check("session grant auto-allows without card",
                      ms3 < 1500 and out3.get("hookSpecificOutput", {}).get("permissionDecision") == "allow",
                      f"{ms3:.0f}ms {out3}")
                card = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 1.5)
                check("no second card while grant active", card is None, card)

                # --- fresh session clears the grant (spec 4.1 session scoping) ---
                p, ms = run_hook(["session", "claude-code", "HookTest", "running"])
                check("session refresh exits 0", p.returncode == 0 and ms < 1500, f"{ms:.0f}ms")
                await asyncio.sleep(0.5)
                c.msgs.clear()
                risky3 = dict(risky2)
                proc, comm = await spawn_relay(risky3)
                r = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 6)
                check("grant cleared on new session (card returns)", r is not None, r)
                if r is not None:
                    await c.send({"type": "approval_response", "payload": {"allow": False},
                                  "correlation_id": r.get("correlation_id")})
                    await asyncio.wait_for(comm, timeout=8)
                elif not proc.returncode:
                    proc.kill()

                # --- bogus terminal pid: ok:false, never raises ---
                c.msgs.clear()
                await c.send({"type": "hook_terminal", "payload": {"pid": 4194303}})
                r = await c.wait_for(lambda m: m.get("type") == "hook_terminal", 5)
                check("hook_terminal bogus pid -> ok false",
                      r is not None and (r.get("payload") or {}).get("ok") is False, (r or {}).get("payload"))

                # --- Claude Code one-click installer (spec 4.1) ---
                c.msgs.clear()
                await c.send({"type": "hook_install", "payload": {"target": "claude"}})
                r = await c.wait_for(lambda m: m.get("type") == "hook_install", 8)
                res = (r or {}).get("payload") or {}
                check("claude install ok", res.get("ok") is True, res)
                check("claude backup created", res.get("backup") and Path(res["backup"]).exists(), res.get("backup"))
                installed = read_json(CLAUDE_SETTINGS)
                evs = claude_hook_events(installed)
                check("settings.json hooks installed (5 events)",
                      evs == ["Notification", "PostToolUse", "PreToolUse", "SessionStart", "Stop"], evs)
                await c.send({"type": "hook_state"})
                r = await c.wait_for(lambda m: m.get("type") == "hook_state", 5)
                check("hook_state reports installed_claude",
                      ((r or {}).get("payload") or {}).get("installed_claude") is True)

                # --- uninstall restores the original file ---
                c.msgs.clear()
                await c.send({"type": "hook_uninstall", "payload": {"target": "claude"}})
                r = await c.wait_for(lambda m: m.get("type") == "hook_uninstall", 8)
                res = (r or {}).get("payload") or {}
                check("claude uninstall ok", res.get("ok") is True, res)
                restored = read_json(CLAUDE_SETTINGS)
                check("settings.json restored (parsed equal)",
                      restored == claude_before and "jarvis-hook" not in json.dumps(restored or {}),
                      "differs" if restored != claude_before else "clean")

                # --- agy installer roundtrip ---
                c.msgs.clear()
                await c.send({"type": "hook_install", "payload": {"target": "agy"}})
                r = await c.wait_for(lambda m: m.get("type") == "hook_install", 8)
                res = (r or {}).get("payload") or {}
                check("agy install ok", res.get("ok") is True, res)
                agy_installed = read_json(AGY_HOOKS)
                check("agy hooks registered",
                      agy_hook_events(agy_installed) == ["session_end", "session_start", "tool_call", "tool_result"],
                      agy_hook_events(agy_installed))
                c.msgs.clear()
                await c.send({"type": "hook_uninstall", "payload": {"target": "agy"}})
                r = await c.wait_for(lambda m: m.get("type") == "hook_uninstall", 8)
                check("agy uninstall ok", ((r or {}).get("payload") or {}).get("ok") is True)
                agy_restored = read_json(AGY_HOOKS)
                check("agy hooks restored (parsed equal)", agy_restored == agy_before
                      and "jarvis-hook" not in json.dumps(agy_restored or {}),
                      "differs" if agy_restored != agy_before else "clean")

                # --- final stats sanity ---
                c.msgs.clear()
                await c.send({"type": "hook_state"})
                r = await c.wait_for(lambda m: m.get("type") == "hook_state", 5)
                st = (r or {}).get("payload") or {}
                stats = st.get("stats") or {}
                check("hook stats accumulated", stats.get("events", 0) >= 6
                      and stats.get("approvals", 0) >= 3 and stats.get("denied", 0) >= 2, stats)
                check("pipe still listening after suite", st.get("listening") is True, st.get("listening"))
    finally:
        # never leave the user's Claude settings modified if a check exploded
        try:
            now = read_json(CLAUDE_SETTINGS)
            if now is not None and "jarvis-hook" in json.dumps(now) and claude_before is not None:
                with open(CLAUDE_SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(claude_before, f, indent=2, ensure_ascii=False)
            now = read_json(AGY_HOOKS)
            if now is not None and "jarvis-hook" in json.dumps(now):
                if agy_before is None:
                    AGY_HOOKS.unlink(missing_ok=True)
                else:
                    with open(AGY_HOOKS, "w", encoding="utf-8") as f:
                        json.dump(agy_before, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
