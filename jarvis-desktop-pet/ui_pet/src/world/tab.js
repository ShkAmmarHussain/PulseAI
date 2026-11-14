// World tab: glue between the backend (Jarvis WS), the store and the 3D scene
// (doc 37 task 4.4). Plain DOM; everything it shows comes from world.* events.
import { createStore } from "./store.js";
import { TEAM_LOOKS, genLook, portrait } from "./chibi.js";
import { roomGeom } from "./building.js";

const ROLE_SKILLS = {
  researcher: ["web_search", "summarize_file", "list_dir"],
  operator: ["launch_app", "close_app", "open_url", "create_file", "move_file", "delete_file", "list_dir", "run_shell", "type_text", "press_hotkey", "click", "move_mouse"],
  watcher: ["vision_describe", "vision_file"],
  archivist: ["memory.recall"],
};
const ROLE_LABEL = { director: "Director", thinker: "Planner", builder: "Builder", researcher: "Researcher", operator: "Operator", watcher: "Watcher", archivist: "Archivist", reporter: "Reporter" };
const TASK_STATE = { queued: "queued", working: "working", done: "done", failed: "failed", skipped: "skipped", stopped: "stopped" };

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const clip = (s, n) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");

const pane = document.getElementById("pane-world");
const store = createStore();
const looks = new Map();
const logs = new Map();
const busy = new Set();
let theme = "night";
try {
  theme = localStorage.getItem("pulseai.world.theme") === "day" ? "day" : "night";
} catch (e) {}
let scene = null, sceneFailed = false, selected = "pip", enabled = null, approval = null, fresh = false;

// a new agent's look comes from its look_seed, so it is the same on every
// screen and after a restart; Reroll just changes the seed
function lookFor(agent) {
  if (TEAM_LOOKS[agent.id]) return TEAM_LOOKS[agent.id];
  const seed = agent.look_seed || agent.id;
  const key = agent.id + "|" + seed;
  if (!looks.has(key)) {
    const taken = new Set([...looks.values(), ...Object.values(TEAM_LOOKS)].map((l) => JSON.stringify(l)));
    looks.set(key, genLook(seed, agent.role, taken));
  }
  return looks.get(key);
}
const face = (a) => portrait(a.id + ":" + JSON.stringify(lookFor(a)), lookFor(a), a.id === "pip");
const roleName = (a) => ROLE_LABEL[a.role] || cap(a.role);
function roomText(a) {
  const R = roomGeom(a.room);
  return R ? `${R.name} · F${R.f}` : "";
}
function taskOf(a) {
  return a && a.task_id ? store.state.tasks[a.task_id] : null;
}
const labelFor = (a) => clip((taskOf(a) && taskOf(a).goal) || a.label || "working", 26);

function log(id, text) {
  const d = new Date();
  const arr = logs.get(id) || [];
  arr.unshift({ t: `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`, text });
  logs.set(id, arr.slice(0, 6));
}

// which agent is waiting on the open approval card: the working agent whose
// task carries that action, else the only working agent
function approvalAgent() {
  if (!approval) return null;
  const working = Object.values(store.state.agents).filter((a) => a.state === "working");
  const act = approval.action && approval.action.action;
  const byStep = working.find((a) => {
    const t = taskOf(a);
    return t && t.params && (t.params.steps || []).some((s) => s.action === act);
  });
  return (byStep || working[0] || {}).id || null;
}

// ---------- rendering ----------
function render() {
  const st = store.state;
  const agents = Object.values(st.agents);
  if (scene) {
    scene.syncAgents(st.agents, { synced: st.synced, fresh, approvalAgent: approvalAgent(), labelFor });
    renderFloorButtons(scene.floorCount());
  }
  renderRoster(agents);
  renderInspector();
  renderJob();
}

function renderRoster(agents) {
  const team = agents.filter((a) => a.kind !== "temp"), temp = agents.filter((a) => a.kind === "temp");
  const ap = approvalAgent();
  const row = (a) => {
    const state = a.id === ap ? "approval" : a.state === "working" ? "work" : "";
    const sub = a.id === ap ? "Needs your approval" : a.state === "working" ? clip((taskOf(a) || {}).goal || "Working", 34) : `${roleName(a)} · ${roomText(a)}`;
    return `<button class="wt-row" data-id="${esc(a.id)}" aria-current="${a.id === selected}">
      <span class="wt-avatar"><img alt="" src="${face(a)}"></span>
      <span class="wt-row-text"><span class="wt-row-name">${esc(a.name)}</span><span class="wt-row-sub">${esc(sub)}</span></span>
      <span class="wt-dot ${state}" aria-hidden="true"></span></button>`;
  };
  $("#wt-roster", pane).innerHTML =
    `<div class="wt-group">Team</div>${team.map(row).join("")}` + (temp.length ? `<div class="wt-group">Temporary</div>${temp.map(row).join("")}` : "");
  $("#wt-count", pane).textContent = agents.length || "";
  pane.querySelectorAll(".wt-row").forEach((b) => (b.onclick = () => pick(b.dataset.id, true)));
}

function renderInspector() {
  const a = store.state.agents[selected];
  const box = $("#wt-insp", pane);
  if (!a) {
    box.innerHTML = '<p class="wt-muted">Select someone in the building.</p>';
    return;
  }
  const ap = approvalAgent() === a.id;
  const t = taskOf(a);
  const stateText = ap ? "Needs your approval" : a.state === "working" ? "Working" : "Idle";
  const chip = ap ? "approval" : a.state === "working" ? "work" : "idle";
  const kind = a.kind === "temp" ? '<span class="wt-badge temp">Temporary</span>' : a.kind === "custom" ? '<span class="wt-badge custom">Custom</span>' : '<span class="wt-badge">Default</span>';
  const skills = ROLE_SKILLS[a.role] || [];
  const lg = logs.get(a.id) || [];
  box.innerHTML = `
    <div class="wt-who"><div class="wt-portrait"><img alt="" src="${face(a)}"></div>
      <div><h2>${esc(a.name)}</h2><p>${esc(roleName(a))} · ${esc(roomText(a))}</p><div class="wt-badges">${kind}</div></div></div>
    <section class="wt-sec"><h3>Now</h3><div class="wt-now"><span class="wt-chip ${chip}">${stateText}</span>
      <p>${esc(t ? t.goal : a.id === "pip" ? "Routing requests to the team" : "Waiting for work")}</p></div></section>
    <section class="wt-sec"><h3>Activity</h3>${lg.length ? `<ol class="wt-log">${lg.map((l) => `<li><time>${l.t}</time><span>${esc(l.text)}</span></li>`).join("")}</ol>` : '<p class="wt-muted">Nothing yet this session.</p>'}</section>
    ${a.description ? `<section class="wt-sec"><h3>What it's for</h3><p class="wt-desc">${esc(a.description)}</p></section>` : ""}
    ${skills.length ? `<section class="wt-sec"><h3>Skills</h3><div class="wt-skills">${skills.map((s) => `<span class="wt-skill">${esc(s)}</span>`).join("")}</div></section>` : ""}
    <div class="wt-actions">
      <button class="wt-btn sm" type="button" id="wt-find"><svg class="ic"><use href="#i-search"/></svg>Find in building</button>
      ${a.kind !== "default" ? '<button class="wt-btn sm" type="button" id="wt-reroll">Reroll look</button>' : ""}
      ${a.kind === "custom" ? '<button class="wt-btn sm" type="button" id="wt-edit">Edit</button>' : ""}
      ${a.kind === "temp" ? '<button class="wt-btn sm" type="button" id="wt-keep">Keep as custom</button>' : ""}
      ${a.kind !== "default" ? `<button class="wt-btn sm danger" type="button" id="wt-del">${a.kind === "temp" ? "Dismiss" : "Delete"}</button>` : ""}
    </div>
    <form class="wt-edit" id="wt-edit-form" hidden>
      <label for="wt-edit-name">Name</label><input class="wt-field" id="wt-edit-name" maxlength="24" value="${esc(a.name)}" />
      <label for="wt-edit-desc">What it's for</label><textarea class="wt-field" id="wt-edit-desc" rows="3" maxlength="400">${esc(a.description || "")}</textarea>
      <div class="wt-form-btns"><button type="button" class="wt-btn sm" id="wt-edit-cancel">Cancel</button><button type="submit" class="wt-btn sm primary">Save</button></div>
    </form>
    <div class="wt-confirm" id="wt-confirm" hidden>
      <p>${a.kind === "temp" ? `Dismiss ${esc(a.name)}? Its current task stops.` : `Delete ${esc(a.name)}? You can bring them back from Recently deleted for 30 days.`}</p>
      <div class="wt-form-btns"><button type="button" class="wt-btn sm" id="wt-del-no">Keep</button><button type="button" class="wt-btn sm danger" id="wt-del-yes">${a.kind === "temp" ? "Dismiss" : "Delete"}</button></div>
    </div>`;
  const J = window.Jarvis;
  $("#wt-find", box).onclick = () => scene && scene.focus(a.id);
  const on = (id, fn) => {
    const el = $(id, box);
    if (el) el.onclick = fn;
  };
  on("#wt-reroll", () => J.world.agent({ op: "update", id: a.id, look_seed: a.id + ":" + Date.now().toString(36) }));
  on("#wt-keep", () => J.world.agent({ op: "keep", id: a.id }));
  on("#wt-edit", () => {
    $("#wt-edit-form", box).hidden = false;
    $("#wt-edit-name", box).focus();
  });
  on("#wt-edit-cancel", () => ($("#wt-edit-form", box).hidden = true));
  on("#wt-del", () => ($("#wt-confirm", box).hidden = false));
  on("#wt-del-no", () => ($("#wt-confirm", box).hidden = true));
  on("#wt-del-yes", () => J.world.agent({ op: "delete", id: a.id }));
  const form = $("#wt-edit-form", box);
  if (form)
    form.onsubmit = (e) => {
      e.preventDefault();
      J.world.agent({ op: "update", id: a.id, name: $("#wt-edit-name", box).value, description: $("#wt-edit-desc", box).value });
    };
}

// ---------- skills drawer (sprint 6) ----------
let skills = [], skillsOpen = false, openSkill = null, drafting = false;
const STATUS = { draft: "Draft", enabled: "On", disabled: "Off" };
function riskWord(r) {
  return r >= 6 ? "High risk" : r >= 4 ? "Medium risk" : "Low risk";
}
function renderSkills() {
  const list = $("#wt-sk-list", pane);
  $("#wt-sk-draft", pane).disabled = drafting;
  $("#wt-sk-draft", pane).textContent = drafting ? "Bodie is drafting…" : "Ask Bodie to draft it";
  if (!skills.length) {
    list.innerHTML = '<p class="wt-muted">No skills yet. Describe one above and Bodie will draft it for you to review.</p>';
    return;
  }
  list.innerHTML = skills
    .map((s) => {
      const open = openSkill === s.name;
      const bad = (s.check || []).length > 0;
      const acts =
        s.status === "enabled"
          ? `<button type="button" class="wt-btn sm" data-op="disable">Turn off</button><button type="button" class="wt-btn sm" data-op="test">Run example</button>`
          : `${bad ? "" : `<button type="button" class="wt-btn sm primary" data-op="enable">Turn on</button>`}<button type="button" class="wt-btn sm danger" data-op="delete">Delete</button>`;
      return `<article class="wt-skill-card${open ? " open" : ""}" data-name="${esc(s.name)}">
        <button type="button" class="wt-sk-top" aria-expanded="${open}">
          <span class="wt-sk-name">${esc(s.name)}</span>
          <span class="wt-badge ${s.status === "enabled" ? "on" : ""}">${STATUS[s.status] || s.status}</span>
          <span class="wt-badge">v${s.version}</span>
        </button>
        <p class="wt-sk-desc">${esc(s.description)}</p>
        ${open ? `<div class="wt-sk-body">
          <div class="wt-kv"><span>Can use</span><b>${s.permissions && s.permissions.length ? esc(s.permissions.join(", ")) : "nothing outside its own code"}</b></div>
          <div class="wt-kv"><span>Risk</span><b>${riskWord(s.risk)} (${s.risk}/10)</b></div>
          ${bad ? `<div class="wt-sk-problems"><b>Why it can't be turned on</b><ul>${s.check.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>` : `<div class="wt-kv"><span>Example result</span><b>${esc(s.test_output || "(empty)")}</b></div>`}
          <pre class="wt-code"><code>${esc(s.code)}</code></pre>
          <div class="wt-actions">${acts}</div>
        </div>` : ""}
      </article>`;
    })
    .join("");
  list.querySelectorAll(".wt-skill-card").forEach((card) => {
    const name = card.dataset.name;
    card.querySelector(".wt-sk-top").onclick = () => {
      openSkill = openSkill === name ? null : name;
      renderSkills();
    };
    card.querySelectorAll("[data-op]").forEach((b) => {
      b.onclick = () => {
        const op = b.dataset.op;
        const s = skills.find((x) => x.name === name) || {};
        window.Jarvis.world.skill(op === "test" ? { op, name, params: s.example || {} } : { op, name });
      };
    });
  });
}
function setSkillsOpen(on) {
  skillsOpen = on;
  $("#wt-skillpanel", pane).hidden = !on;
  $("#wt-insp", pane).hidden = on;
  $("#wt-skills-btn", pane).setAttribute("aria-pressed", String(on));
  if (on) {
    window.Jarvis.world.skill({ op: "list" });
    renderSkills();
  }
}

// roster footer: new agent form + recently deleted
function renderArchived(list) {
  const box = $("#wt-archived", pane);
  if (!list || !list.length) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  box.innerHTML =
    '<div class="wt-group">Recently deleted</div>' +
    list.map((r) => `<div class="wt-arch-row"><span>${esc(r.name)} <small>${esc(cap(r.role))}</small></span><button type="button" class="wt-btn sm" data-id="${esc(r.id)}">Bring back</button></div>`).join("");
  box.querySelectorAll("button").forEach((b) => (b.onclick = () => window.Jarvis.world.agent({ op: "restore", id: b.dataset.id })));
}

// floor buttons follow the building as it grows (All, then top floor down to 1)
let shownButtons = 0;
function renderFloorButtons(n) {
  if (n === shownButtons) return;
  shownButtons = n;
  const seg = $("#wt-floors", pane);
  const cur = (seg.querySelector('[aria-pressed="true"]') || {}).dataset;
  const pressed = cur ? cur.floor : "0";
  const nums = ["0"].concat(Array.from({ length: n }, (_, i) => String(n - i)));
  seg.innerHTML = nums.map((f) => `<button type="button" aria-pressed="${f === pressed}" data-floor="${f}">${f === "0" ? "All" : f}</button>`).join("");
  seg.querySelectorAll("button").forEach(
    (b) =>
      (b.onclick = () => {
        seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        scene && scene.setFloor(+b.dataset.floor);
      })
  );
}

function setTheme(t) {
  theme = t;
  try {
    localStorage.setItem("pulseai.world.theme", t);
  } catch (e) {}
  if (scene) scene.setTheme(t);
  const b = $("#wt-theme", pane);
  b.title = t === "day" ? "Switch to night" : "Switch to day";
  b.setAttribute("aria-label", t === "day" ? "Switch to night lighting" : "Switch to day lighting");
}

const sound = (n) => window.Earcons && window.Earcons.play(n);

function renderJob() {
  const jobs = Object.values(store.state.jobs);
  const job = jobs.filter((j) => j.status === "open").pop() || jobs[jobs.length - 1];
  const strip = $("#wt-job", pane);
  if (!job) {
    strip.hidden = true;
    return;
  }
  strip.hidden = false;
  const tasks = job.task_ids.map((id) => store.state.tasks[id]).filter(Boolean);
  const done = tasks.filter((t) => t.state === "done").length;
  $("#wt-job-title", pane).textContent = clip(job.text, 70);
  $("#wt-job-meta", pane).textContent =
    job.status === "open" ? (tasks.length ? `${done} of ${tasks.length} tasks done` : "Planning…") : cap(job.status === "partial" ? "finished with problems" : job.status);
  $("#wt-tasks", pane).innerHTML = tasks
    .map((t) => {
      const who = (store.state.agents[t.agent_id] || {}).name || cap(t.role);
      return `<li class="wt-task"><span class="wt-dot ${t.state === "working" ? "work" : t.state}"></span><b>${esc(clip(t.goal, 28))}</b><span>${esc(who)} · ${TASK_STATE[t.state] || t.state}</span></li>`;
    })
    .join("");
}

function renderApproval() {
  const card = $("#wt-approval", pane);
  if (!approval) {
    card.hidden = true;
    return;
  }
  const fa = window.ApprovalText ? window.ApprovalText.friendlyAction(approval) : { title: "Allow this action?" };
  const band = window.ApprovalText ? window.ApprovalText.riskBand(approval.risk) : { label: "" };
  const who = store.state.agents[approvalAgent()];
  const tgt = approval.action && (approval.action.cmd || approval.action.target || approval.action.path || approval.action.url || approval.action.text);
  card.hidden = false;
  $("#wt-ap-title", card).textContent = (who ? who.name + ": " : "") + fa.title;
  $("#wt-ap-sub", card).textContent = `${band.label || "Risk"} · risk ${approval.risk}/10`;
  const path = $("#wt-ap-path", card);
  path.hidden = !tgt;
  path.textContent = tgt || "";
  $("#wt-ap-avatar", card).innerHTML = who ? `<img alt="" src="${face(who)}">` : "";
}

function answer(allow) {
  if (!approval) return;
  window.Jarvis.approval(allow, {}, approval.cid);
  approval = null;
  renderApproval();
  render();
}

function pick(id, focus) {
  selected = id;
  if (skillsOpen) setSkillsOpen(false);
  if (scene) {
    scene.select(id);
    if (focus) scene.focus(id);
  }
  render();
}

let landed = false;
function setEnabled(on) {
  // the World tab is home when the Mini World is on (doc 36): land there once
  if (on && !landed && !location.hash && window.showTab) window.showTab("world");
  landed = true;
  enabled = on;
  $("#wt-off", pane).hidden = on !== false;
  $("#wt-body", pane).classList.toggle("is-off", on === false);
  if (on) window.Jarvis.world.snapshot();
}

// ---------- boot ----------
function ensureScene() {
  if (scene || sceneFailed) return;
  import("./scene.js")
    .then(({ createScene }) => {
      try {
        scene = createScene($("#wt-stage", pane), { lookFor, onPick: (id) => pick(id, false) });
        scene.select(selected);
        scene.setTheme(theme);
        scene.setActive(pane.classList.contains("active"));
        render();
      } catch (e) {
        fallback(e);
      }
    })
    .catch(fallback);
}
function fallback(e) {
  sceneFailed = true;
  console.warn("World 3D view unavailable", e);
  $("#wt-stage", pane).innerHTML = '<div class="wt-fallback"><b>3D view is not available on this device.</b><span>The list on the left still shows every agent and what it is doing.</span></div>';
}

function wire() {
  const J = window.Jarvis;
  const onWorld = (d) => {
    const r = store.apply(d);
    if (r === "gap") {
      J.world.snapshot();
      return;
    }
    if (r !== "ok") return;
    // agents already in a snapshot are placed at their desks; ones added
    // afterwards walk in through the lobby door
    if (d.topic === "world.snapshot") {
      fresh = false;
      render();
      fresh = true;
      return;
    }
    const p = d.payload || {};
    if (d.topic === "world.agent.updated" && p.agent) {
      if (p.agent.state === "working") {
        if (!busy.has(p.agent.id)) log(p.agent.id, clip((store.state.tasks[p.agent.task_id] || {}).goal || p.agent.label || "Working", 60));
        busy.add(p.agent.id);
      } else if (busy.delete(p.agent.id)) log(p.agent.id, "Finished");
    }
    if (d.topic === "world.agent.added" && p.agent && p.agent.kind !== "default") log(p.agent.id, p.agent.kind === "temp" ? "Arrived for a job" : "Joined the team");
    render();
  };
  ["world.snapshot", "world.agent.added", "world.agent.updated", "world.agent.removed", "world.job.opened", "world.job.closed", "world.task.created", "world.task.updated"].forEach((t) => J.on(t, onWorld));
  J.on("world.status", (d) => setEnabled(!!(d.payload || {}).enabled));
  J.on("world.archived", (d) => renderArchived((d.payload || {}).agents || []));
  J.on("world.skills", (d) => {
    skills = (d.payload || {}).skills || [];
    drafting = false;
    renderSkills();
  });
  J.on("world.skill.test", (d) => {
    const p = d.payload || {};
    const s = skills.find((x) => x.name === p.name);
    if (s) {
      s.test_output = p.output;
      renderSkills();
    }
  });
  $("#wt-skills-btn", pane).onclick = () => setSkillsOpen(!skillsOpen);
  $("#wt-sp-close", pane).onclick = () => setSkillsOpen(false);
  $("#wt-sk-form", pane).onsubmit = (e) => {
    e.preventDefault();
    const d = $("#wt-sk-desc", pane).value.trim();
    if (!d || drafting) return;
    drafting = true;
    J.world.skill({ op: "draft", description: d });
    $("#wt-sk-desc", pane).value = "";
    renderSkills();
  };
  // keep "Recently deleted" current after agents come and go
  ["world.agent.added", "world.agent.removed"].forEach((t) => J.on(t, () => J.world.agent({ op: "archived" })));
  J.on("ui.approval", (d) => {
    if (!String(d.correlation_id || "").startsWith("world-")) return;
    approval = Object.assign({ cid: d.correlation_id }, d.payload || {});
    renderApproval();
    render();
  });
  J.on("ui.approval_cancelled", (d) => {
    if (approval && approval.cid === d.correlation_id) {
      approval = null;
      renderApproval();
      render();
    }
  });
  document.addEventListener("jarvis:connected", () => {
    store.reset();
    J.world.status();
    J.world.snapshot();
    J.world.agent({ op: "archived" });
  });
  if (J.isConnected && J.isConnected()) {
    J.world.status();
    J.world.snapshot();
  }

  $("#wt-form", pane).onsubmit = (e) => {
    e.preventDefault();
    const inp = $("#wt-input", pane);
    const v = inp.value.trim();
    if (!v) return;
    J.world.say(v);
    inp.value = "";
  };
  $("#wt-stop", pane).onclick = () => J.world.stop();
  $("#wt-home", pane).onclick = () => scene && scene.home();
  $("#wt-theme", pane).onclick = () => setTheme(theme === "day" ? "night" : "day");
  setTheme(theme);
  // small sounds for the moments that matter (respects the app's sound setting)
  J.on("world.job.closed", (d) => {
    const st = (((d.payload || {}).job) || {}).status;
    sound(st === "done" ? "snd_success" : st === "stopped" ? "snd_listen_stop" : "snd_error");
  });
  J.on("world.agent.added", (d) => {
    if (fresh && (((d.payload || {}).agent) || {}).kind !== "default") sound("snd_dock_peek");
  });
  pane.querySelectorAll("#wt-floors button").forEach(
    (b) =>
      (b.onclick = () => {
        pane.querySelectorAll("#wt-floors button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        scene && scene.setFloor(+b.dataset.floor);
      })
  );
  $("#wt-allow", pane).onclick = () => answer(true);
  $("#wt-deny", pane).onclick = () => answer(false);
  $("#wt-enable", pane).onclick = () => J.world.set(true);
  const nf = $("#wt-new-form", pane), addBtn = $("#wt-add", pane);
  const closeNew = () => {
    nf.hidden = true;
    addBtn.hidden = false;
  };
  addBtn.onclick = () => {
    nf.hidden = false;
    addBtn.hidden = true;
    $("#wt-new-desc", pane).focus();
  };
  $("#wt-new-cancel", pane).onclick = closeNew;
  pane.querySelectorAll(".wt-preset").forEach((b) => (b.onclick = () => ($("#wt-new-desc", pane).value = b.dataset.text)));
  nf.onsubmit = (e) => {
    e.preventDefault();
    const d = $("#wt-new-desc", pane).value.trim();
    if (!d) {
      $("#wt-new-desc", pane).focus();
      return;
    }
    J.world.agent({ op: "create", description: d, name: $("#wt-new-name", pane).value.trim() });
    $("#wt-new-desc", pane).value = "";
    $("#wt-new-name", pane).value = "";
    closeNew();
  };
  pane.addEventListener("keydown", (e) => {
    if (!approval || e.target.closest("input")) return;
    if (e.key === "y" || e.key === "Y") answer(true);
    if (e.key === "n" || e.key === "N") answer(false);
  });
  // render only while the tab is visible
  new MutationObserver(() => {
    const on = pane.classList.contains("active");
    if (on) ensureScene();
    if (scene) scene.setActive(on);
  }).observe(pane, { attributes: true, attributeFilter: ["class"] });
  if (pane.classList.contains("active")) ensureScene();
}

if (pane && window.Jarvis) wire();
