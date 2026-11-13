"""Mini World state: snapshot + diffs (doc 37, task 1.1).

Run: .venv/Scripts/python tests/world_state_test.py
exit 0 = pass
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.world.state import AgentInfo, TaskInfo, WorldState, apply_diff, empty_snapshot  # noqa: E402

results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(extra) if extra != "" else ""))


diffs = []
st = WorldState(on_change=diffs.append)
check("seq starts at 0", st.seq == 0)

st.add_agent(AgentInfo(id="pip", name="Pip", role="director", kind="default", room="f3r1c2"))
st.add_agent(AgentInfo(id="rhea", name="Rhea", role="researcher", kind="default", room="f2r1c1"))
st.open_job("j1", "compare laptops")
st.add_task(TaskInfo(id="t1", job_id="j1", role="researcher", goal="specs A", needs=[]))
st.add_task(TaskInfo(id="t2", job_id="j1", role="researcher", goal="specs B", needs=[]))
st.add_task(TaskInfo(id="t3", job_id="j1", role="writer", goal="table", needs=["t1", "t2"]))
st.update_agent("rhea", state="working", task_id="t1", label="reading")
st.update_task("t1", state="done", result="notes A")
st.remove_agent("rhea")
st.close_job("j1", "done", answer="saved")

check("10 mutations -> seq 10", st.seq == 10, st.seq)
check("diff seq strictly +1", [d["seq"] for d in diffs] == list(range(1, 11)), [d["seq"] for d in diffs])
check("diff topics are world.*", all(d["topic"].startswith("world.") for d in diffs))

try:
    st.update_agent("nobody", state="idle")
    check("update unknown agent raises KeyError", False)
except KeyError:
    check("update unknown agent raises KeyError", True)
check("failed update does not bump seq", st.seq == 10)

snap = empty_snapshot()
for d in diffs:
    snap = apply_diff(snap, d)
check("replayed diffs == snapshot()", snap == st.snapshot(), (snap, st.snapshot()))
check("snapshot seq matches", st.snapshot()["seq"] == st.seq)
check("job closed with answer", st.snapshot()["jobs"]["j1"]["status"] == "done" and st.snapshot()["jobs"]["j1"]["answer"] == "saved")
check("job lists its tasks", st.snapshot()["jobs"]["j1"]["task_ids"] == ["t1", "t2", "t3"])

before = copy.deepcopy(snap)
apply_diff(snap, diffs[0])
check("apply_diff is pure", snap == before)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
