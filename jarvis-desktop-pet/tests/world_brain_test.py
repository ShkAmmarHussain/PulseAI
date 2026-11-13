"""Mini World brain gateway: priorities, concurrency, cancel (doc 37, task 1.3).

Run: .venv/Scripts/python tests/world_brain_test.py
exit 0 = pass
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.world.brain import Brain  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


def job(log, name, dur=0.05, fail=False):
    async def fn():
        log.append(name)
        await asyncio.sleep(dur)
        if fail:
            raise RuntimeError("boom")
        return name
    return fn


async def main():
    # priority order with concurrency 1
    b = Brain(concurrency=1)
    log = []
    waits = []
    b.on_wait = lambda j, w: waits.append((j, w))
    first = asyncio.create_task(b.submit(job(log, "bg1"), job_id="a", priority=1))
    await asyncio.sleep(0.01)
    rest = [
        asyncio.create_task(b.submit(job(log, "bg2"), job_id="a", priority=1)),
        asyncio.create_task(b.submit(job(log, "bg3"), job_id="a", priority=1)),
        asyncio.create_task(b.submit(job(log, "inter"), job_id="b", priority=0)),
    ]
    await asyncio.sleep(0.01)
    check("waiting() counts queued only", b.waiting() == 3, b.waiting())
    check("waiting(job) filters", b.waiting("b") == 1, b.waiting("b"))
    out = await asyncio.gather(first, *rest)
    check("interactive jumps the queue", log == ["bg1", "inter", "bg2", "bg3"], log)
    check("results returned to the right caller", out == ["bg1", "bg2", "bg3", "inter"], out)
    check("on_wait fired for queued calls", ("b", True) in waits and ("b", False) in waits, waits)

    # concurrency 2
    b2 = Brain(concurrency=2)
    t0 = time.perf_counter()
    await asyncio.gather(b2.submit(job([], "x", .2), job_id="a"), b2.submit(job([], "y", .2), job_id="a"))
    dt = time.perf_counter() - t0
    check("concurrency 2 runs in parallel", dt < 0.35, round(dt, 3))

    # cancel one job, the other survives
    b3 = Brain(concurrency=1)
    log3 = []
    j1 = [asyncio.create_task(b3.submit(job(log3, f"j1-{i}", .2), job_id="j1")) for i in range(3)]
    await asyncio.sleep(0.01)
    j2 = asyncio.create_task(b3.submit(job(log3, "j2", .02), job_id="j2"))
    await asyncio.sleep(0.01)
    n = b3.cancel_job("j1")
    check("cancel_job counts running + queued", n == 3, n)
    res = await asyncio.gather(*j1, return_exceptions=True)
    check("cancelled submits raise CancelledError", all(isinstance(r, asyncio.CancelledError) for r in res), res)
    check("other job still completes", await j2 == "j2")
    check("cancelled queued calls never ran", log3 == ["j1-0", "j2"], log3)
    check("queue empty after", b3.waiting() == 0)

    # exceptions propagate and do not stall
    b4 = Brain(concurrency=1)
    try:
        await b4.submit(job([], "bad", .01, fail=True), job_id="a")
        check("exception propagates", False)
    except RuntimeError as e:
        check("exception propagates", str(e) == "boom")
    check("queue continues after error", await b4.submit(job([], "ok", .01), job_id="a") == "ok")

    # cancel_all
    b5 = Brain(concurrency=1)
    ts = [asyncio.create_task(b5.submit(job([], str(i), .2), job_id=f"j{i}")) for i in range(3)]
    await asyncio.sleep(0.01)
    check("cancel_all counts all", b5.cancel_all() == 3)
    res = await asyncio.gather(*ts, return_exceptions=True)
    check("cancel_all cancels all", all(isinstance(r, asyncio.CancelledError) for r in res))


asyncio.run(main())
print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
