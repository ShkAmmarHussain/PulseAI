const msgs = document.getElementById("msgs");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send");
const conn = document.getElementById("conn");
const typingEl = document.getElementById("typing");
const emptyEl = document.getElementById("empty-state");
let typingTimer = null;

function hideEmpty() {
  if (emptyEl) emptyEl.remove();
}

function showTyping() {
  hideEmpty();
  typingEl.hidden = false;
  msgs.appendChild(typingEl);
  msgs.scrollTop = msgs.scrollHeight;
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
  msgs.scrollTop = msgs.scrollHeight;
}

function send() {
  const t = input.value.trim();
  if (!t) return;
  input.value = "";
  showTyping();
  Jarvis.text(t);
}
sendBtn.onclick = send;
input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

const micBtn = document.getElementById("mic");
let micOn = false;
function setMic(on) {
  micOn = on;
  micBtn.classList.toggle("rec", on);
}
micBtn.onclick = () => {
  const next = !micOn;
  setMic(next);
  Jarvis.voiceListen(next);
};
Jarvis.on("ui.voice_state", (d) => {
  const st = (d.payload || {}).state || "idle";
  micBtn.classList.remove("busy");
  if (st === "listening") { setMic(true); showTyping(); }
  else if (st === "transcribing") { setMic(false); micBtn.classList.add("busy"); }
  else setMic(false);
  if (st === "error") addMsg("system", "Voice: " + ((d.payload || {}).error || "unknown error"));
});

Jarvis.on("ui.chat", (d) => {
  if (!d.payload) return;
  if (d.payload.role === "assistant") hideTyping();
  addMsg(d.payload.role || "assistant", d.payload.text || "");
});
Jarvis.on("ui.approval", (d) => {
  hideTyping();
  const p = d.payload || {};
  const wrap = document.createElement("div");
  wrap.className = "approval-card";
  const text = document.createElement("div");
  text.className = "ac-text";
  text.textContent = p.message || "Approval needed";
  const risk = document.createElement("span");
  risk.className = "risk";
  risk.textContent = "risk " + (p.risk || "?") + "/10";
  text.appendChild(risk);
  const btns = document.createElement("div");
  btns.className = "ac-btns";
  const allow = document.createElement("button");
  allow.className = "allow";
  allow.textContent = "Allow";
  const deny = document.createElement("button");
  deny.className = "deny";
  deny.textContent = "Deny";
  allow.onclick = () => {
    Jarvis.approval(true, { action: p.action }, d.correlation_id);
    wrap.remove();
    showTyping();
  };
  deny.onclick = () => {
    Jarvis.approval(false, { action: p.action }, d.correlation_id);
    wrap.remove();
    addMsg("system", "Action denied.");
  };
  btns.appendChild(allow);
  btns.appendChild(deny);
  wrap.appendChild(text);
  wrap.appendChild(btns);
  msgs.insertBefore(wrap, typingEl);
  msgs.scrollTop = msgs.scrollHeight;
});

document.addEventListener("jarvis:connected", () => {
  conn.textContent = "connected";
  conn.classList.add("on");
});
document.addEventListener("jarvis:disconnected", () => {
  conn.textContent = "reconnecting...";
  conn.classList.remove("on");
});
