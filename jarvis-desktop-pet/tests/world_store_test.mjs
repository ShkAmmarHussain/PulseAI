// Mini World UI store (doc 37, task 4.2).
// Run: node tests/world_store_test.mjs   (exit 0 = pass)
// The diff script below matches tests/world_state_test.py, so both sides agree.
import { createStore, emptyState } from "../ui_pet/src/world/store.js";

const results = [];
function check(name, ok, extra) {
  results.push(!!ok);
  console.log((ok ? "PASS " : "FAIL ") + name + (extra !== undefined ? " | " + JSON.stringify(extra).slice(0, 300) : ""));
}

const A = (id, name, extra = {}) => Object.assign({ id, name, role: "r", kind: "default", room: "f1r1c1", state: "idle", task_id: null, label: "", job_id: null }, extra);
const T = (id, extra = {}) => Object.assign({ id, job_id: "j1", role: "researcher", goal: "g", needs: [], agent_id: null, state: "queued", result: "", error: "", params: {} }, extra);
let seq = 0;
const d = (topic, body) => ({ topic, payload: Object.assign({ topic, seq: ++seq }, body) });
const diffs = [
  d("world.agent.added", { agent: A("pip", "Pip") }),
  d("world.agent.added", { agent: A("rhea", "Rhea") }),
  d("world.job.opened", { job: { id: "j1", text: "x", status: "open", answer: "", task_ids: [] }, job_id: "j1" }),
  d("world.task.created", { task: T("t1"), job_id: "j1", task_id: "t1" }),
  d("world.task.created", { task: T("t2"), job_id: "j1", task_id: "t2" }),
  d("world.task.created", { task: T("t3", { needs: ["t1", "t2"] }), job_id: "j1", task_id: "t3" }),
  d("world.agent.updated", { agent: A("rhea", "Rhea", { state: "working", task_id: "t1", label: "reading" }) }),
  d("world.task.updated", { task: T("t1", { state: "done", result: "notes A" }), job_id: "j1", task_id: "t1" }),
  d("world.agent.removed", { agent_id: "rhea" }),
  d("world.job.closed", { job: { id: "j1", text: "x", status: "done", answer: "saved", task_ids: ["t1", "t2", "t3"] }, job_id: "j1" }),
];

// before a snapshot every diff is a gap
const s0 = createStore();
check("no snapshot yet -> gap", s0.apply(diffs[0]) === "gap");

const s = createStore();
const events = [];
s.on((kind) => events.push(kind));
check("empty snapshot ok", s.apply({ topic: "world.snapshot", payload: Object.assign(emptyState(), { seq: 0 }) }) === "ok");
const res = diffs.map((m) => s.apply(m));
check("all 10 diffs apply", res.every((r) => r === "ok"), res);
check("final seq 10", s.state.seq === 10);
check("agents", Object.keys(s.state.agents).join() === "pip");
check("job closed with answer", s.state.jobs.j1.status === "done" && s.state.jobs.j1.answer === "saved");
check("task ids recorded once", s.state.jobs.j1.task_ids.join() === "t1,t2,t3");
check("task result", s.state.tasks.t1.result === "notes A" && s.state.tasks.t2.state === "queued");
check("listeners called per diff", events.length === 11, events.length);
check("duplicate ignored", s.apply(diffs[3]) === "ignored" && s.state.seq === 10);
check("unrelated topic ignored", s.apply({ topic: "ui.chat", payload: {} }) === "ignored");

const g = createStore();
g.apply({ topic: "world.snapshot", payload: { seq: 0, agents: {}, jobs: {}, tasks: {} } });
g.apply(diffs[0]);
check("jump -> gap", g.apply(diffs[2]) === "gap");
check("after gap, wait for snapshot", g.apply(diffs[1]) === "gap");
g.apply({ topic: "world.snapshot", payload: { seq: 5, agents: { pip: A("pip", "Pip") }, jobs: {}, tasks: {} } });
check("resync then continue", g.apply(diffs[5]) === "ok" && g.state.seq === 6);

const snapCopy = createStore();
const payload = { seq: 3, agents: { pip: A("pip", "Pip") }, jobs: {}, tasks: {} };
snapCopy.apply({ topic: "world.snapshot", payload });
payload.agents.pip.name = "changed";
check("snapshot is copied, not shared", snapCopy.state.agents.pip.name === "Pip");

const ok = results.every(Boolean);
console.log(`\n${results.filter(Boolean).length}/${results.length} passed`);
process.exit(ok ? 0 : 1);
