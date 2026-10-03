// Tab switching + pet visibility control (single source of truth: backend config)

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.getElementById("pane-chat").classList.toggle("active", name === "chat");
  document.getElementById("pane-settings").classList.toggle("active", name === "settings");
  if (name === "chat") {
    const msgs = document.getElementById("msgs");
    msgs.scrollTop = msgs.scrollHeight;
    document.getElementById("chat-input").focus();
  }
}
window.showTab = showTab;

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => showTab(t.dataset.tab);
});
if (location.hash === "#settings") showTab("settings");

let petEnabled = true;

function tcmd(name, args) {
  if (window.__TAURI__ && window.__TAURI__.tauri) window.__TAURI__.tauri.invoke(name, args);
}

function applyPet(enabled, persist) {
  petEnabled = !!enabled;
  const sw = document.getElementById("pet-enabled");
  if (sw) sw.checked = petEnabled;
  const btn = document.getElementById("pet-toggle");
  if (btn) btn.classList.toggle("active", petEnabled);
  tcmd("set_pet", { visible: petEnabled });
  if (persist && window.Jarvis) Jarvis.setPet(petEnabled);
}

document.getElementById("pet-toggle").onclick = () => applyPet(!petEnabled, true);
document.getElementById("pet-enabled").onchange = (e) => applyPet(e.target.checked, true);

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
