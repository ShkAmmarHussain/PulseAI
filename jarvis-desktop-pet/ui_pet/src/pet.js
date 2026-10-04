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
  setMood("concerned");
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
function syncPetSound(d) {
  const v = (((d || {}).payload || {}).config || {}).voice || {};
  petSoundMuted = v.ui_sounds === false;
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
