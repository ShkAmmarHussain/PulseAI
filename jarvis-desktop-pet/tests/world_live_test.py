"""Mini World against the real models (doc 37, task 2.4, live part).

Needs LM Studio on http://localhost:1234 (or a cloud provider configured).
Prints SKIP and exits 0 when no model is reachable.

Run: .venv/Scripts/python tests/world_live_test.py
exit 0 = pass (or skipped)
"""

import asyncio
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import load_config  # noqa: E402
from core.world.plan import validate_plan  # noqa: E402
from core.world.roles import ROLE_ACTIONS, WORKING_ROLES  # noqa: E402
from core.world.team import build_world, default_chat  # noqa: E402
from core.world.thinker import make_thinker  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra)[:300] if extra != "" else ""))


def reachable(cfg) -> bool:
    from core import llm

    if llm.get_provider(cfg) in ("openai", "anthropic"):
        return bool(llm.get_api_key(cfg, llm.get_provider(cfg)))
    base = (cfg.get("config", {}).get("lm_studio") or {}).get("base_url") or "http://localhost:1234/v1"
    req = urllib.request.Request(base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + (llm.get_api_key(cfg, "lm_studio") or "x")})
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("NOTE LM Studio is running but asks for an API token; set it in Settings > Models or turn off 'Require authentication' in LM Studio")
        return False
    except Exception:
        return False


async def main(cfg):
    async def no_execute(step):
        return f"(test) would run {step.get('action')}"

    async def deny(step, risk):
        return False

    w = build_world(cfg, None, execute=no_execute, approve=deny)
    job = await w.director.handle("what is 2+2")
    check("live: simple question answered", job.status == "done" and "4" in job.answer, job.answer)

    think = make_thinker(cfg, chat=default_chat(cfg), roles={r: ROLE_ACTIONS[r] for r in WORKING_ROLES})
    req = "Find the specs of the Lenovo X1 Carbon and the Dell XPS 14, write a comparison table and save it to my Documents folder"
    plan = await think(req)
    order, errs = validate_plan(plan, {"researcher", "operator", "watcher", "archivist"}, {"max_tasks": 8, "max_new_agents": 3})
    if errs:  # one retry, exactly like the Director
        plan = await think(req + "\n\nYour last plan was invalid: " + "; ".join(errs))
        order, errs = validate_plan(plan, {"researcher", "operator", "watcher", "archivist"}, {"max_tasks": 8, "max_new_agents": 3})
    check("live: complex request gives a valid plan", not errs and len(order) >= 2, errs or [t["role"] for t in order])


cfg = load_config()
if not reachable(cfg):
    print("SKIP no model reachable (start LM Studio to run the live checks)")
    sys.exit(0)
asyncio.run(main(cfg))
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
