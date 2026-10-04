const msgs = document.getElementById("msgs");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send");
const conn = document.getElementById("conn");
const typingEl = document.getElementById("typing");
const emptyEl = document.getElementById("empty-state");
const voiceStatus = document.getElementById("voice-status");
const voiceText = document.getElementById("vs-text");
const peekBtn = document.getElementById("approval-peek");
let typingTimer = null;
let stickBottom = true;
const USER_NAME = "Ammar";

// ---- procedural UI earcons (spec 29, section 5.4) ----
// 8 subtle state cues synthesized live via Web Audio (no audio assets).
const Earcons = (function () {
  let ctx = null;
  let muted = false;
  const GAIN = 0.16;
  function ensure() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      try { ctx = new AC(); } catch (e) { return null; }
    }
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    return ctx;
  }
  // browsers need a gesture before audio can start
  window.addEventListener("pointerdown", () => ensure(), { once: true });
  window.addEventListener("keydown", () => ensure(), { once: true });

  function tone(freq, t0, dur, opts) {
    opts = opts || {};
    const o = ctx.createOscillator();
    o.type = opts.type || "sine";
    o.frequency.setValueAtTime(freq, t0);
    if (opts.to) o.frequency.exponentialRampToValueAtTime(opts.to, t0 + dur);
    const g = ctx.createGain();
    const peak = opts.gain || GAIN;
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.001), t0 + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    o.connect(g);
    g.connect(ctx.destination);
    o.start(t0);
    o.stop(t0 + dur + 0.03);
  }
  function swoosh(t0, dur) {
    const frames = Math.floor(ctx.sampleRate * dur);
    const buf = ctx.createBuffer(1, frames, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < frames; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / frames);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const f = ctx.createBiquadFilter();
    f.type = "bandpass";
    f.frequency.setValueAtTime(600, t0);
    f.frequency.exponentialRampToValueAtTime(3200, t0 + dur);
    f.Q.value = 1.2;
    const g = ctx.createGain();
    g.gain.setValueAtTime(GAIN, t0);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(f); f.connect(g); g.connect(ctx.destination);
    src.start(t0);
  }
  const CUES = {
    // wake-word detected: gentle 2-note rising chime (440 -> 880)
    snd_wake: (t) => { tone(440, t, 0.10); tone(880, t + 0.10, 0.16, { gain: GAIN * 0.9 }); },
    // mic opens: subdued tactile click
    snd_listen_start: (t) => { tone(1200, t, 0.035, { type: "square", gain: GAIN * 0.45 }); },
    // mic closes / transcribing begins: low soft settle tone
    snd_listen_stop: (t) => { tone(330, t, 0.22, { gain: GAIN * 0.8 }); },
    // task completes: crisp bright 3-note major chord
    snd_success: (t) => { [523.25, 659.25, 783.99].forEach((f, i) => tone(f, t + i * 0.07, 0.30, { gain: GAIN * 0.8 })); },
    // tool failure / disconnection: muted low double-tap
    snd_error: (t) => { tone(196, t, 0.14, { type: "triangle" }); tone(196, t + 0.16, 0.18, { type: "triangle", gain: GAIN * 0.8 }); },
    // approval card arrives: high-contrast melodic warning chime
    snd_approval: (t) => { tone(987.77, t, 0.14); tone(783.99, t + 0.13, 0.24); },
    // poking the pet: tactile soft pop
    snd_squish: (t) => { tone(320, t, 0.14, { to: 110 }); },
    // top-edge dock expands (phase 5): soft swoosh
    snd_dock_peek: (t) => { swoosh(t, 0.28); },
  };
  function flash() {
    const logo = document.querySelector(".brand .logo");
    if (!logo) return;
    logo.classList.remove("sounding");
    void logo.offsetWidth; // restart the animation
    logo.classList.add("sounding");
  }
  return {
    play(name) {
      if (muted || !CUES[name]) return false;
      const c = ensure();
      if (!c) return false;
      try { CUES[name](c.currentTime + 0.005); flash(); return true; } catch (e) { return false; }
    },
    setMuted(m) { muted = !!m; },
    isMuted() { return muted; },
    names: Object.keys(CUES),
  };
})();
window.Earcons = Earcons;

// time-based greeting (spec 7.3 - subtle, second line does the work)
(function setGreeting() {
  const h = new Date().getHours();
  const part = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  const el = document.getElementById("greeting");
  if (el) el.textContent = part + ", " + USER_NAME;
})();

function hideEmpty() {
  if (emptyEl && emptyEl.parentElement) emptyEl.remove();
}

msgs.addEventListener("scroll", () => {
  stickBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 60;
  if (stickBottom && jumpBtn) jumpBtn.hidden = true;
});

let jumpBtn = null;
function ensureJumpBtn() {
  if (jumpBtn) return;
  jumpBtn = document.createElement("button");
  jumpBtn.id = "jump-latest";
  jumpBtn.type = "button";
  jumpBtn.hidden = true;
  jumpBtn.textContent = "New messages \u2193";
  jumpBtn.onclick = () => {
    msgs.scrollTop = msgs.scrollHeight;
    jumpBtn.hidden = true;
    stickBottom = true;
  };
  document.getElementById("pane-chat").appendChild(jumpBtn);
}
function scrollLatest(force) {
  if (force || stickBottom) msgs.scrollTop = msgs.scrollHeight;
  else ensureJumpBtn(), (jumpBtn.hidden = false);
}

function showTyping() {
  hideEmpty();
  typingEl.hidden = false;
  msgs.appendChild(typingEl);
  scrollLatest(true);
  clearTimeout(typingTimer);
  typingTimer = setTimeout(hideTyping, 60000);
}
function hideTyping() {
  typingEl.hidden = true;
  clearTimeout(typingTimer);
}

function nowTime() {
  try {
    return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch (e) {
    return "";
  }
}

function metaRow(who) {
  const meta = document.createElement("div");
  meta.className = "msg-meta";
  const av = document.createElement("div");
  if (who === "assistant") {
    av.className = "msg-avatar assistant orb";
    av.innerHTML = '<i class="core"></i>';
  } else {
    av.className = "msg-avatar user";
    av.innerHTML = '<svg class="ic"><use href="#i-user"/></svg>';
  }
  const name = document.createElement("span");
  name.className = "msg-name";
  name.textContent = who === "assistant" ? "Jarvis" : "You";
  const time = document.createElement("span");
  time.className = "msg-time";
  time.textContent = nowTime();
  meta.appendChild(av);
  meta.appendChild(name);
  meta.appendChild(time);
  return meta;
}

function addMsg(role, text) {
  hideEmpty();
  let node;
  if (role === "assistant" || role === "user") {
    const group = document.createElement("div");
    group.className = "msg-group " + role;
    group.appendChild(metaRow(role));
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    group.appendChild(div);
    node = group;
  } else {
    node = document.createElement("div");
    node.className = "msg " + role;
    node.textContent = text;
  }
  msgs.insertBefore(node, typingEl);
  scrollLatest();
}

// ---- composer ----
function autogrow() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 220) + "px";
}
input.addEventListener("input", autogrow);

function send() {
  const t = input.value.trim();
  if (!t) return;
  if (!typingEl.hidden) return; // one in-flight request at a time
  input.value = "";
  autogrow();
  showTyping();
  Jarvis.text(t);
}
sendBtn.onclick = send;
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});

// welcome action chips fill the composer (prompt suggestions, not auto-send)
document.querySelectorAll("#empty-state .chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.dataset.prompt || "";
    autogrow();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  });
});

// files dropped on the pet/dock: stage the inspection prompt in the composer
// (spec 29 sections 5.2 + acceptance 6 - the summary prompt opens, not auto-runs)
Jarvis.on("ui.file_ingest", (d) => {
  const items = ((d || {}).payload || {}).items || [];
  if (!items.length) return;
  const it = items[0];
  const q = String(it.path || "").replace(/"/g, "");
  if (!q) return;
  const more = items.length > 1 ? ` (and ${items.length - 1} more dropped file${items.length > 2 ? "s" : ""})` : "";
  const prompt =
    it.kind === "image"
      ? `Describe this image file: "${q}"${more}`
      : `Summarize this file: "${q}" - key points, structure, and anything notable.${more}`;
  if (window.showTab) showTab("chat");
  input.value = prompt;
  autogrow();
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
});

// header search: asking from anywhere lands in the conversation
const searchInput = document.getElementById("global-search");
if (searchInput) {
  searchInput.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const t = searchInput.value.trim();
    if (!t) return;
    searchInput.value = "";
    if (window.showTab) showTab("chat");
    input.value = t;
    send();
  });
}

// ---- microphone / voice states ----
const micBtns = [document.getElementById("mic"), document.getElementById("top-mic")].filter(Boolean);
let micOn = false;
function setMic(on) {
  micOn = on;
  micBtns.forEach((b) => {
    b.classList.toggle("rec", on);
    b.title = on ? "Stop listening" : "Click to talk";
    b.setAttribute("aria-pressed", String(on));
  });
}
function setMicBusy(busy) {
  micBtns.forEach((b) => {
    b.classList.toggle("busy", busy);
    b.disabled = busy;
  });
}
function setVoiceStatus(text, mode) {
  if (!voiceStatus) return;
  const col = document.getElementById("composer-col");
  if (col) col.classList.toggle("listening", mode === "listening");
  if (text) {
    voiceStatus.hidden = false;
    voiceText.textContent = text;
    voiceStatus.classList.toggle("transcribing", mode === "transcribing");
  } else {
    voiceStatus.hidden = true;
  }
}
function toggleMic() {
  const next = !micOn;
  setMic(next);
  Jarvis.voiceListen(next);
}
micBtns.forEach((b) => (b.onclick = () => { if (!b.disabled) toggleMic(); }));

let lastVoiceState = null;
Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  setMicBusy(false);
  if (st === "listening") {
    // wake-word path arrives from "wake"; manual push-to-talk from "idle"
    Earcons.play(lastVoiceState === "wake" ? "snd_wake" : "snd_listen_start");
    setMic(true);
    setVoiceStatus("Listening\u2026", "listening");
  } else if (st === "transcribing") {
    Earcons.play("snd_listen_stop");
    setMic(false);
    setMicBusy(true);
    setVoiceStatus("Transcribing\u2026", "transcribing");
  } else {
    setMic(false);
    setVoiceStatus("");
  }
  if (st === "error") {
    Earcons.play("snd_error");
    addMsg("system", "Voice: " + ((d.payload || {}).error || "unknown error"));
  }
  lastVoiceState = st;
});

// tool outcomes -> success/error earcons (spec 29, section 5.4)
Jarvis.on("tool.result", (d) => {
  Earcons.play((d.payload || {}).ok === false ? "snd_error" : "snd_success");
});

// stock acknowledgment / settings mute (spec 29, sections 3.1 + 5.4)
function syncSoundPrefs(d) {
  const v = ((d || {}).payload || {}).config || {};
  const voice = v.voice || {};
  Earcons.setMuted(voice.ui_sounds === false);
}
Jarvis.on("settings", syncSoundPrefs);
Jarvis.on("settings_saved", syncSoundPrefs);

Jarvis.on("ui.chat", (d) => {
  if (!d.payload) return;
  if (d.payload.role === "assistant") hideTyping();
  // any ui.chat carrying an approval's cid is that approval's outcome -
  // clears the card even when the user answered it in the other window
  if (d.correlation_id) {
    removeApprovalCards(String(d.correlation_id));
  }
  addMsg(d.payload.role || "assistant", d.payload.text || "");
});

// spoken responses: mirror TTS activity as a labelled state
Jarvis.on("tts_state", (d) => {
  const speaking = !!(d.payload && d.payload.speaking);
  if (speaking) setVoiceStatus("Speaking\u2026", "speaking");
  else if (voiceText && voiceText.textContent === "Speaking\u2026") setVoiceStatus("");
});

// ---- approvals (section 12 + mockup approval prompt) ----
const VERBS = {
  launch_app: "Open", open_app: "Open", close_app: "Close",
  delete_file: "Delete", move_file: "Move", create_file: "Create",
  list_dir: "List files in", open_url: "Open in your browser",
  web_search: "Search the web", run_shell: "Run a command",
  vision_describe: "Describe your screen", type_text: "Type text",
  vision_file: "Analyzed image file", summarize_file: "Summarized file",
  respond: "Respond", noop: "Run",
};

function friendlyAction(p) {
  const a = (p.action && (p.action.action || p.action.name)) || "";
  const verb = VERBS[a] || a.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  let tgt = (p.action && (p.action.target || p.action.path || p.action.url || p.action.cmd)) || "";
  if (tgt) {
    const parts = String(tgt).split(/[\\/]/);
    tgt = parts[parts.length - 1] || String(tgt);
    if (tgt.length > 46) tgt = tgt.slice(0, 43) + "\u2026";
  }
  return { verb, tgt, title: (verb + (tgt ? " " + tgt : "")).trim() };
}

function riskBand(r) {
  const n = Number(r);
  if (!isFinite(n)) return { cls: "med", label: "Unknown" };
  if (n <= 2) return { cls: "low", label: "Low" };
  if (n <= 6) return { cls: "med", label: "Medium" };
  return { cls: "high", label: "High" };
}

function removeApprovalCards(cid) {
  document.querySelectorAll(".approval-card").forEach((card) => {
    if (card.dataset.cid && String(card.dataset.cid) === String(cid)) card.remove();
  });
  if (!document.querySelector(".approval-card") && peekBtn) peekBtn.hidden = true;
}

Jarvis.on("ui.approval", (d) => {
  hideTyping();
  Earcons.play("snd_approval");
  const p = d.payload || {};
  const fa = friendlyAction(p);
  const band = riskBand(p.risk);
  const tgt = p.action && p.action.target;

  const wrap = document.createElement("div");
  wrap.className = "approval-card";
  if (d.correlation_id) wrap.dataset.cid = d.correlation_id;

  const head = document.createElement("div");
  head.className = "ac-head";
  head.innerHTML =
    '<span class="ac-shield"><svg class="ic"><use href="#i-shield"/></svg></span>' +
    '<span class="ac-title-label">Action requires approval</span>';
  const closeBtn = document.createElement("button");
  closeBtn.className = "ac-close";
  closeBtn.type = "button";
  closeBtn.title = "Hide for now";
  closeBtn.setAttribute("aria-label", "Collapse approval prompt");
  closeBtn.innerHTML = '<svg class="ic"><use href="#i-x"/></svg>';
  head.appendChild(closeBtn);

  const body = document.createElement("div");
  body.className = "ac-body";
  const app = document.createElement("div");
  app.className = "ac-app";
  app.innerHTML =
    '<span class="ac-app-icon"><svg class="ic"><use href="#i-folder"/></svg></span>' +
    '<div class="ac-app-main">' +
    '<div class="ac-action"></div>' +
    '<div class="ac-desc"></div>' +
    (tgt ? '<div class="ac-target">Target: </div>' : "") +
    "</div>";
  app.querySelector(".ac-action").textContent = fa.title;
  app.querySelector(".ac-desc").textContent =
    p.message || "Jarvis wants to run this action on your computer.";
  if (tgt) app.querySelector(".ac-target").textContent = "Target: " + tgt;
  body.appendChild(app);

  const meta = document.createElement("div");
  meta.className = "ac-meta";
  const riskCol = document.createElement("div");
  riskCol.className = "ac-risk";
  const lab = document.createElement("span");
  lab.className = "ac-label";
  lab.textContent = "Risk level";
  const badge = document.createElement("span");
  badge.className = "risk " + band.cls;
  badge.textContent = band.label;
  badge.title = p.risk == null ? "Risk unknown" : "Risk " + p.risk + "/10";
  riskCol.appendChild(lab);
  riskCol.appendChild(badge);
  meta.appendChild(riskCol);

  const why = document.createElement("div");
  why.className = "ac-why";
  const whyBtn = document.createElement("button");
  whyBtn.className = "ac-why-btn";
  whyBtn.type = "button";
  whyBtn.setAttribute("aria-expanded", "false");
  whyBtn.innerHTML = 'Why? <svg class="ic"><use href="#i-chevron"/></svg>';
  const whyBody = document.createElement("div");
  whyBody.className = "ac-why-body";
  whyBody.hidden = true;
  whyBody.textContent =
    "Jarvis wants to run: " + fa.title + ". Nothing happens on your computer until you allow it.";
  whyBtn.onclick = () => {
    const open = whyBody.hidden;
    whyBody.hidden = !open;
    whyBtn.setAttribute("aria-expanded", String(open));
  };
  why.appendChild(whyBtn);
  why.appendChild(whyBody);
  meta.appendChild(why);
  body.appendChild(meta);

  const btns = document.createElement("div");
  btns.className = "ac-btns";
  const allow = document.createElement("button");
  allow.className = "allow";
  allow.textContent = "Allow once";
  const deny = document.createElement("button");
  deny.className = "deny";
  deny.textContent = "Deny";
  const settle = (btn, label) => {
    wrap.dataset.pending = "1";
    [allow, deny].forEach((b) => { b.disabled = true; });
    wrap.querySelectorAll(".ac-extra").forEach((b) => { b.disabled = true; });
    btn.textContent = label;
    showTyping();
    // safety: never leave a stuck pending card around
    setTimeout(() => removeApprovalCards(wrap.dataset.cid || ""), 90000);
  };
  allow.onclick = () => {
    Jarvis.approval(true, { action: p.action }, d.correlation_id);
    settle(allow, "Allowing\u2026");
  };
  deny.onclick = () => {
    Jarvis.approval(false, { action: p.action }, d.correlation_id);
    settle(deny, "Denying\u2026");
  };
  btns.appendChild(deny);
  btns.appendChild(allow);
  if (p.hook) {
    // terminal approval (spec 4.2): session grant + terminal jump
    const always = document.createElement("button");
    always.className = "deny ac-extra";
    always.textContent = "Always allow for session";
    always.onclick = () => {
      Jarvis.approval(true, { action: p.action, remember: true }, d.correlation_id);
      settle(always, "Allowing\u2026");
    };
    btns.appendChild(always);
    if (p.pid) {
      const term = document.createElement("button");
      term.className = "ac-why-btn ac-extra";
      term.type = "button";
      term.textContent = "Open Terminal";
      term.onclick = () => Jarvis.hookTerminal(p.pid);
      btns.appendChild(term);
    }
  }

  closeBtn.onclick = () => {
    wrap.style.display = "none";
    if (peekBtn) peekBtn.hidden = false;
  };

  wrap.appendChild(head);
  wrap.appendChild(body);
  wrap.appendChild(btns);
  msgs.insertBefore(wrap, typingEl);
  if (peekBtn) peekBtn.hidden = true;
  scrollLatest(true);
});

if (peekBtn) {
  peekBtn.onclick = () => {
    const card = document.querySelector(".approval-card");
    if (card) {
      card.style.display = "";
      peekBtn.hidden = true;
      scrollLatest(true);
    } else {
      peekBtn.hidden = true;
    }
  };
}

// backend expired the approval (treated as denied) - remove the pending card
Jarvis.on("ui.approval_cancelled", (d) => {
  if (d.correlation_id) removeApprovalCards(String(d.correlation_id));
});

document.addEventListener("jarvis:connected", () => {
  conn.textContent = "Connected";
  conn.classList.add("on");
});
document.addEventListener("jarvis:disconnected", () => {
  conn.textContent = "Reconnecting\u2026";
  conn.classList.remove("on");
  Earcons.play("snd_error");
});
