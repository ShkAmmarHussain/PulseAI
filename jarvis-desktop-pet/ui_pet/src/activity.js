// Activity timeline (spec section 63) - a concise session log built from the
// events the backend already broadcasts. Low-level noise (mic levels, TTS
// ticks, wake test frames) is deliberately filtered out.
(function () {
  const list = document.getElementById("activity-list");
  if (!list) return;
  const clearBtn = document.getElementById("activity-clear");
  const MAX = 200;
  let count = 0;
  let topDay = null;

  const VERBS = {
    launch_app: "Opened", open_app: "Opened", close_app: "Closed",
    delete_file: "Deleted", move_file: "Moved", create_file: "Created",
    list_dir: "Listed files", open_url: "Opened in browser",
    web_search: "Searched the web", run_shell: "Ran a command",
    vision_describe: "Looked at your screen", type_text: "Typed text",
    respond: "Responded", noop: "Ran action",
  };

  function clip(s, n) {
    s = String(s == null ? "" : s).split("\n")[0].trim();
    return s.length > n ? s.slice(0, n - 1) + "\u2026" : s;
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

  function addEntry(e) {
    const empty = document.getElementById("activity-empty");
    if (empty) empty.remove();
    const ts = e.ts || Date.now();
    const key = new Date(ts).toDateString();
    let header = null;
    if (key !== topDay) {
      header = document.createElement("div");
      header.className = "act-day";
      header.dataset.day = key;
      header.textContent = dayLabel(ts);
      list.prepend(header);
      topDay = key;
    }

    const item = document.createElement("div");
    item.className = "act-item" + (e.tone ? " " + e.tone : "");
    const time = document.createElement("span");
    time.className = "act-time";
    try {
      time.textContent = new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    } catch (err) {
      time.textContent = "";
    }
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
    item.appendChild(time);
    item.appendChild(track);
    item.appendChild(body);

    const anchor = list.querySelector(".act-item");
    if (anchor) list.insertBefore(item, anchor);
    else list.appendChild(item);

    count++;
    while (count > MAX) {
      const last = list.querySelector(".act-item:last-of-type");
      if (!last) break;
      last.remove();
      count--;
    }
  }

  function stepNames(steps) {
    return (steps || [])
      .slice(0, 3)
      .map((s) => {
        const a = (s && s.action) || "";
        const v = VERBS[a] || a.replace(/[_-]+/g, " ");
        let t = (s && (s.target || s.path || s.url)) || "";
        if (t) {
          const parts = String(t).split(/[\\/]/);
          t = parts[parts.length - 1] || String(t);
          v += " " + clip(t, 40);
        }
        return v;
      })
      .join(" \u00b7 ");
  }

  let prevModels = null;

  const TOPICS = {
    "ui.chat": (d) => {
      const p = d.payload || {};
      const text = clip(p.text, 180);
      if (!text) return;
      if (p.role === "user") addEntry({ label: "You asked", detail: text, tone: "muted" });
      else if (p.role === "assistant") addEntry({ label: "Jarvis replied", detail: text });
      else addEntry({ label: "Notice", detail: text, tone: "muted" });
    },
    "ui.approval": (d) => {
      const p = d.payload || {};
      addEntry({ label: "Approval requested", detail: clip(p.message || "Jarvis needs your permission to continue.", 180), tone: "warn" });
    },
    "ui.approval_cancelled": () => {
      addEntry({ label: "Approval timed out", detail: "No answer was given, so the action was denied.", tone: "bad" });
    },
    "tool.result": (d) => {
      const p = d.payload || {};
      const names = stepNames(p.steps);
      const summary = clip(p.summary, 140);
      const detail = names ? names + (summary ? " \u2014 " + summary : "") : summary;
      addEntry({
        label: p.ok === false ? "Action failed" : "Action completed",
        detail: detail || "Done.",
        tone: p.ok === false ? "bad" : "ok",
      });
    },
    "ui.voice_state": (d) => {
      const p = d.payload || {};
      if (p.state === "wake") addEntry({ label: "Wake word detected", detail: "Jarvis started listening.", tone: "ok" });
      else if (p.state === "error") addEntry({ label: "Voice input error", detail: clip(p.error || "Unknown error", 160), tone: "bad" });
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
      addEntry({
        label: grew ? "Model loaded" : "Model unloaded",
        detail: ids || "All models released \u2014 memory free.",
        tone: grew ? "ok" : "muted",
      });
    },
    "ui.state": (d) => {
      if (d.payload && d.payload.settings_saved) {
        addEntry({ label: "Settings saved", detail: "Your changes are now active.", tone: "muted" });
      }
    },
    "ui.pet_visibility": (d) => {
      const on = !d.payload || d.payload.enabled !== false;
      addEntry({ label: on ? "Pet shown" : "Pet hidden", detail: on ? "Jarvis is on your desktop." : "Jarvis is only in this window.", tone: "muted" });
    },
  };

  Jarvis.on("*", (d) => {
    const fn = TOPICS[d.topic || d.type];
    if (fn) {
      try { fn(d); } catch (e) { /* never break the socket on a bad event */ }
    }
  });

  document.addEventListener("jarvis:connected", () => {
    addEntry({ label: "Connected to local service", detail: "Jarvis is ready.", tone: "ok" });
  });
  document.addEventListener("jarvis:disconnected", () => {
    addEntry({ label: "Connection lost", detail: "Trying to reconnect\u2026", tone: "bad" });
    topDay = null;
  });

  if (clearBtn) {
    clearBtn.onclick = () => {
      list.innerHTML = "";
      list.appendChild(makeEmpty());
      count = 0;
      topDay = null;
    };
  }
})();
