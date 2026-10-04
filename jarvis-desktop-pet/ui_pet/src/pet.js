const bubble = document.getElementById("bubble");
const approval = document.getElementById("approval");
const petEl = document.getElementById("pet");
let bubbleTimer = null;
let moodTimer = null;
let pendingApproval = null;

const statusEl = document.getElementById("pet-status");
const statusText = document.getElementById("pet-status-text");
function setStatus(text, mode) {
  if (statusText) statusText.textContent = text;
  if (statusEl) {
    statusEl.classList.toggle("active", mode === "active");
    statusEl.classList.toggle("off", mode === "off");
  }
}

function setMood(m) {
  petEl.dataset.mood = m;
  if (window.Pet3D) window.Pet3D.setMood(m);
}
function moodTemp(m, ms) {
  setMood(m);
  clearTimeout(moodTimer);
  moodTimer = setTimeout(() => setMood("idle"), ms);
}
function showBubble(text, ms) {
  bubble.textContent = text;
  bubble.style.display = "block";
  clearTimeout(bubbleTimer);
  bubbleTimer = setTimeout(() => { bubble.style.display = "none"; }, ms || 5000);
}

function showApproval(data, cid) {
  pendingApproval = { payload: data.payload || data, cid: cid || data.correlation_id };
  const pp = pendingApproval.payload;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let html = esc(pp.message || "Approve?");
  if (pp.action && pp.action.target) html += '<div class="ac-target">Target: ' + esc(pp.action.target) + "</div>";
  approval.querySelector(".msg").innerHTML =
    html + ' <span class="risk">Risk level ' + (pp.risk == null ? "?" : pp.risk) + "/10</span>";
  const a = approval.querySelector(".allow");
  const dn = approval.querySelector(".deny");
  a.disabled = false;
  dn.disabled = false;
  a.textContent = "Allow once";
  dn.textContent = "Deny";
  approval.querySelectorAll(".hook-extra").forEach((b) => b.remove());
  if (pp.hook) {
    const row = approval.querySelector(".btns");
    const al = document.createElement("button");
    al.className = "hook-extra";
    al.textContent = "Always allow";
    al.onclick = () => {
      if (!pendingApproval) return;
      Jarvis.approval(true, { action: pp.action, remember: true }, pendingApproval.cid);
      settleApproval(al, "Allowing\u2026");
    };
    row.appendChild(al);
    if (pp.pid) {
      const tm = document.createElement("button");
      tm.className = "hook-extra";
      tm.textContent = "Terminal";
      tm.onclick = () => Jarvis.hookTerminal(pp.pid);
      row.appendChild(tm);
    }
  }
  delete approval.dataset.pending;
  approval.style.display = "block";
  bubble.style.display = "none";
  setMood("approval");
  setStatus("Needs approval", "active");
  clearTimeout(moodTimer);
}

// selection is only a request; the card stays in a pending state until the
// backend reports the outcome (or the prompt expires)
function settleApproval(btn, label) {
  if (!pendingApproval) return;
  approval.dataset.pending = "1";
  approval.querySelectorAll(".allow, .deny, .hook-extra").forEach((b) => { b.disabled = true; });
  btn.textContent = label;
  showBubble("Working\u2026", 8000);
  setMood("thinking");
  setStatus("Working\u2026", "active");
  clearTimeout(moodTimer);
  setTimeout(() => {
    if (approval.dataset.pending === "1") {
      approval.style.display = "none";
      delete approval.dataset.pending;
      pendingApproval = null;
      approval.querySelectorAll(".allow, .deny, .hook-extra").forEach((b) => { b.disabled = false; });
    }
  }, 90000);
}

approval.querySelector(".allow").onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(true, { action: pendingApproval.payload.action }, pendingApproval.cid);
    settleApproval(approval.querySelector(".allow"), "Allowing\u2026");
  }
};
approval.querySelector(".deny").onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(false, { action: pendingApproval.payload.action }, pendingApproval.cid);
    settleApproval(approval.querySelector(".deny"), "Denying\u2026");
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
    delete approval.dataset.pending;
    pendingApproval = null;
    const a = approval.querySelector(".allow");
    const dn = approval.querySelector(".deny");
    a.disabled = false;
    dn.disabled = false;
    a.textContent = "Allow once";
    dn.textContent = "Deny";
  }
  if (d.payload.role === "assistant" && d.payload.text) {
    showBubble(d.payload.text);
    setStatus("Ready", "idle");
    if (petEl.dataset.mood !== "speaking") moodTemp("happy", 2200);
  }
  if (d.payload.role === "user") {
    setMood("thinking");
    setStatus("Thinking\u2026", "active");
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
    setStatus("Working \u2014 " + (p.agent || "coding agent"), "active");
  } else if (st === "waiting") {
    clearTimeout(moodTimer);
    setMood("concerned");
    setStatus("Agent needs input", "active");
  } else if (petEl.dataset.mood === "executing") {
    moodTemp("happy", 1800);
    setStatus("Ready", "idle");
  }
});
Jarvis.on("ui.approval_cancelled", (d) => {
  if (pendingApproval && d.correlation_id && String(pendingApproval.cid) === String(d.correlation_id)) {
    approval.style.display = "none";
    delete approval.dataset.pending;
    pendingApproval = null;
    const a = approval.querySelector(".allow");
    const dn = approval.querySelector(".deny");
    a.disabled = false;
    dn.disabled = false;
    a.textContent = "Allow once";
    dn.textContent = "Deny";
    setStatus("Ready", "idle");
    showBubble("Timed out \u2014 denied.", 3500);
  }
});

Jarvis.on("tts_state", (d) => {
  const speaking = !!(d.payload && d.payload.speaking);
  if (speaking) {
    clearTimeout(moodTimer);
    setMood("speaking");
    setStatus("Speaking\u2026", "active");
  } else if (petEl.dataset.mood === "speaking") {
    moodTemp("happy", 1400);
    setStatus("Ready", "idle");
  }
});

Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  if (st === "listening") {
    setMood("listening");
    clearTimeout(moodTimer);
    setStatus("Listening\u2026", "active");
    showBubble("Listening...", 6000);
  } else if (st === "transcribing") {
    setMood("thinking");
    clearTimeout(moodTimer);
    setStatus("Transcribing\u2026", "active");
  } else if (st === "wake" || st === "idle") {
    if (["listening", "thinking"].includes(petEl.dataset.mood)) setMood("idle");
    setStatus("Ready", "idle");
  } else if (st === "error") {
    moodTemp("concerned", 4000);
    setStatus("Voice error", "active");
    showBubble("Voice: " + ((d.payload || {}).error || "error"), 4000);
  }
});

document.addEventListener("jarvis:connected", () => {
  setStatus("Ready", "idle");
  showBubble('Say "Hey Jarvis" or type a message.', 5000);
});
document.addEventListener("jarvis:disconnected", () => {
  setStatus("Offline", "off");
  showBubble("Reconnecting...", 3000);
});

function tcmd(name) {
  if (window.__TAURI__ && window.__TAURI__.tauri) window.__TAURI__.tauri.invoke(name);
}

let dragOrigin = null;
let dragMoved = false;
petEl.addEventListener("mousedown", (e) => {
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
  const cfg = ((d || {}).payload || {}).config || {};
  const v = cfg.voice || {};
  petSoundMuted = v.ui_sounds === false;
  // wardrobe/colorway (spec 29, section 5.5.7)
  const cw = (cfg.runtime || {}).pet_colorway || "obsidian";
  if (window.Pet3D && window.Pet3D.applyColorway) window.Pet3D.applyColorway(cw);
}
Jarvis.on("settings", syncPetSound);
Jarvis.on("settings_saved", syncPetSound);
Jarvis.getSettings();

petEl.onclick = () => {
  if (dragMoved) { dragMoved = false; return; }
  playSquish();
  tcmd("open_chat");
};
document.getElementById("btn-chat").onclick = () => tcmd("open_chat");
document.getElementById("btn-settings").onclick = () => tcmd("open_settings");

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
  setStatus("Inspecting " + name, "active");
  clearTimeout(moodTimer);
  setMood("ingesting");
  if (window.Pet3D && window.Pet3D.ingestDrop) window.Pet3D.ingestDrop();
  playGulp();
  Jarvis.fileIngest(list);
  moodTimer = setTimeout(() => { setMood("idle"); setStatus("Ready", "idle"); }, 4500);
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
  if (petEl.dataset.mood === "sleep") { setMood("idle"); setStatus("Ready", "idle"); }
}
document.addEventListener("mousemove", markActive, { passive: true });
document.addEventListener("mousedown", markActive, { passive: true });

petEl.addEventListener("mouseenter", () => {
  markActive();
  if (petEl.dataset.mood === "idle") { clearTimeout(moodTimer); setMood("curious"); }
});
petEl.addEventListener("mouseleave", () => {
  if (petEl.dataset.mood === "curious") { clearTimeout(moodTimer); setMood("idle"); }
});
// rapid clicking (>5 pokes in 1.5s -> dizzy)
const origClick = petEl.onclick;
petEl.onclick = (e) => {
  markActive();
  // poke impulse + volume-conserving squash (spec 29, section 5.5.4)
  if (window.Pet3D && window.Pet3D.poke && e) {
    const r = petEl.getBoundingClientRect();
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
    setStatus("Sleeping", "idle");
  }
}, 15000);

const micBtn = document.getElementById("btn-mic");
let micOn = false;
micBtn.onclick = () => {
  micOn = !micOn;
  Jarvis.voiceListen(micOn);
};
Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  micBtn.classList.toggle("rec", st === "listening");
  micBtn.classList.toggle("busy", st === "transcribing");
  micOn = st === "listening";
  document.body.classList.toggle("dock-show", st === "listening" || st === "transcribing");
});

setTimeout(() => showBubble("Hi, I'm Jarvis.", 4000), 800);
