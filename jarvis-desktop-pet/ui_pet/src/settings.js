const note = document.getElementById("settings-note");
const val = (id) => document.getElementById(id).value;
const setv = (id, v) => { document.getElementById(id).value = v == null ? "" : v; };
let current = {};
let dirty = false;
const saveBtn = document.getElementById("save");
function setDirty(on) {
  on = !!on;
  if (dirty === on) return;
  dirty = on;
  saveBtn.disabled = !on;
  if (on) {
    note.textContent = "Unsaved changes.";
    note.classList.remove("ok");
  }
}
// controls that apply immediately (not via Save)
const IMMEDIATE_IDS = ["v-wake", "v-device", "v-autostart", "v-speed", "wake-test", "tts-test", "test", "save"];
const sc = document.getElementById("settings-content");
if (sc) {
  const mark = (e) => { if (e.target && !IMMEDIATE_IDS.includes(e.target.id)) setDirty(true); };
  sc.addEventListener("input", mark);
  sc.addEventListener("change", mark);
}

function fill(s) {
  current = s;
  const cfg = s.config || {};
  const lm = cfg.lm_studio || {};
  setv("lm-url", lm.base_url);
  setv("lm-key", lm.api_key);
  setv("lm-timeout", lm.timeout_ms == null ? 30 : lm.timeout_ms / 1000);

  const ar = s.agents && s.agents.agent_roles ? s.agents.agent_roles : {};
  setv("m-orchestrator", (ar.orchestrator || {}).model_id);
  setv("m-planner", (ar.planner || {}).model_id);
  setv("m-tool_control", (ar.tool_control || {}).model_id);
  setv("m-vision", (ar.vision || {}).model_id);
  setv("m-small", (ar.memory_agent || {}).model_id);

  const perm = s.permissions || {};
  setv("safety-mode", perm.default_policy || "conservative");
  const appr = (perm.approvals || {});
  setv("approval-timeout", appr.timeout_ms == null ? 45 : appr.timeout_ms / 1000);

  const pers = s.personality || {};
  const ident = pers.identity || {};
  setv("p-name", ident.name);
  setv("p-wake", ident.wake_word);
  setv("p-voice", ident.voice_style);

  const rm = (cfg.resource_manager || {});
  setv("rm-vision-timeout", rm.vision_timeout_ms == null ? 20 : rm.vision_timeout_ms / 1000);
  setv("rm-unload-idle", rm.unload_idle_ms == null ? 60 : rm.unload_idle_ms / 1000);
  setv("rm-cooldown", rm.cooldown_ms == null ? 2 : rm.cooldown_ms / 1000);

  const voice = cfg.voice || {};
  const wake = voice.wake || {};
  document.getElementById("v-wake").checked = wake.enabled !== false;
  setv("v-threshold", wake.threshold == null ? 0.35 : wake.threshold);
  document.getElementById("v-agc").checked = voice.agc !== false;
  document.getElementById("v-gate").checked = voice.noise_gate !== false;
  setv("v-hotkey", voice.hotkey || "");
  Jarvis.autostartState();
  setv("v-engine", voice.tts_engine || "kokoro");
  setv("v-voice", voice.tts_voice || "af_heart");
  setv("v-speed", voice.tts_speed == null ? 1 : voice.tts_speed);
  document.getElementById("v-speed-val").textContent =
    (voice.tts_speed == null ? 1 : voice.tts_speed).toFixed(2);
  note.textContent = "Loaded. Edit and press Save.";
  note.classList.remove("ok");
  setDirty(false);
  Jarvis.voiceDevices();
  Jarvis.rmState();
  if (window.onSettingsLoaded) window.onSettingsLoaded(s);
}

function collect() {
  const s = JSON.parse(JSON.stringify(current));
  s.config = s.config || {};
  s.config.lm_studio = s.config.lm_studio || {};
  s.config.lm_studio.base_url = val("lm-url");
  s.config.lm_studio.api_key = val("lm-key");
  s.config.lm_studio.timeout_ms = (Number(val("lm-timeout")) || 30) * 1000;
  s.config.resource_manager = s.config.resource_manager || {};
  s.config.resource_manager.vision_timeout_ms = (Number(val("rm-vision-timeout")) || 20) * 1000;
  s.config.resource_manager.unload_idle_ms = (Number(val("rm-unload-idle")) || 60) * 1000;
  s.config.resource_manager.cooldown_ms = (Number(val("rm-cooldown")) || 2) * 1000;

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
  s.permissions.approvals.timeout_ms = (Number(val("approval-timeout")) || 45) * 1000;

  s.personality = s.personality || {};
  s.personality.identity = s.personality.identity || {};
  s.personality.identity.name = val("p-name");
  s.personality.identity.wake_word = val("p-wake");
  s.personality.identity.voice_style = val("p-voice");

  s.config.voice = s.config.voice || {};
  s.config.voice.wake = s.config.voice.wake || {};
  s.config.voice.wake.enabled = document.getElementById("v-wake").checked;
  s.config.voice.wake.threshold = Number(val("v-threshold")) || 0.35;
  s.config.voice.tts_engine = val("v-engine") || "kokoro";
  s.config.voice.tts_voice = val("v-voice") || "af_heart";
  s.config.voice.tts_speed = Number(val("v-speed")) || 1;
  s.config.voice.agc = document.getElementById("v-agc").checked;
  s.config.voice.noise_gate = document.getElementById("v-gate").checked;
  s.config.voice.hotkey = val("v-hotkey").trim();
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
  const dh = document.getElementById("v-device-hint");
  if (dh) { dh.textContent = p.ok ? "Active input: " + (p.device || "system default") : "Could not open that microphone \u2014 check it is connected and not in use."; dh.classList.toggle("bad", !p.ok); }
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
  dirty = false;
  saveBtn.disabled = true;
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

// ---- wake word / mic test ----
const wtBtn = document.getElementById("wake-test");
const wtOut = document.getElementById("wake-test-out");
let wtTimer = null;
wtBtn.addEventListener("click", () => {
  wtBtn.disabled = true;
  wtOut.classList.remove("ok", "bad");
  wtOut.textContent = "Listening... say “Hey Jarvis”";
  Jarvis.wakeTest(8);
  clearTimeout(wtTimer);
  wtTimer = setTimeout(() => {
    if (wtBtn.disabled) {
      wtBtn.disabled = false;
      wtOut.classList.add("bad");
      wtOut.textContent = "No response from backend.";
    }
  }, 12000);
});
Jarvis.on("wake_test_ack", (d) => {
  if (!(d.payload || {}).ok) {
    wtBtn.disabled = false;
    clearTimeout(wtTimer);
    wtOut.classList.add("bad");
    wtOut.textContent = "Mic busy (transcribing or listening). Retry.";
  }
});
Jarvis.on("ui.wake_test", (d) => {
  const p = d.payload || {};
  if (p.phase === "start") {
    wtOut.classList.remove("ok", "bad");
    wtOut.textContent = "Listening... say “Hey Jarvis” (" + Math.round(p.seconds) + "s, threshold " + p.threshold + ")";
    if (!p.model_ready) wtOut.textContent = "Loading wake model...";
  } else if (p.phase === "run") {
    wtOut.classList.remove("ok", "bad");
    wtOut.textContent = "score " + p.score.toFixed(2) + " (max " + p.max.toFixed(2) + "/" + p.threshold + ") · level " + p.level.toFixed(3);
    const bar = document.getElementById("v-level");
    if (bar) {
      bar.style.width = Math.max(0, Math.min(100, (p.level / 0.25) * 100)).toFixed(1) + "%";
      bar.parentElement.classList.toggle("hot", p.level > 0.03);
    }
  } else if (p.phase === "done") {
    wtBtn.disabled = false;
    clearTimeout(wtTimer);
    if (p.error) {
      wtOut.classList.add("bad");
      wtOut.textContent = "Error: " + p.error;
    } else if (p.detected) {
      wtOut.classList.add("ok");
      wtOut.textContent = "Detected! max " + p.max_score.toFixed(2) + " >= " + p.threshold;
    } else {
      wtOut.classList.add("bad");
      wtOut.textContent =
        "Not detected (max " + p.max_score.toFixed(2) + " < " + p.threshold + ")" +
        (p.level > 0.02 ? " - lower the threshold or speak closer." : " - no voice detected; check the mic/meter.");
    }
  }
});

// ---- autostart with Windows ----
let pendingAutostart = null;
Jarvis.on("autostart_state", (d) => {
  const p = d.payload || {};
  const cb = document.getElementById("v-autostart");
  if (!cb) return;
  cb.checked = !!p.enabled;
  cb.disabled = p.available === false;
  const sec = cb.closest(".section");
  const hint = sec && sec.querySelector(".hint");
  if (hint && p.available === false) {
    hint.textContent = "Autostart is only available in the installed app.";
  }
  if (pendingAutostart !== null) {
    const ok = p.available !== false && p.enabled === pendingAutostart;
    note.textContent = ok
      ? pendingAutostart
        ? "Jarvis will start with Windows (chat hidden)."
        : "Autostart off."
      : "Could not change autostart.";
    note.classList.toggle("ok", ok);
    pendingAutostart = null;
  }
});
const asCb = document.getElementById("v-autostart");
if (asCb) {
  asCb.addEventListener("change", (e) => {
    pendingAutostart = e.target.checked;
    note.textContent = e.target.checked ? "Enabling autostart..." : "Disabling autostart...";
    note.classList.remove("ok");
    Jarvis.autostart(e.target.checked);
  });
}

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

// ---- settings index nav (scroll to section + active highlight) ----
const secNav = document.getElementById("settings-index");
if (secNav) {
  const navBtns = Array.prototype.slice.call(secNav.querySelectorAll("button[data-sec]"));
  navBtns.forEach((b) => {
    b.addEventListener("click", () => {
      const el = document.getElementById(b.dataset.sec);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  const setActive = (id) => navBtns.forEach((b) => b.classList.toggle("active", b.dataset.sec === id));
  const root = document.getElementById("pane-settings");
  if (root && window.IntersectionObserver) {
    const obs = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (vis.length) setActive(vis[0].target.id);
      },
      { root: root, threshold: [0.25, 0.6], rootMargin: "-72px 0px -55% 0px" }
    );
    navBtns.forEach((b) => { const el = document.getElementById(b.dataset.sec); if (el) obs.observe(el); });
  }
}

// ---- model memory (live load/offload status from the lifecycle manager) ----
function renderRmStatus(s) {
  const el = document.getElementById("rm-status");
  if (!el) return;
  if (!s || !Array.isArray(s.loaded)) { el.textContent = "Model status unavailable."; return; }
  if (!s.auto_manage) {
    el.textContent = "Automatic model memory is off. Loaded: " +
      (s.loaded.map((m) => m.id).join(", ") || "none") + ".";
    return;
  }
  const hint = document.getElementById("rm-hint");
  if (hint) {
    hint.textContent = "Models load when a task needs them and unload after " +
      s.unload_idle_s + "s idle (max " + s.max_concurrent + " at once), so memory stays free.";
  }
  if (!s.loaded.length) {
    el.textContent = "All models idle-unloaded \u2014 memory fully free. The next task loads its model on demand.";
    return;
  }
  el.innerHTML = "";
  const head = document.createElement("div");
  head.className = "rm-head";
  head.textContent = "In memory (" + s.loaded.length + "):";
  el.appendChild(head);
  s.loaded.forEach((m) => {
    const row = document.createElement("div");
    row.className = "rm-row";
    const badge = document.createElement("span");
    badge.className = "rm-badge" + (m.in_use > 0 ? " busy" : "");
    badge.textContent = m.in_use > 0 ? "using" : "idle";
    const idn = document.createElement("span");
    idn.className = "rm-id";
    idn.textContent = m.id;
    const idle = document.createElement("span");
    idle.className = "rm-idle";
    idle.textContent = m.in_use > 0 ? "active now" : m.idle_s + "s";
    row.appendChild(badge);
    row.appendChild(idn);
    row.appendChild(idle);
    el.appendChild(row);
  });
}
Jarvis.on("rm_state", (d) => renderRmStatus(d.payload));