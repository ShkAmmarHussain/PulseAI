const msgs = document.getElementById("msgs");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send");
const conn = document.getElementById("conn");
const typingEl = document.getElementById("typing");
const emptyEl = document.getElementById("empty-state");
const voiceStatus = document.getElementById("voice-status");
const voiceText = document.getElementById("vs-text");
let typingTimer = null;
let stickBottom = true;

function hideEmpty() {
  if (emptyEl) emptyEl.remove();
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

function addMsg(role, text) {
  hideEmpty();
  let node;
  if (role === "assistant") {
    const row = document.createElement("div");
    row.className = "msg-row";
    const av = document.createElement("div");
    av.className = "avatar";
    av.innerHTML = '<svg class="ic"><use href="#i-face"/></svg>';
    const wrap = document.createElement("div");
    wrap.className = "msg-col";
    const name = document.createElement("span");
    name.className = "msg-name";
    name.textContent = "Jarvis";
    const div = document.createElement("div");
    div.className = "msg assistant";
    div.textContent = text;
    wrap.appendChild(name);
    wrap.appendChild(div);
    row.appendChild(av);
    row.appendChild(wrap);
    node = row;
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
  input.style.height = Math.min(input.scrollHeight, 148) + "px";
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

// ---- microphone / voice states ----
const micBtn = document.getElementById("mic");
let micOn = false;
function setMic(on) {
  micOn = on;
  micBtn.classList.toggle("rec", on);
  micBtn.title = on ? "Stop listening" : "Click to talk";
  micBtn.setAttribute("aria-pressed", String(on));
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
micBtn.onclick = () => {
  if (micBtn.disabled) return;
  const next = !micOn;
  setMic(next);
  Jarvis.voiceListen(next);
};
Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  micBtn.classList.remove("busy");
  micBtn.disabled = false;
  if (st === "listening") {
    setMic(true);
    setVoiceStatus("Listening\u2026", "listening");
  } else if (st === "transcribing") {
    setMic(false);
    micBtn.classList.add("busy");
    micBtn.disabled = true;
    setVoiceStatus("Transcribing\u2026", "transcribing");
  } else {
    setMic(false);
    setVoiceStatus("");
  }
  if (st === "error") addMsg("system", "Voice: " + ((d.payload || {}).error || "unknown error"));
});

Jarvis.on("ui.chat", (d) => {
  if (!d.payload) return;
  if (d.payload.role === "assistant") hideTyping();
  // any ui.chat carrying an approval's cid is that approval's outcome -
  // clears the card even when the user answered it in the other window
  if (d.correlation_id) {
    document.querySelectorAll(".approval-card").forEach((card) => {
      if (card.dataset.cid && String(card.dataset.cid) === String(d.correlation_id)) card.remove();
    });
  }
  addMsg(d.payload.role || "assistant", d.payload.text || "");
});

// spoken responses: mirror TTS activity as a labelled state
Jarvis.on("tts_state", (d) => {
  const speaking = !!(d.payload && d.payload.speaking);
  if (speaking) setVoiceStatus("Speaking\u2026", "speaking");
  else if (voiceText && voiceText.textContent === "Speaking\u2026") setVoiceStatus("");
});

// ---- approvals ----
Jarvis.on("ui.approval", (d) => {
  hideTyping();
  const p = d.payload || {};
  const wrap = document.createElement("div");
  wrap.className = "approval-card";
  if (d.correlation_id) wrap.dataset.cid = d.correlation_id;
  const text = document.createElement("div");
  text.className = "ac-text";
  text.textContent = p.message || "Approval needed";
  const risk = document.createElement("span");
  risk.className = "risk";
  risk.textContent = "Risk level " + (p.risk == null ? "?" : p.risk) + "/10 \u2014 confirmation required";
  text.appendChild(risk);
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
    btn.textContent = label;
    showTyping();
    // safety: never leave a stuck pending card around
    setTimeout(() => wrap.remove(), 90000);
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
  wrap.appendChild(text);
  wrap.appendChild(btns);
  msgs.insertBefore(wrap, typingEl);
  scrollLatest(true);
});

// backend expired the approval (treated as denied) - remove the pending card
Jarvis.on("ui.approval_cancelled", (d) => {
  const cid = d.correlation_id;
  document.querySelectorAll(".approval-card").forEach((card) => {
    if (cid && card.dataset.cid === String(cid)) card.remove();
  });
});

document.addEventListener("jarvis:connected", () => {
  conn.textContent = "connected";
  conn.classList.add("on");
});
document.addEventListener("jarvis:disconnected", () => {
  conn.textContent = "reconnecting...";
  conn.classList.remove("on");
});
