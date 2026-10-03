const bubble = document.getElementById("bubble");
const approval = document.getElementById("approval");
const petEl = document.getElementById("pet");
let bubbleTimer = null;
let moodTimer = null;
let pendingApproval = null;

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
  approval.querySelector(".msg").innerHTML =
    (pendingApproval.payload.message || "Approve?") +
    ' <span class="risk">risk ' + (pendingApproval.payload.risk || "?") + "/10</span>";
  approval.style.display = "block";
  bubble.style.display = "none";
  setMood("concerned");
  clearTimeout(moodTimer);
}

approval.querySelector(".allow").onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(true, { action: pendingApproval.payload.action }, pendingApproval.cid);
  }
  approval.style.display = "none";
  pendingApproval = null;
  showBubble("Approved.", 2500);
  moodTemp("happy", 2500);
};
approval.querySelector(".deny").onclick = () => {
  if (pendingApproval) {
    Jarvis.approval(false, { action: pendingApproval.payload.action }, pendingApproval.cid);
  }
  approval.style.display = "none";
  pendingApproval = null;
  showBubble("Denied.", 2500);
  setMood("idle");
};

Jarvis.on("ui.pet_state", (d) => {
  if (d.payload && d.payload.text) showBubble(d.payload.text);
});
Jarvis.on("ui.chat", (d) => {
  if (!d.payload) return;
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

document.addEventListener("jarvis:connected", () => showBubble('Say "Hey Jarvis" or type a message.', 5000));
document.addEventListener("jarvis:disconnected", () => showBubble("Reconnecting...", 3000));

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

petEl.onclick = () => {
  if (dragMoved) { dragMoved = false; return; }
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
});

setTimeout(() => showBubble("Hi, I'm Jarvis.", 4000), 800);
