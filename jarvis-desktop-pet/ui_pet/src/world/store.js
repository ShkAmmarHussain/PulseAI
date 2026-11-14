// Mini World state mirror (doc 36 §13, doc 37 task 4.2).
// world.snapshot replaces the state; world.* diffs apply in seq order with the
// same rules as core/world/state.py apply_diff. A seq jump means we missed
// something: apply() returns "gap" and the tab asks for a fresh snapshot.

const DIFF_TOPICS = new Set([
  "world.agent.added", "world.agent.updated", "world.agent.removed",
  "world.job.opened", "world.job.closed", "world.job.updated",
  "world.task.created", "world.task.updated",
]);

export function emptyState() {
  return { seq: 0, agents: {}, jobs: {}, tasks: {}, synced: false };
}

function clone(o) {
  return JSON.parse(JSON.stringify(o));
}

export function applyDiff(state, diff) {
  const t = diff.topic;
  if (t === "world.agent.added" || t === "world.agent.updated") state.agents[diff.agent.id] = clone(diff.agent);
  else if (t === "world.agent.removed") delete state.agents[diff.agent_id];
  else if (t === "world.job.opened" || t === "world.job.closed" || t === "world.job.updated") state.jobs[diff.job.id] = clone(diff.job);
  else if (t === "world.task.created" || t === "world.task.updated") {
    const task = clone(diff.task);
    state.tasks[task.id] = task;
    const job = state.jobs[task.job_id];
    if (t === "world.task.created" && job && job.task_ids.indexOf(task.id) < 0) job.task_ids.push(task.id);
  }
  state.seq = diff.seq;
  return state;
}

export function createStore() {
  let state = emptyState();
  const subs = [];
  const emit = (kind, detail) => subs.forEach((fn) => fn(kind, detail, state));
  return {
    get state() {
      return state;
    },
    on(fn) {
      subs.push(fn);
    },
    reset() {
      state = emptyState();
      emit("reset", null);
    },
    // msg = {topic, payload} as broadcast by ws_bridge
    apply(msg) {
      const topic = msg && msg.topic;
      const p = (msg && msg.payload) || {};
      if (topic === "world.snapshot") {
        state = Object.assign(emptyState(), clone(p), { synced: true });
        emit("snapshot", null);
        return "ok";
      }
      if (!DIFF_TOPICS.has(topic)) return "ignored";
      if (!state.synced) return "gap";
      if (typeof p.seq !== "number" || p.seq <= state.seq) return "ignored";
      if (p.seq !== state.seq + 1) {
        state.synced = false;
        return "gap";
      }
      applyDiff(state, p);
      emit(topic, p);
      return "ok";
    },
  };
}
