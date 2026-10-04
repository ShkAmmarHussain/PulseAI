"""Zero-LLM fast-path intent router (spec 29, section 3.4 + 7.1).

Part A: pure rules (volume/media/power/timer/app + compound splitting +
fallback). Part B: end-to-end over the backend WS - real volume changes via
pycaw, real app launch, timer set/cancel, shutdown approval gate (deny only,
never approve), intent.fast_path events, rm_state stats.

Run (backend on :8765): .venv/Scripts/python tests/fast_router_test.py
exit 0 = pass
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fast_router import (  # noqa: E402
    FastRouter,
    load_apps,
    match_app,
    route,
    route_one,
    split_compound,
)

WS = "ws://127.0.0.1:8765/ws"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


# ---------------- Part A: pure rules ----------------


def unit_tests():
    v = route_one("volume up")
    check("volume up", v and v[0] == "media_volume" and v[1].get("op") == "up", v)
    v = route_one("turn the volume down")
    check("volume down", v and v[0] == "media_volume" and v[1].get("op") == "down", v)
    v = route_one("set volume to 42 percent")
    check("volume set 42%", v and v[1].get("op") == "set" and abs(v[1].get("level", 0) - 0.42) < 1e-6, v)
    v = route_one("volume 80")
    check("volume 80 (bare)", v and v[1].get("op") == "set" and abs(v[1].get("level", 0) - 0.8) < 1e-6, v)
    v = route_one("mute the volume")
    check("mute", v and v[1].get("op") == "mute", v)
    v = route_one("unmute")
    check("unmute alone falls back (needs volume word)", v is None, v)
    v = route_one("turn the volume back on")
    check("volume back on = unmute", v and v[1].get("op") == "unmute", v)
    v = route_one("maximum volume")
    check("max volume", v and v[1].get("op") == "set" and v[1].get("level") == 1.0, v)
    v = route_one("increase the volume")
    check("increase volume", v and v[1].get("op") == "up", v)

    v = route_one("pause spotify")
    check("pause spotify", v and v[0] == "media_control" and v[1].get("op") == "pause", v)
    v = route_one("play some music")
    check("play music", v and v[0] == "media_control" and v[1].get("op") == "play", v)
    v = route_one("skip this track")
    check("next track", v and v[1].get("op") == "next", v)
    v = route_one("go back to the previous song")
    check("previous song", v and v[1].get("op") == "prev", v)
    check("media without noun falls back", route_one("stop it") is None, route_one("stop it"))

    v = route_one("shut down the computer")
    check("shutdown", v and v[0] == "system_power" and v[1].get("action") == "shutdown", v)
    v = route_one("power off")
    check("power off", v and v[1].get("action") == "shutdown", v)
    v = route_one("lock the screen")
    check("lock screen", v and v[1].get("action") == "lock", v)
    v = route_one("put the pc to sleep")
    check("sleep", v and v[1].get("action") == "sleep", v)
    v = route_one("cancel the pending shutdown")
    check("cancel shutdown", v and v[1].get("action") == "cancel_shutdown", v)

    v = route_one("set a timer for 90 seconds")
    check("timer 90s", v and v[0] == "system_timer" and v[1].get("seconds") == 90, v)
    v = route_one("set a timer for 2 minutes")
    check("timer 2m", v and v[1].get("seconds") == 120, v)
    v = route_one("set an alarm for 3 hours")
    check("timer 3h", v and v[1].get("seconds") == 10800, v)
    v = route_one("timer for 30 seconds")
    check("timer 30s (no set)", v and v[1].get("seconds") == 30, v)
    v = route_one("cancel the timer")
    check("timer cancel", v and v[1].get("action") == "cancel", v)

    v = route_one("open notepad")
    check("open notepad", v and v[0] == "app_open" and v[1].get("cmd") == "notepad.exe", v)
    v = route_one("launch calculator")
    check("launch calculator", v and v[1].get("app") == "Calculator", v)
    v = route_one("open the notepad")
    check("open the notepad", v and v[1].get("app") == "Notepad", v)
    v = route_one("open notpad")
    check("fuzzy app >= 0.90", v and v[1].get("app") == "Notepad" and v[2] >= 0.90, v)

    check("confidence floor 0.90 on rules", route_one("volume up")[2] >= 0.90, route_one("volume up")[2])

    parts = split_compound("turn down volume and pause spotify")
    check("compound splits", len(parts) == 2 and parts[0] == "turn down volume", parts)
    r = route("turn down volume and pause spotify")
    check(
        "compound routes both parts",
        r and len(r) == 2 and r[0][0] == "media_volume" and r[1][0] == "media_control",
        r,
    )
    check("partial compound falls back entirely", route("open notepad and tell me a joke") is None)
    check("fallback: question", route("what is the capital of France") is None)
    check("fallback: chat", route("tell me a joke about penguins") is None)
    check("fallback: creation", route("write a poem about the sea") is None)
    check("fallback: open nonsense", route_one("open the quarterly financial report") is None)

    apps = load_apps()
    check("apps registry non-empty", isinstance(apps, list) and len(apps) >= 10, len(apps))
    hit = match_app("vs code")
    check("match_app alias exact", hit and hit[0] == "Visual Studio Code" and hit[2] == 1.0, hit)
    check("match_app miss", match_app("zzz-unknown-app-xyz") is None, match_app("zzz-unknown-app-xyz"))

    fr = FastRouter(_FakeBus(), {"config": {"fast_path": {"enabled": False}}})
    check("fast_path disable flag", fr.enabled is False, fr.enabled)
    fr.update_config({"config": {"fast_path": {"enabled": True}}})
    check("fast_path enable flag", fr.enabled is True)
    fr2 = FastRouter(_FakeBus(), {"permissions": {"approvals": {"timeout_ms": 45000}}})
    check("approval timeout from permissions cfg", fr2._approval_timeout_s() == 45.0, fr2._approval_timeout_s())


class _FakeBus:
    def subscribe(self, *a, **k):
        pass

    async def publish(self, *a, **k):
        pass


# ---------------- Part B: WS end-to-end ----------------


def volume_state():
    from core.fast_router import volume_state as vs

    return vs()


def apply_set(level, muted=False):
    from core.fast_router import apply_volume

    apply_volume({"op": "set", "level": level})
    apply_volume({"op": "unmute" if not muted else "mute"})


def shutdown_pending():
    try:
        p = subprocess.run(["shutdown", "/query"], capture_output=True, text=True, timeout=5, creationflags=0x08000000)
    except Exception:
        return False
    out = ((p.stdout or "") + (p.stderr or "")).lower()
    return "remaining" in out or "will start" in out


def notepad_pids():
    try:
        p = subprocess.run(["tasklist", "/FI", "IMAGENAME eq notepad.exe", "/FO", "CSV"],
                           capture_output=True, text=True, timeout=5, creationflags=0x08000000)
        return {line.split(",")[1].strip('"') for line in (p.stdout or "").splitlines()
                if line.lower().startswith('"notepad.exe"')}
    except Exception:
        return set()


def kill_pids(pids):
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5,
                           creationflags=0x08000000)
        except Exception:
            pass


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


def fp(family, **want):
    """Predicate for an intent.fast_path event of the given action/params."""
    def p(m):
        if not is_tp(m, "intent.fast_path"):
            return False
        pl = m.get("payload") or {}
        if pl.get("action") != family:
            return False
        params = pl.get("params") or {}
        return all(params.get(k) == v for k, v in want.items())
    return p


def asst(fragment):
    """Predicate for an assistant chat message containing a distinctive fragment."""
    def p(m):
        pl = m.get("payload") or {}
        return is_tp(m, "ui.chat") and pl.get("role") == "assistant" and fragment in str(pl.get("text") or "")
    return p


async def main():
    orig_vol, orig_mute = volume_state()
    pre_pids = notepad_pids()
    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(WS, timeout=30) as ws:
                c = Client(ws)

                # baseline stats (spec 7.1 / rm-status metric)
                await c.send({"type": "rm_state"})
                r = await c.wait_for(lambda m: m.get("type") == "rm_state", 5)
                fstats = (r or {}).get("payload", {}).get("fast_path") or {}
                check("rm_state carries fast_path stats", fstats.get("enabled") is True, fstats)
                base_hits = fstats.get("hits", 0)

                # --- volume up (pycaw real change) ---
                apply_set(0.40)
                time.sleep(0.2)
                before, _ = volume_state()
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "volume up"}})
                ev = await c.wait_for(lambda m: is_tp(m, "intent.fast_path"), 4)
                pl = (ev or {}).get("payload") or {}
                check("volume up -> intent.fast_path (spec 7.1)",
                      ev is not None and pl.get("action") == "media_volume"
                      and pl.get("bypassed_llm") is True and pl.get("latency_ms", 9999) < 250
                      and pl.get("params", {}).get("op") == "up", pl)
                time.sleep(0.4)
                after, _ = volume_state()
                check("volume actually raised ~10%", after >= before + 8, f"{before}->{after}")
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and (m.get("payload") or {}).get("role") == "assistant", 4)
                check("assistant reply with new level",
                      r is not None and "Volume" in (r.get("payload") or {}).get("text", ""),
                      (r or {}).get("payload"))
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and (m.get("payload") or {}).get("role") == "user", 4)
                check("user echo published",
                      r is not None and (r.get("payload") or {}).get("text") == "volume up",
                      (r or {}).get("payload"))

                # --- mute / unmute ---
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "mute the volume"}})
                r = await c.wait_for(fp("media_volume", op="mute"), 4)
                check("mute routes", r is not None, (r or {}).get("payload"))
                await c.wait_for(asst("Volume muted"), 4)
                time.sleep(0.3)
                _, muted = volume_state()
                check("system muted", muted is True)
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "unmute the volume"}})
                r = await c.wait_for(fp("media_volume", op="unmute"), 4)
                check("unmute routes", r is not None, (r or {}).get("payload"))
                await c.wait_for(asst("Volume unmuted"), 4)
                time.sleep(0.3)
                _, muted = volume_state()
                check("system unmuted", muted is False)

                # --- compound: two intents, zero LLM ---
                apply_set(0.40)
                time.sleep(0.2)
                before, _ = volume_state()
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "turn down volume and pause spotify"}})
                ev1 = await c.wait_for(fp("media_volume", op="down"), 4)
                ev2 = await c.wait_for(fp("media_control", op="pause"), 4)
                check("compound -> 2 fast_path events", ev1 is not None and ev2 is not None,
                      [(ev or {}).get("payload") for ev in (ev1, ev2)])
                time.sleep(0.4)
                after, _ = volume_state()
                check("compound lowered volume", after <= before - 8, f"{before}->{after}")
                r = await c.wait_for(asst("Paused"), 4)
                txt = (r or {}).get("payload", {}).get("text") or ""
                check("compound summary reply", "Volume" in txt and "Paused" in txt, txt)

                # --- app open ---
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "open notepad"}})
                r = await c.wait_for(asst("Opened Notepad"), 5)
                check("app open reply", r is not None, (r or {}).get("payload"))
                new_pids = set()
                for _ in range(20):
                    await asyncio.sleep(0.2)
                    new_pids = notepad_pids() - pre_pids
                    if new_pids:
                        break
                check("notepad launched", bool(new_pids), new_pids)

                # --- timer set + cancel (no chime) ---
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "set a timer for 500 seconds"}})
                ev = await c.wait_for(fp("system_timer", action="set"), 4)
                check("timer routes", ev is not None, (ev or {}).get("payload"))
                r = await c.wait_for(asst("Timer set"), 4)
                check("timer set reply", r is not None, (r or {}).get("payload"))
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "cancel the timer"}})
                r = await c.wait_for(asst("Cancelled"), 4)
                check("timer cancel reply", r is not None, (r or {}).get("payload"))

                # --- shutdown approval gate (deny path only) ---
                check("no shutdown scheduled before", shutdown_pending() is False)
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "shut down the computer"}})
                appr = await c.wait_for(lambda m: is_tp(m, "ui.approval"), 5)
                check("shutdown raises approval card (risk 9)", appr is not None
                      and (appr.get("payload") or {}).get("risk") == 9, (appr or {}).get("payload"))
                check("shutdown fast_path event", any(
                    is_tp(m, "intent.fast_path") and (m.get("payload") or {}).get("action") == "system_power"
                    for m in c.msgs))
                check("no shutdown scheduled while pending", shutdown_pending() is False)
                appr_cid = (appr or {}).get("correlation_id")
                check("approval has correlation_id", bool(appr_cid), appr_cid)
                await c.send({"type": "approval_response", "payload": {"allow": False},
                              "correlation_id": appr_cid})
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and "denied" in str((m.get("payload") or {}).get("text", "")).lower(), 5)
                check("deny reply", r is not None, (r or {}).get("payload"))
                await asyncio.sleep(0.5)
                check("deny left no shutdown scheduled", shutdown_pending() is False)

                # --- fallback to LLM pipeline ---
                c.msgs.clear()
                await c.send({"type": "text_input", "payload": {"text": "what is the capital of France"}})
                r = await c.wait_for(lambda m: is_tp(m, "ui.chat")
                                     and (m.get("payload") or {}).get("role") == "user", 3)
                check("fallback still reaches pipeline (user echo)",
                      r is not None and "capital" in (r.get("payload") or {}).get("text", ""),
                      (r or {}).get("payload"))
                ev = await c.wait_for(lambda m: is_tp(m, "intent.fast_path"), 1.5)
                check("fallback produced NO fast_path event", ev is None, ev)

                # --- rm_state stats accumulated (spec 3.4 rm-status metric) ---
                await c.send({"type": "rm_state"})
                r = await c.wait_for(
                    lambda m: m.get("type") == "rm_state"
                    and ((m.get("payload") or {}).get("fast_path") or {}).get("hits", 0) > base_hits, 5)
                fstats = (r or {}).get("payload", {}).get("fast_path") or {}
                check("fast_path hits counted", fstats.get("hits", 0) >= base_hits + 7, fstats)
                bya = fstats.get("by_action") or {}
                check("by_action breakdown",
                      all(bya.get(k, 0) >= 1 for k in ("media_volume", "media_control", "app_open",
                                                       "system_timer", "system_power")), bya)
                check("approval not left pending", fstats.get("approvals_pending") == 0, fstats)
    finally:
        # safety: never leave a shutdown scheduled, restore volume, clean up
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True, timeout=5, creationflags=0x08000000)
        except Exception:
            pass
        try:
            apply_set(orig_vol / 100.0, muted=orig_mute)
        except Exception:
            pass
        try:
            kill_pids(notepad_pids() - pre_pids)
        except Exception:
            pass

    print(f"== {sum(results)}/{len(results)} PASS ==")
    return 0 if all(results) else 1


if __name__ == "__main__":
    unit_tests()
    sys.exit(asyncio.run(main()))
