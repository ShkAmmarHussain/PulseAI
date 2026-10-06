// Shell: navigation, sidebar collapse, pet visibility (single source of
// truth for pet state stays the backend config).

const PANES = ["chat", "activity", "memory", "settings"];

function showTab(name) {
  if (PANES.indexOf(name) < 0) name = "chat";
  document.querySelectorAll(".nav-item").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  PANES.forEach((n) => {
    const el = document.getElementById("pane-" + n);
    if (el) el.classList.toggle("active", n === name);
  });
  if (name === "chat") {
    const msgs = document.getElementById("msgs");
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
    const input = document.getElementById("chat-input");
    if (input) input.focus();
  }
}
window.showTab = showTab;

document.querySelectorAll(".nav-item").forEach((t) => {
  t.onclick = () => showTab(t.dataset.tab);
});
if (location.hash === "#settings") showTab("settings");
else if (location.hash === "#activity") showTab("activity");

// ---- sidebar collapse (manual override wins; auto below 1100px) ----
const appEl = document.getElementById("app");
const sbToggle = document.getElementById("sb-toggle");
let sbManual = null;
function sbApply() {
  if (!appEl) return;
  const collapsed = sbManual === null ? window.innerWidth < 1100 : sbManual;
  appEl.classList.toggle("sb-collapsed", collapsed);
}
if (sbToggle) {
  sbToggle.onclick = () => {
    sbManual = !appEl.classList.contains("sb-collapsed");
    sbApply();
  };
}
window.addEventListener("resize", () => {
  if (sbManual === null) sbApply();
});
sbApply();

// ---- header shortcuts ----
const topSettings = document.getElementById("top-settings");
if (topSettings) topSettings.onclick = () => showTab("settings");

const qaBtn = document.getElementById("quick-actions-btn");
if (qaBtn) {
  qaBtn.onclick = () => {
    showTab("chat");
    const chip = document.querySelector("#empty-state .chip");
    if (chip) chip.focus();
    else {
      const input = document.getElementById("chat-input");
      if (input) input.focus();
    }
  };
}

// ---- pet visibility ----
let petEnabled = true;

function tcmd(name, args) {
  if (window.__TAURI__ && window.__TAURI__.tauri) window.__TAURI__.tauri.invoke(name, args);
}

function applyPet(enabled, persist) {
  petEnabled = !!enabled;
  document.querySelectorAll("[data-pet-toggle]").forEach((cb) => {
    cb.checked = petEnabled;
  });
  tcmd("set_pet", { visible: petEnabled });
  if (persist && window.Jarvis) Jarvis.setPet(petEnabled);
}

document.querySelectorAll("[data-pet-toggle]").forEach((cb) => {
  cb.onchange = (e) => applyPet(e.target.checked, true);
});

// backend broadcasts the authoritative state after any set_pet (incl. tray menu)
Jarvis.on("ui.pet_visibility", (d) => applyPet((d.payload || {}).enabled !== false, false));

// called by settings.js whenever fresh settings arrive (initial load / save)
window.onSettingsLoaded = (s) => {
  const rt = (s.config && s.config.runtime) || {};
  if (typeof rt.pet_enabled === "boolean" && rt.pet_enabled !== petEnabled) {
    applyPet(rt.pet_enabled, false);
  }
  applyCompanion(rt.companion || "pet");
};

// ---- companion presentation: floating pet vs top-edge dock (spec 29, section 5.1) ----
let companionMode = null;

function applyCompanion(mode) {
  companionMode = mode === "dock" ? "dock" : "pet";
  if (!window.__TAURI__ || !window.__TAURI__.tauri) return;
  window.__TAURI__.tauri.invoke("set_companion", { mode: companionMode });
  // dock mode hides the pet window locally (does NOT persist pet_enabled);
  // pet mode restores whatever the user's pet toggle says
  window.__TAURI__.tauri.invoke("set_pet", { visible: companionMode === "pet" && petEnabled });
}
window.applyCompanion = applyCompanion;

// Rust evals this after every set_companion so the window state never drifts
window.onCompanionChanged = (mode) => {
  companionMode = mode === "dock" ? "dock" : "pet";
  if (window.setCompanionSeg) window.setCompanionSeg(companionMode);
};

// called from Rust tray menu
window.togglePetFromTray = () => {
  if (companionMode === "dock") applyCompanion("pet");
  else applyPet(!petEnabled, true);
};

// ---- dictate-to-cursor bubble (spec 29, section 3.2) ----
const dictBubble = document.getElementById("dictation-bubble");
const dictBtn = document.getElementById("dictate-btn");
if (dictBtn) dictBtn.onclick = () => Jarvis.dictation("toggle");
Jarvis.on("dictation.start", () => {
  if (dictBtn) dictBtn.classList.add("rec");
  if (!dictBubble) return;
  dictBubble.hidden = false;
  dictBubble.classList.remove("flash");
  const lbl = dictBubble.querySelector(".db-label");
  if (lbl) lbl.textContent = "Listening — speak to type";
});
Jarvis.on("dictation.stop", () => {
  if (dictBtn) dictBtn.classList.remove("rec");
  if (dictBubble) dictBubble.hidden = true;
});
Jarvis.on("dictation.result", (d) => {
  if (!dictBubble) return;
  const p = d.payload || {};
  const lbl = dictBubble.querySelector(".db-label");
  if (lbl) lbl.textContent = p.injected === false ? "Couldn't inject text" : "Typed into " + (p.app || "focused window");
  dictBubble.classList.add("flash");
  clearTimeout(dictBubble._hideT);
  dictBubble._hideT = setTimeout(() => {
    dictBubble.hidden = true;
    dictBubble.classList.remove("flash");
  }, 2500);
});
Jarvis.on("ui.mic_level", (d) => {
  if (!dictBubble || dictBubble.hidden) return;
  const lvl = Math.min(1, (d.payload || {}).level || 0);
  const now = Date.now();
  const bars = dictBubble.querySelectorAll(".db-bars i");
  bars.forEach((b, i) => {
    const wob = 0.5 + 0.5 * Math.sin(now / 90 + i * 1.4);
    const h = 10 + lvl * 60 * (0.45 + 0.55 * wob);
    b.style.height = Math.max(8, Math.min(72, h)).toFixed(0) + "px";
  });
});
