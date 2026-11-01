// Activity timeline (spec section 63, restyled per spec 34 section 4): a
// concise session log built from the events the backend already broadcasts.
// Each request becomes a task card (status dot + title) holding its steps;
// background events (connection, settings, models...) collect in "Session"
// cards. Low-level noise (mic levels, TTS ticks, wake test frames) is
// deliberately filtered out.
(function () {
  const list = document.getElementById("activity-list");
  if (!list) return;
  const clearBtn = document.getElementById("activity-clear");
  const MAX_CARDS = 60;
  let topDay = null;
  let task = null; // the request card still collecting steps

  const VERBS = {
    launch_app: "Opened", open_app: "Opened", close_app: "Closed",
    delete_file: "Deleted", move_file: "Moved", create_file: "Created",
    list_dir: "Listed files", open_url: "Opened in browser",
    web_search: "Searched the web", run_shell: "Ran a command",
    vision_describe: "Looked at your screen", type_text: "Typed text",
    vision_file: "Analyzed image file", summarize_file: "Summarized file",
    press_hotkey: "Pressed a shortcut", click: "Clicked", move_mouse: "Moved the mouse",
    respond: "Responded", noop: "Ran action",
  };
  const STATUS_LABEL = { run: "Working", warn: "Waiting for you", ok: "Done", bad: "Failed", muted: "" };

  function clip(s, n) {
    s = String(s == null ? "" : s).split("\n")[0].trim();
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  function makeEmpty() {
    const d = document.createElement("div");
    d.className = "act-empty";
    d.id = "activity-empty";
    d.innerHTML =
      '<div class="act-empty-orb orb" aria-hidden="true"><i class="core"></i></div>' +
      '<div class="act-empty-title">No activity yet</div>' +
      '<p class="act-empty-sub">Actions Jarvis takes &mdash; requests, approvals, completed work &mdash; will show up here as they happen.</p>';
    return d;
  }

  function dayLabel(ts) {
    const d = new Date(ts);
    const today = new Date();
    const y = new Date(today.getTime() - 86400000);
    if (d.toDateString() === today.toDateString()) return "Today";
    if (d.toDateString() === y.toDateString()) return "Yesterday";
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  function hhmm(ts) {
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch (err) {
      return "";
    }
  }

  function setStatus(card, st) {
    card.dataset.status = st;
    const lab = card.querySelector(".act-card-status");
    if (lab) lab.textContent = STATUS_LABEL[st] || "";
  }

  // newest card first; a day header precedes the first card of each day
  function newCard(kind, title, ts) {
    const empty = document.getElementById("activity-empty");
    if (empty) empty.remove();
    const key = new Date(ts).toDateString();
    if (key !== topDay) {
      const header = document.createElement("div");
      header.className = "act-day";
      header.dataset.day = key;
      header.textContent = dayLabel(ts);
      list.prepend(header);
      topDay = key;
    }
    const card = document.createElement("section");
    card.className = "act-card " + kind;
    const head = document.createElement("div");
    head.className = "act-card-head";
    head.innerHTML =
      '<span class="act-card-dot" aria-hidden="true"></span>' +
      '<span class="act-card-title"></span>' +
      '<span class="act-card-status"></span>' +
      '<span class="act-card-time"></span>';
    head.querySelector(".act-card-title").textContent = title;
    head.querySelector(".act-card-time").textContent = hhmm(ts);
    const steps = document.createElement("div");
    steps.className = "act-steps";
    card.appendChild(head);
    card.appendChild(steps);
    // days only move forward, so the newest header is always the first one
    list.querySelector(".act-day").after(card);
    const cards = list.querySelectorAll(".act-card");
    for (let i = MAX_CARDS; i < cards.length; i++) cards[i].remove();
    return card;
  }

  function addStep(card, e) {
    const ts = e.ts || Date.now();
    const item = document.createElement("div");
    item.className = "act-item" + (e.tone ? " " + e.tone : "");
    const time = document.createElement("span");
    time.className = "act-time";
    time.textContent = hhmm(ts);
    const track = document.createElement("span");
    track.className = "act-track";
    track.innerHTML = '<span class="act-dot"></span>';
    const body = document.createElement("div");
    body.className = "act-body";
    const label = document.createElement("div");
    label.className = "act-label";
    label.textContent = e.label;
    body.appendChild(label);
    if (e.detail) {
      const det = document.createElement("div");
      det.className = "act-detail";
      det.textContent = e.detail;
      body.appendChild(det);
    }
    if (e.node) body.appendChild(e.node);
    item.appendChild(time);
    item.appendChild(track);
    item.appendChild(body);
    card.querySelector(".act-steps").appendChild(item);
  }

  // background events go into the newest "Session" card, or start one
  function sessionStep(e) {
    let card = list.querySelector(".act-card");
    if (!card || !card.classList.contains("session") || card === task ||
        new Date(card.dataset.ts || 0).toDateString() !== new Date().toDateString()) {
      card = newCard("session", "Session", Date.now());
      card.dataset.ts = String(Date.now());
      setStatus(card, "muted");
    }
    addStep(card, e);
  }

  // request steps join the open task card; without one they start their own
  function taskStep(e, fallbackTitle) {
    if (!task) {
      task = newCard("task", fallbackTitle || e.label, Date.now());
      setStatus(task, "run");
    }
    addStep(task, e);
    return task;
  }
  function finishTask(st) {
    if (!task) return;
    if (task.dataset.status !== "bad") setStatus(task, st);
    task = null;
  }

  function stepNames(steps) {
    return (steps || [])
      .slice(0, 3)
      .map((s) => {
        // one wording source for every surface; no raw tool names (spec 34 section 7.2)
        if (window.ApprovalText && s) return window.ApprovalText.friendlyAction({ action: s }).title;
        const a = (s && s.action) || "";
        let v = VERBS[a] || a.replace(/[_-]+/g, " ");
        let t = (s && (s.target || s.path || s.url)) || "";
        if (t) {
          const parts = String(t).split(/[\\/]/);
          t = parts[parts.length - 1] || String(t);
          v += " " + clip(t, 40);
        }
        return v;
      })
      .join(" · ");
  }

  let prevModels = null;

  const TOPICS = {
    "ui.chat": (d) => {
      const p = d.payload || {};
      const text = clip(p.text, 180);
      if (!text) return;
      if (p.role === "user") {
        finishTask("ok");
        task = newCard("task", clip(p.text, 90), Date.now());
        setStatus(task, "run");
        addStep(task, { label: "You asked", detail: text, tone: "muted" });
      } else if (p.role === "assistant") {
        taskStep({ label: "Jarvis replied", detail: text }, "Jarvis replied");
        finishTask("ok");
      } else {
        sessionStep({ label: "Notice", detail: text, tone: "muted" });
      }
    },
    "ui.approval": (d) => {
      const p = d.payload || {};
      const AT = window.ApprovalText;
      const title = AT ? AT.friendlyAction(p).title : "An action";
      const risk = AT ? AT.riskBand(p.risk).label : "";
      const card = taskStep({ label: "Asked for your approval", detail: title + (risk ? " · " + risk : ""), tone: "warn" }, title);
      setStatus(card, "warn");
    },
    "ui.approval_cancelled": () => {
      const card = taskStep({ label: "Approval timed out", detail: "No answer was given, so the action was denied.", tone: "bad" }, "Approval timed out");
      setStatus(card, "bad");
      finishTask("bad");
    },
    "tool.result": (d) => {
      const p = d.payload || {};
      const names = stepNames(p.steps);
      const summary = clip(p.summary, 140);
      const detail = names ? names + (summary ? " — " + summary : "") : summary;
      const bad = p.ok === false;
      const card = taskStep({
        label: bad ? "Action failed" : "Action completed",
        detail: detail || "Done.",
        tone: bad ? "bad" : "ok",
      }, names || "Action");
      setStatus(card, bad ? "bad" : "run");
    },
    "ui.voice_state": (d) => {
      const p = d.payload || {};
      if (p.state === "wake") sessionStep({ label: "Wake word detected", detail: "Jarvis started listening.", tone: "ok" });
      else if (p.state === "error") sessionStep({ label: "Voice input error", detail: clip(p.error || "Unknown error", 160), tone: "bad" });
    },
    "rm_state": (d) => {
      const p = d.payload || {};
      if (!p || !Array.isArray(p.loaded)) return;
      const ids = p.loaded.map((m) => m.id).join(", ");
      const key = ids;
      if (prevModels === null) { prevModels = key; return; }
      if (key === prevModels) return;
      const grew = p.loaded.length > (prevModels ? prevModels.split(",").filter(Boolean).length : 0);
      prevModels = key;
      sessionStep({
        label: grew ? "Model loaded" : "Model unloaded",
        detail: ids || "All models released — memory free.",
        tone: grew ? "ok" : "muted",
      });
    },
    "ui.state": (d) => {
      if (d.payload && d.payload.settings_saved) {
        sessionStep({ label: "Settings saved", detail: "Your changes are now active.", tone: "muted" });
      }
    },
    "ui.pet_visibility": (d) => {
      const on = !d.payload || d.payload.enabled !== false;
      sessionStep({ label: on ? "Pet shown" : "Pet hidden", detail: on ? "Jarvis is on your desktop." : "Jarvis is only in this window.", tone: "muted" });
    },
    "agent.hook.session": (d) => {
      const p = d.payload || {};
      const st = p.status || "update";
      sessionStep({
        label: "Coding agent " + st,
        detail: (p.agent || "CLI agent") + (p.project ? " — " + p.project : ""),
        tone: st === "running" ? "ok" : st === "waiting" ? "warn" : "muted",
      });
    },
    "agent.hook.diff": (d) => {
      const p = d.payload || {};
      let node = null;
      if (p.patch) {
        const det = document.createElement("details");
        det.className = "act-diff";
        const sum = document.createElement("summary");
        sum.textContent = "Show diff";
        const pre = document.createElement("pre");
        pre.textContent = p.patch;
        det.appendChild(sum);
        det.appendChild(pre);
        node = det;
      }
      sessionStep({
        label: "Edited " + (p.file || "file"),
        detail: "(+" + (p.added || 0) + " -" + (p.removed || 0) + ")",
        tone: "muted",
        node: node,
      });
    },
  };

  Jarvis.on("*", (d) => {
    const fn = TOPICS[d.topic || d.type];
    if (fn) {
      try { fn(d); } catch (e) { /* never break the socket on a bad event */ }
    }
  });

  document.addEventListener("jarvis:connected", () => {
    sessionStep({ label: "Connected to local service", detail: "Jarvis is ready.", tone: "ok" });
  });
  document.addEventListener("jarvis:disconnected", () => {
    finishTask("bad");
    sessionStep({ label: "Connection lost", detail: "Trying to reconnect…", tone: "bad" });
  });

  if (clearBtn) {
    clearBtn.onclick = () => {
      list.innerHTML = "";
      list.appendChild(makeEmpty());
      task = null;
      topDay = null;
    };
  }

  // ---- active timers & reminders (spec 32, section 3.2) ----
  const timersWrap = document.getElementById("task-timers");
  const timersList = document.getElementById("task-timers-list");
  let activeTasks = [];

  function fmtLeft(sec) {
    if (sec <= 0) return "0s";
    if (sec < 60) return Math.ceil(sec) + "s";
    if (sec < 3600) return Math.floor(sec / 60) + "m " + Math.round(sec % 60) + "s";
    return Math.floor(sec / 3600) + "h " + Math.floor((sec % 3600) / 60) + "m";
  }

  function renderTimers() {
    if (!timersWrap || !timersList) return;
    const now = Date.now() / 1000;
    const chips = activeTasks.filter(
      (t) => t && t.status === "active" && t.type === "reminder" && Number(t.due_timestamp) > 0
    );
    timersWrap.hidden = chips.length === 0;
    timersList.innerHTML = "";
    chips.forEach((t) => {
      const chip = document.createElement("div");
      chip.className = "task-chip";
      chip.dataset.id = t.id || "";
      chip.dataset.due = String(t.due_timestamp || 0);
      const title = document.createElement("span");
      title.className = "task-chip-title";
      title.textContent = t.title || "Reminder";
      const left = document.createElement("span");
      left.className = "task-chip-left";
      const cancel = document.createElement("button");
      cancel.className = "task-chip-cancel";
      cancel.type = "button";
      cancel.textContent = "Cancel";
      chip.appendChild(title);
      chip.appendChild(left);
      chip.appendChild(cancel);
      timersList.appendChild(chip);
    });
    updateCountdowns();
  }

  function updateCountdowns() {
    if (!timersList || !timersWrap || timersWrap.hidden) return;
    const now = Date.now() / 1000;
    timersList.querySelectorAll(".task-chip").forEach((el) => {
      const leftEl = el.querySelector(".task-chip-left");
      if (!leftEl) return;
      const due = Number(el.dataset.due || 0);
      leftEl.textContent = fmtLeft(Math.max(0, due - now)) + " remaining";
    });
  }
  setInterval(updateCountdowns, 1000);

  if (timersList) {
    timersList.addEventListener("click", (e) => {
      const btn = e.target.closest(".task-chip-cancel");
      if (!btn) return;
      const chip = btn.closest(".task-chip");
      if (!chip || !chip.dataset.id) return;
      Jarvis.send({ type: "tasks.cancel", payload: { task_id: chip.dataset.id } });
    });
  }

  function takeTasks(d) {
    activeTasks = ((d && d.payload) || {}).tasks || [];
    renderTimers();
  }
  ["tasks.updated", "tasks.list", "tasks.create", "tasks.cancel"].forEach((t) => {
    Jarvis.on(t, takeTasks);
  });
  Jarvis.on("task.fired", () => {
    if (window.Earcons && typeof window.Earcons.play === "function") window.Earcons.play("snd_wake");
    renderTimers();
  });
  const requestTasks = () => Jarvis.send({ type: "tasks.list" });
  document.addEventListener("jarvis:connected", requestTasks);
  requestTasks();
})();
