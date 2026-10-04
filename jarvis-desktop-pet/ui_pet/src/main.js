// Shell: navigation, sidebar collapse, pet visibility (single source of
// truth for pet state stays the backend config).

const PANES = ["chat", "activity", "settings"];

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
};

// called from Rust tray menu
window.togglePetFromTray = () => applyPet(!petEnabled, true);
