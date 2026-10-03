const note = document.getElementById("settings-note");
const val = (id) => document.getElementById(id).value;
const setv = (id, v) => { document.getElementById(id).value = v == null ? "" : v; };
let current = {};

function fill(s) {
  current = s;
  const cfg = s.config || {};
  const lm = cfg.lm_studio || {};
  setv("lm-url", lm.base_url);
  setv("lm-key", lm.api_key);
  setv("lm-timeout", lm.timeout_ms);

  const ar = s.agents && s.agents.agent_roles ? s.agents.agent_roles : {};
  setv("m-orchestrator", (ar.orchestrator || {}).model_id);
  setv("m-planner", (ar.planner || {}).model_id);
  setv("m-tool_control", (ar.tool_control || {}).model_id);
  setv("m-vision", (ar.vision || {}).model_id);
  setv("m-small", (ar.memory_agent || {}).model_id);

  const perm = s.permissions || {};
  setv("safety-mode", perm.default_policy || "conservative");
  const appr = (perm.approvals || {});
  setv("approval-timeout", appr.timeout_ms);

  const pers = s.personality || {};
  const ident = pers.identity || {};
  setv("p-name", ident.name);
  setv("p-wake", ident.wake_word);
  setv("p-voice", ident.voice_style);

  const rm = (cfg.resource_manager || {});
  setv("rm-vision-timeout", rm.vision_timeout_ms);
  setv("rm-unload-idle", rm.unload_idle_ms);
  setv("rm-cooldown", rm.cooldown_ms);

  const voice = cfg.voice || {};
  const wake = voice.wake || {};
  document.getElementById("v-wake").checked = wake.enabled !== false;
  setv("v-threshold", wake.threshold == null ? 0.5 : wake.threshold);
  setv("v-engine", voice.tts_engine || "kokoro");
  setv("v-voice", voice.tts_voice || "af_heart");
  setv("v-speed", voice.tts_speed == null ? 1 : voice.tts_speed);
  document.getElementById("v-speed-val").textContent =
    (voice.tts_speed == null ? 1 : voice.tts_speed).toFixed(2);
  note.textContent = "Loaded. Edit and press Save.";
  note.classList.remove("ok");
  Jarvis.voiceDevices();
  if (window.onSettingsLoaded) window.onSettingsLoaded(s);
}

function collect() {
  const s = JSON.parse(JSON.stringify(current));
  s.config = s.config || {};
  s.config.lm_studio = s.config.lm_studio || {};
  s.config.lm_studio.base_url = val("lm-url");
  s.config.lm_studio.api_key = val("lm-key");
  s.config.lm_studio.timeout_ms = Number(val("lm-timeout")) || 30000;
  s.config.resource_manager = s.config.resource_manager || {};
  s.config.resource_manager.vision_timeout_ms = Number(val("rm-vision-timeout")) || 20000;
  s.config.resource_manager.unload_idle_ms = Number(val("rm-unload-idle")) || 60000;
  s.config.resource_manager.cooldown_ms = Number(val("rm-cooldown")) || 2000;

  s.agents = s.agents || {};
  const ar = s.agents.agent_roles = s.agents.agent_roles || {};
  const ensure = (k, q) => (ar[k] = ar[k] || { quant: q });
  ensure("orchestrator", "Q5_K_M"); ensure("planner", "Q5_K_M");
  ensure("tool_control", "Q5_K_M"); ensure("vision", "Q5_K_M");
  ar.orchestrator.model_id = val("m-orchestrator");
  ar.planner.model_id = val("m-planner");
  ar.tool_control.model_id = val("m-tool_control");
  ar.vision.model_id = val("m-vision");
  const small = val("m-small");
  ["pet_ux", "perception", "memory_agent", "safety", "voice_tts"].forEach((k) => {
    ensure(k, "Q5_K_M");
    ar[k].model_id = small;
  });

  s.permissions = s.permissions || {};
  s.permissions.default_policy = val("safety-mode");
  s.permissions.approvals = s.permissions.approvals || {};
  s.permissions.approvals.timeout_ms = Number(val("approval-timeout")) || 45000;

  s.personality = s.personality || {};
  s.personality.identity = s.personality.identity || {};
  s.personality.identity.name = val("p-name");
  s.personality.identity.wake_word = val("p-wake");
  s.personality.identity.voice_style = val("p-voice");

  s.config.voice = s.config.voice || {};
  s.config.voice.wake = s.config.voice.wake || {};
  s.config.voice.wake.enabled = document.getElementById("v-wake").checked;
  s.config.voice.wake.threshold = Number(val("v-threshold")) || 0.5;
  s.config.voice.tts_engine = val("v-engine") || "kokoro";
  s.config.voice.tts_voice = val("v-voice") || "af_heart";
  s.config.voice.tts_speed = Number(val("v-speed")) || 1;
  return s;
}

Jarvis.on("settings", (d) => fill(d.payload));
Jarvis.on("settings_saved", (d) => {
  fill(d.payload);
  note.textContent = "Saved.";
  note.classList.add("ok");
});

// ---- microphone selection + live input level ----
Jarvis.on("voice_devices", (d) => {
  const sel = document.getElementById("v-device");
  const p = d.payload || {};
  const devices = p.devices || [];
  const current = sel.value || p.current || "";
  sel.innerHTML = '<option value="">System default input</option>';
  devices.forEach((dev) => {
    const o = document.createElement("option");
    o.value = dev.name;
    o.textContent = dev.name + (dev.default ? " (default)" : "") + (dev.rate ? " - " + dev.rate + " Hz" : "");
    sel.appendChild(o);
  });
  const names = devices.map((x) => x.name);
  sel.value = names.includes(current) ? current : "";
});
Jarvis.on("voice_device_set", (d) => {
  const p = d.payload || {};
  note.textContent = p.ok ? "Microphone set: " + (p.device || "system default") : "Could not open that microphone.";
  note.classList.toggle("ok", !!p.ok);
  Jarvis.voiceDevices();
});
Jarvis.on("ui.mic_level", (d) => {
  const p = d.payload || {};
  const bar = document.getElementById("v-level");
  if (!bar) return;
  const meter = bar.parentElement;
  const pct = Math.max(0, Math.min(100, ((p.level || 0) / 0.25) * 100));
  bar.style.width = pct.toFixed(1) + "%";
  meter.classList.toggle("hot", (p.level || 0) > 0.03);
  meter.classList.toggle("clip", (p.peak || 0) > 0.98);
  const nm = document.getElementById("v-level-name");
  if (nm) {
    const dev = (p.device || "").replace(/^Microphone \((.*)\)$/, "$1");
    nm.textContent = p.active ? (dev || "default") : "paused";
  }
});

document.getElementById("save").onclick = () => {
  note.textContent = "Saving...";
  Jarvis.saveSettings(collect());
};
document.getElementById("test").onclick = () => {
  const url = val("lm-url");
  note.textContent = "Testing " + url + " ...";
  note.classList.remove("ok");
  Jarvis.testLm(url);
};

document.getElementById("v-speed").addEventListener("input", (e) => {
  document.getElementById("v-speed-val").textContent = Number(e.target.value).toFixed(2);
});
document.getElementById("v-wake").addEventListener("change", (e) => {
  Jarvis.voiceWake(e.target.checked);
  note.textContent = e.target.checked ? "Wake word on." : "Wake word off (mic released).";
  note.classList.add("ok");
});
document.getElementById("v-device").addEventListener("change", (e) => {
  note.textContent = "Switching microphone...";
  note.classList.remove("ok");
  Jarvis.voiceDevice(e.target.value);
});
document.getElementById("tts-test").onclick = () => {
  const voice = val("v-voice");
  note.textContent = "Playing preview (" + voice + ")...";
  note.classList.add("ok");
  Jarvis.ttsTest(voice, "Hello, I am Jarvis. This is how I will sound.");
};

Jarvis.on("lm_test", (d) => {
  const p = d.payload || {};
  if (p.ok) {
    note.textContent = "LM Studio OK. Models: " + ((p.models || []).join(", ") || "none loaded");
    note.classList.add("ok");
  } else {
    note.textContent = "Cannot reach LM Studio (" + (p.base_url || "") + "): " + (p.error || "unknown error");
    note.classList.remove("ok");
  }
});

Jarvis.getSettings();
document.addEventListener("jarvis:connected", () => Jarvis.getSettings());