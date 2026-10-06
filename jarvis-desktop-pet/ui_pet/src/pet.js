const bubble = document.getElementById("bubble");
const bubbleText = document.getElementById("bubble-text");
const approval = document.getElementById("approval");
const approvalMsg = document.getElementById("approval-msg");
const approvalCountdown = document.getElementById("approval-countdown");
const petEl = document.getElementById("pet");
const petStage = document.getElementById("pet-stage");
const petHit = petStage || petEl;
let bubbleTimer = null;
let moodTimer = null;
let pendingApproval = null;
let approvalTick = null;

// ---- 2D/3D render switcher (doc 31, section 2) ----
const pet2dEl = document.getElementById("pet-2d");
const pet3dEl = document.getElementById("pet-3d");
const renderLabel = document.getElementById("dock-render-label");
let renderMode = "2d";
let lastSettings = null;

function applyRenderModeDom(mode) {
  if (pet2dEl) pet2dEl.style.display = mode === "2d" ? "" : "none";
  if (pet3dEl) pet3dEl.style.display = mode === "3d" ? "" : "none";
  if (renderLabel) renderLabel.textContent = mode.toUpperCase();
  document.body.dataset.renderMode = mode;
  if (mode === "3d" && window.Pet3D && typeof window.Pet3D.resize === "function") {
    try { window.Pet3D.resize(); } catch (e) {}
  }
}
function setRenderMode(mode, persist) {
  const m = mode === "3d" ? "3d" : "2d";
  renderMode = m;
  applyRenderModeDom(m);
  if (persist && lastSettings && lastSettings.config) {
    try {
      const p = JSON.parse(JSON.stringify(lastSettings));
      p.config.runtime = p.config.runtime || {};
      p.config.runtime.pet_render_mode = m;
      Jarvis.saveSettings(p);
    } catch (e) {}
  }
}
window.setRenderMode = setRenderMode;
applyRenderModeDom(renderMode); // HTML defaults match; set the state marker now

function setMood(m) {
  petEl.dataset.mood = m;
  if (window.Pet3D) window.Pet3D.setMood(m);
  if (window.Pet2D) window.Pet2D.setMood(m);
}
function moodTemp(m, ms) {
  setMood(m);
  clearTimeout(moodTimer);
  moodTimer = setTimeout(() => setMood("idle"), ms);
}
function showBubble(text, ms) {
  if (bubbleText) bubbleText.textContent = text;
  bubble.style.display = "block";
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => { bubble.style.display = "none"; }, ms || 5000);
}

function startApprovalCountdown(sec) {
  let left = Math.max(0, sec | 0);
  if (approvalCountdown) approvalCountdown.textContent = left + "s";
  clearInterval(approvalTick);
  approvalTick = setInterval(() => {
    left -= 1;
    if (approvalCountdown) approvalCountdown.textContent = Math.max(0, left) + "s";
    if (left <= 0) clearInterval(approvalTick);
  }, 1000);
}
function stopApprovalCountdown() {
  clearInterval(approvalTick);
  approvalTick = null;
}

function resetApprovalButtons() {
  const a = approval.querySelector(".btn-allow");
  const dn = approval.querySelector(".btn-deny");
  if (a) { a.disabled = false; a.textContent = "Allow once"; }
  if (dn) { dn.disabled = false; dn.textContent = "Deny"; }
}

function showApproval(data, cid) {
  pendingApproval = { payload: data.payload || data, cid: cid || data.correlation_id };
  const pp = pendingApproval.payload;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let html = esc(pp.message || "Approve?");
  if (pp.action && pp.action.target) html += '<div class="ac-target">Target: ' + esc(pp.action.target) + "</div>";
  html += ' <span class="risk">Risk level ' + (pp.risk == null ? "?" : pp.risk) + "/10</span>";
  if (approvalMsg) approvalMsg.innerHTML = html;
  resetApprovalButtons();
  approval.querySelectorAll(".hook-extra").forEach((b) => b.remove());
  if (pp.hook) {
    const row = approval.querySelector(".approval-actions");
    const al = document.createElement("button");
    al.className = "hook-extra btn-deny";
    al.textContent = "Always allow";
    al.onclick = () => {
      if (!pendingApproval) return;
      Jarvis.approval(true, { action: pp.action, remember: true }, pendingApproval.cid);
      settleApproval(al, "Allowing\u2026");
    };
    row.appendChild(al);
    if (pp.pid) {
      const tm = document.createElement("button");
      tm.className = "hook-extra btn-deny";
      tm.textContent = "Terminal";
      tm.onclick = () => Jarvis.hookTerminal(pp.pid);
      row.appendChild(tm);
    }
  }
  delete approval.dataset.pending;
  approval.style.display = "block";
  document.body.classList.add("approval-open");
  bubble.style.display = "none";
  startApprovalCountdown(pp.timeout || 30);
  setMood("approval");
  clearTimeout(moodTimer);
}

// selection is only a request; the card stays in a pending state until the
// backend reports the outcome (or the prompt expires)
function settleApproval(btn, label) {
  if (!pendingApproval) return;
  approval.dataset.pending = "1";
  approval.querySelectorAll(".btn-allow, .btn-deny, .hook-extra").forEach((b) => { b.disabled = true; });
  btn.textContent = label;
  stopApprovalCountdown();
  showBubble("Working\u2026", 8000);
  setMood("thinking");
  clearTimeout(moodTimer);
  setTimeout(() => {
    if (approval.dataset.pending === "1") {
      approval.style.display = "none";
      document.body.classList.remove("approval-open");
      delete approval.dataset.pending;
      pendingApproval = null;
      approval.querySelectorAll(".btn-allow, .btn-deny, .hook-extra").forEach((b) => { b.disabled = false; });
    }
  }, 90000);
}

const petAllowBtn = document.getElementById("pet-allow-btn");
const petDenyBtn = document.getElementById("pet-deny-btn");
if (petAllowBtn) petAllowBtn.onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(true, { action: pendingApproval.payload.action }, pendingApproval.cid);
    settleApproval(petAllowBtn, "Allowing\u2026");
  }
};
if (petDenyBtn) petDenyBtn.onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(false, { action: pendingApproval.payload.action }, pendingApproval.cid);
    settleApproval(petDenyBtn, "Denying\u2026");
  }
};

Jarvis.on("ui.pet_state", (d) => {
  if (d.payload && d.payload.text) showBubble(d.payload.text);
});
Jarvis.on("ui.chat", (d) => {
  if (!d.payload) return;
  // answered approval (here or in the main window): hide the card, the
  // message is the outcome
  if (d.correlation_id && pendingApproval &&
      String(pendingApproval.cid) === String(d.correlation_id)) {
    approval.style.display = "none";
    document.body.classList.remove("approval-open");
    delete approval.dataset.pending;
    pendingApproval = null;
    stopApprovalCountdown();
    resetApprovalButtons();
  }
  if (d.payload.role === "assistant" && d.payload.text) {
    showBubble(d.payload.text);
    if (petEl.dataset.mood !== "speaking") moodTemp("happy", 2200);
  }
  if (d.payload.role === "user") {
    setMood("thinking");
    clearTimeout(moodTimer);
  }
});
Jarvis.on("ui.approval", (d) => showApproval(d, d.correlation_id));
Jarvis.on("tool.result", (d) => {
  markActive();
  if (petEl.dataset.mood === "approval") return;
  const ok = !!(d.payload || {}).ok;
  playChime(ok);
  clearTimeout(moodTimer);
  setMood(ok ? "happy" : "concerned");
  moodTimer = setTimeout(() => setMood("idle"), ok ? 2200 : 3000);
});
// coding-agent sessions drive the Executing state (spec 29, section 5.5.5)
Jarvis.on("agent.hook.session", (d) => {
  markActive();
  const p = d.payload || {};
  const st = p.status || "update";
  if (st === "running") {
    clearTimeout(moodTimer);
    setMood("executing");
  } else if (st === "waiting") {
    clearTimeout(moodTimer);
    setMood("concerned");
  } else if (petEl.dataset.mood === "executing") {
    moodTemp("happy", 1800);
  }
});
Jarvis.on("ui.approval_cancelled", (d) => {
  if (pendingApproval && d.correlation_id && String(pendingApproval.cid) === String(d.correlation_id)) {
    approval.style.display = "none";
    document.body.classList.remove("approval-open");
    delete approval.dataset.pending;
    pendingApproval = null;
    stopApprovalCountdown();
    resetApprovalButtons();
    showBubble("Timed out \u2014 denied.", 3500);
  }
});

Jarvis.on("tts_state", (d) => {
  const speaking = !!(d.payload && d.payload.speaking);
  if (speaking) {
    clearTimeout(moodTimer);
    setMood("speaking");
  } else if (petEl.dataset.mood === "speaking") {
    moodTemp("happy", 1400);
  }
});

Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  if (st === "listening") {
    setMood("listening");
    clearTimeout(moodTimer);
    showBubble("Listening...", 6000);
  } else if (st === "transcribing") {
    setMood("thinking");
    clearTimeout(moodTimer);
  } else if (st === "wake" || st === "idle") {
    if (["listening", "thinking"].includes(petEl.dataset.mood)) setMood("idle");
  } else if (st === "error") {
    moodTemp("concerned", 4000);
    showBubble("Voice: " + ((d.payload || {}).error || "error"), 4000);
  }
});

document.addEventListener("jarvis:connected", () => {
  showBubble('Say "Hey Jarvis" or type a message.', 5000);
});
document.addEventListener("jarvis:disconnected", () => {
  showBubble("Reconnecting...", 3000);
});

function tcmd(name) {
  if (window.__TAURI__ && window.__TAURI__.tauri) window.__TAURI__.tauri.invoke(name);
}

let dragOrigin = null;
let dragMoved = false;
petHit.addEventListener("mousedown", (e) => {
  if (e.button !== 0) return;
  dragOrigin = { x: e.clientX, y: e.clientY };
  dragMoved = false;
});
document.addEventListener("mousemove", (e) => {
  if (!dragOrigin || dragMoved) return;
  const dx = e.clientX - dragOrigin.x;
  const dy = e.clientY - dragOrigin.y;
  if (dx * dx + dy * dy > 36) {
    dragMoved = true;
    dragOrigin = null;
    try {
      window.__TAURI__.window.getCurrent().startDragging();
    } catch (err) {}
  }
});
document.addEventListener("mouseup", () => { dragOrigin = null; });

// tactile squish earcon on poke (spec 29, section 5.4)
let petSoundMuted = false;
let petCtx = null;
function playSquish() {
  if (petSoundMuted) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!petCtx) petCtx = new AC();
    if (petCtx.state === "suspended") petCtx.resume().catch(() => {});
    const t = petCtx.currentTime;
    const o = petCtx.createOscillator();
    o.frequency.setValueAtTime(320, t);
    o.frequency.exponentialRampToValueAtTime(110, t + 0.14);
    const g = petCtx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.16, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
    o.connect(g);
    g.connect(petCtx.destination);
    o.start(t);
    o.stop(t + 0.2);
  } catch (e) {}
}
function playChime(ok) {
  if (petSoundMuted) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!petCtx) petCtx = new AC();
    if (petCtx.state === "suspended") petCtx.resume().catch(() => {});
    const t = petCtx.currentTime;
    const seq = ok ? [[660, 0], [880, 0.09], [1100, 0.18]] : [[330, 0], [220, 0.12]];
    seq.forEach(([f, at]) => {
      const o = petCtx.createOscillator();
      o.type = "sine";
      o.frequency.setValueAtTime(f, t + at);
      const g = petCtx.createGain();
      g.gain.setValueAtTime(0.0001, t + at);
      g.gain.exponentialRampToValueAtTime(0.12, t + at + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t + at + 0.14);
      o.connect(g);
      g.connect(petCtx.destination);
      o.start(t + at);
      o.stop(t + at + 0.17);
    });
  } catch (e) {}
}
function syncPetSound(d) {
  const payload = ((d || {}).payload) || {};
  lastSettings = payload;
  const cfg = payload.config || {};
  const v = cfg.voice || {};
  petSoundMuted = v.ui_sounds === false;
  // wardrobe/colorway (spec 29, section 5.5.7)
  const cw = (cfg.runtime || {}).pet_colorway || "porcelain";
  if (window.Pet3D && window.Pet3D.applyColorway) window.Pet3D.applyColorway(cw);
  // 2D/3D render mode (doc 31, section 2.1) - runtime.pet_render_mode
  setRenderMode((cfg.runtime || {}).pet_render_mode || "2d", false);
}
Jarvis.on("settings", syncPetSound);
Jarvis.on("settings_saved", syncPetSound);
// saves made in other windows only broadcast ui.state {settings_saved} -
// refetch so colorway / sound changes from the main window apply here too
Jarvis.on("ui.state", (d) => {
  if ((d.payload || {}).settings_saved) Jarvis.getSettings();
});
Jarvis.getSettings();

petHit.onclick = () => {
  if (dragMoved) { dragMoved = false; return; }
  playSquish();
  tcmd("open_chat");
};
const btnChat = document.getElementById("dock-btn-chat");
if (btnChat) btnChat.onclick = () => tcmd("open_chat");
const btnSettings = document.getElementById("dock-btn-settings");
if (btnSettings) btnSettings.onclick = () => tcmd("open_settings");
const btnDockmode = document.getElementById("dock-btn-dockmode");
if (btnDockmode) btnDockmode.onclick = () => {
  if (window.__TAURI__ && window.__TAURI__.tauri) window.__TAURI__.tauri.invoke("set_companion", { mode: "dock" });
};
// 1-click 2D/3D toggle (doc 31, section 2.3) - persists runtime.pet_render_mode
const btnRendermode = document.getElementById("dock-btn-rendermode");
if (btnRendermode) btnRendermode.onclick = () => setRenderMode(renderMode === "3d" ? "2d" : "3d", true);

// ---- file drag-and-drop ingestion (spec 29, sections 5.2 / 5.5.6) ----
function playGulp() {
  if (petSoundMuted) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!petCtx) petCtx = new AC();
    if (petCtx.state === "suspended") petCtx.resume().catch(() => {});
    const t = petCtx.currentTime;
    const o = petCtx.createOscillator();
    o.frequency.setValueAtTime(170, t);
    o.frequency.exponentialRampToValueAtTime(540, t + 0.1);
    o.frequency.exponentialRampToValueAtTime(240, t + 0.24);
    const g = petCtx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.18, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.26);
    o.connect(g);
    g.connect(petCtx.destination);
    o.start(t);
    o.stop(t + 0.3);
  } catch (e) {}
}

function ingestFiles(paths) {
  const list = (paths || []).filter(Boolean);
  if (!list.length) return;
  const name = String(list[0]).split(/[\\/]/).pop();
  showBubble("Inspecting " + name + (list.length > 1 ? ` (+${list.length - 1} more)` : "") + "...", 6000);
  clearTimeout(moodTimer);
  setMood("ingesting");
  if (window.Pet3D && window.Pet3D.ingestDrop) window.Pet3D.ingestDrop();
  playGulp();
  Jarvis.fileIngest(list);
  moodTimer = setTimeout(() => { setMood("idle"); }, 4500);
  markActive();
}

if (window.__TAURI__ && window.__TAURI__.event && window.__TAURI__.event.listen) {
  const tev = window.__TAURI__.event;
  tev.listen("tauri://file-drop-hover", (e) => {
    markActive();
    if (petEl.dataset.mood !== "ingesting") { clearTimeout(moodTimer); setMood("ingesting"); }
    if (window.Pet3D && window.Pet3D.ingestHover) {
      window.Pet3D.ingestHover((e && e.payload && e.payload.position) || null);
    }
  });
  tev.listen("tauri://file-drop-cancelled", () => {
    if (petEl.dataset.mood === "ingesting") { setMood("idle"); if (window.Pet3D && window.Pet3D.ingestEnd) window.Pet3D.ingestEnd(); }
  });
  tev.listen("tauri://file-drop", (e) => {
    ingestFiles((e && e.payload && e.payload.paths) || []);
  });

  // taffy stretch while the window is dragged, damped snap-back after
  // (spec 29, section 5.5.4 - drag velocity trailing)
  const petWin = window.__TAURI__.window && window.__TAURI__.window.getCurrent
    ? window.__TAURI__.window.getCurrent() : null;
  let lastWin = null;
  let stretchTimer = null;
  if (petWin && petWin.listen) {
    petWin.listen("tauri://move", (e) => {
      const p = e && e.payload;
      if (p && lastWin && window.Pet3D && window.Pet3D.stretch) {
        window.Pet3D.stretch(p.x - lastWin.x, p.y - lastWin.y);
        clearTimeout(stretchTimer);
        stretchTimer = setTimeout(() => {
          if (window.Pet3D && window.Pet3D.stretchEnd) window.Pet3D.stretchEnd();
          lastWin = null;
        }, 120);
      }
      if (p) lastWin = p;
    }).catch(() => {});
  }
}
// HTML5 fallback (plain webviews / CDP tests)
document.addEventListener("dragover", (e) => {
  e.preventDefault();
  markActive();
  if (petEl.dataset.mood !== "ingesting") { clearTimeout(moodTimer); setMood("ingesting"); }
  if (window.Pet3D && window.Pet3D.ingestHover) window.Pet3D.ingestHover([e.clientX, e.clientY]);
});
document.addEventListener("dragleave", (e) => {
  if (e.relatedTarget != null) return;
  if (petEl.dataset.mood === "ingesting") { setMood("idle"); if (window.Pet3D && window.Pet3D.ingestEnd) window.Pet3D.ingestEnd(); }
});
document.addEventListener("drop", (e) => {
  e.preventDefault();
  const dt = e.dataTransfer;
  const files = dt ? Array.from(dt.files || []) : [];
  let paths = files.map((f) => f.path || f.name).filter(Boolean);
  if (!paths.length && dt) {
    const txt = dt.getData("text/uri-list") || dt.getData("text/plain") || "";
    paths = txt.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  }
  ingestFiles(paths);
});

// ---- hover curiosity + rapid-poke dizzy + eco-sleep (spec 29, section 5.5.5) ----
let pokes = [];
let lastActivity = Date.now();
function markActive() {
  lastActivity = Date.now();
  if (petEl.dataset.mood === "sleep") { setMood("idle"); }
}
document.addEventListener("mousemove", markActive, { passive: true });
document.addEventListener("mousedown", markActive, { passive: true });

// hover curiosity: bound to both render layers (only the visible one fires)
[pet2dEl, pet3dEl].filter(Boolean).forEach((el) => {
  el.addEventListener("mouseenter", () => {
    markActive();
    if (petEl.dataset.mood === "idle") { clearTimeout(moodTimer); setMood("curious"); }
  });
  el.addEventListener("mouseleave", () => {
    if (petEl.dataset.mood === "curious") { clearTimeout(moodTimer); setMood("idle"); }
  });
});
// rapid clicking (>5 pokes in 1.5s -> dizzy)
const origClick = petHit.onclick;
petHit.onclick = (e) => {
  markActive();
  // poke impulse + volume-conserving squash (spec 29, section 5.5.4)
  if (window.Pet3D && window.Pet3D.poke && e) {
    const r = petHit.getBoundingClientRect();
    window.Pet3D.poke(
      ((e.clientX - r.left) / (r.width || 1)) * 2 - 1,
      -(((e.clientY - r.top) / (r.height || 1)) * 2 - 1)
    );
  }
  const now = Date.now();
  pokes.push(now);
  pokes = pokes.filter((t) => now - t <= 1500);
  if (pokes.length > 5) {
    pokes = [];
    clearTimeout(moodTimer);
    setMood("dizzy");
    showBubble("Whoa, easy there!", 2500);
    moodTimer = setTimeout(() => setMood("idle"), 2600);
    return;
  }
  if (petEl.dataset.mood === "idle") setMood("poked");
  origClick(e);
};
// eco-sleep after 5 minutes of inactivity in this window
setInterval(() => {
  if (petEl.dataset.mood === "sleep") return;
  if (Date.now() - lastActivity > 5 * 60 * 1000 && petEl.dataset.mood === "idle") {
    setMood("sleep");
  }
}, 15000);

const micBtn = document.getElementById("dock-btn-mic");
let micOn = false;
if (micBtn) micBtn.onclick = () => {
  micOn = !micOn;
  Jarvis.voiceListen(micOn);
};
Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  if (micBtn) {
    micBtn.classList.toggle("rec", st === "listening");
    micBtn.classList.toggle("busy", st === "transcribing");
  }
  micOn = st === "listening";
  document.body.classList.toggle("dock-show", st === "listening" || st === "transcribing");
});

setTimeout(() => showBubble("Hi, I'm Jarvis \u2014 need a hand?", 4000), 800);
