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
  const mark = (e) => {
    // dictionary + history have their own save buttons, not the global Save
    if (e.target && e.target.closest && e.target.closest("#sec-dictionary, #sec-history, #sec-integrations")) return;
    if (e.target && !IMMEDIATE_IDS.includes(e.target.id)) setDirty(true);
  };
  sc.addEventListener("input", mark);
  sc.addEventListener("change", mark);
}

// ---- companion presentation toggle (spec 29, section 5.1) ----
function setCompanionSeg(mode) {
  document.querySelectorAll("#companion-seg [data-mode]").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-mode") === mode);
  });
}
function selectedCompanion() {
  const on = document.querySelector("#companion-seg [data-mode].on");
  return on ? on.getAttribute("data-mode") : "pet";
}
document.querySelectorAll("#companion-seg [data-mode]").forEach((b) => {
  b.addEventListener("click", () => {
    setCompanionSeg(b.getAttribute("data-mode"));
    setDirty(true);
    if (window.applyCompanion) window.applyCompanion(selectedCompanion());
  });
});

// ---- pet render style: 2D vector vs 3D WebGL (doc 31, section 4.3) ----
function setRenderSeg(mode) {
  document.querySelectorAll("#pet-render-seg [data-render]").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-render") === mode);
  });
}
function selectedRender() {
  const on = document.querySelector("#pet-render-seg [data-render].on");
  return on ? on.getAttribute("data-render") : "2d";
}
window.setRenderSeg = setRenderSeg;
document.querySelectorAll("#pet-render-seg [data-render]").forEach((b) => {
  b.addEventListener("click", () => {
    const mode = b.getAttribute("data-render");
    // applies instantly: persist now so the pet window switches on the
    // settings broadcast (no Save press needed for this control)
    const p = JSON.parse(JSON.stringify(current || {}));
    if (!p.config) return;
    p.config.runtime = p.config.runtime || {};
    p.config.runtime.pet_render_mode = mode;
    current = p;
    setRenderSeg(mode);
    ownSaveAt = Date.now(); // our direct settings_saved reply is authoritative
    Jarvis.saveSettings(p);
  });
});

// ---- model provider picker: lm_studio / openai / anthropic (spec 33, section 5.1) ----
function setProviderSeg(p) {
  document.querySelectorAll("#provider-seg [data-provider]").forEach((b) => {
    b.classList.toggle("on", b.getAttribute("data-provider") === p);
  });
}
function selectedProvider() {
  const on = document.querySelector("#provider-seg [data-provider].on");
  return on ? on.getAttribute("data-provider") : "lm_studio";
}
function showProvFields(p) {
  const map = {
    "prov-lm-field": p === "lm_studio",
    "prov-lm-key-field": p === "lm_studio",
    "prov-openai-field": p === "openai",
    "prov-anthropic-field": p === "anthropic",
  };
  Object.keys(map).forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.hidden = !map[id];
  });
}
window.setProviderSeg = setProviderSeg;
document.querySelectorAll("#provider-seg [data-provider]").forEach((b) => {
  b.addEventListener("click", () => {
    const p = b.getAttribute("data-provider");
    setProviderSeg(p);
    showProvFields(p);
    setDirty(true);
  });
});
function providerKeyOf(p) {
  if (p === "openai") return (document.getElementById("prov-openai-key") || {}).value || "";
  if (p === "anthropic") return (document.getElementById("prov-anthropic-key") || {}).value || "";
  return (document.getElementById("lm-key") || {}).value || "";
}
function testProvider() {
  const p = selectedProvider();
  const key = providerKeyOf(p);
  note.textContent = "Testing " + Jarvis.providerName(p) + " ...";
  note.classList.remove("ok");
  Jarvis.testLm(p === "lm_studio" ? val("lm-url") : null, p, key);
}
let provTestT = null;
["prov-openai-key", "prov-anthropic-key"].forEach((id) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", () => {
    // a pasted key validates immediately - no endpoint to configure (spec 33)
    clearTimeout(provTestT);
    const key = el.value.trim();
    if (key.length < 10) return;
    provTestT = setTimeout(testProvider, 900);
  });
});

function fill(s) {
  current = s;
  const cfg = s.config || {};
  const lm = cfg.lm_studio || {};
  setv("lm-url", lm.base_url);
  setv("lm-key", lm.api_key);
  setv("lm-timeout", lm.timeout_ms == null ? 30 : lm.timeout_ms / 1000);

  const llm = cfg.llm || {};
  const prov = llm.provider === "openai" || llm.provider === "anthropic" ? llm.provider : "lm_studio";
  setProviderSeg(prov);
  showProvFields(prov);
  setv("prov-openai-key", ((llm.openai || {}).api_key) || "");
  setv("prov-anthropic-key", ((llm.anthropic || {}).api_key) || "");

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
  setv("v-dict-hotkey", voice.dictation_hotkey || "ctrl+alt+d");
  Jarvis.autostartState();
  Jarvis.hookState();
  setv("v-engine", voice.tts_engine || "kokoro");
  setv("v-voice", voice.tts_voice || "af_heart");
  setv("v-speed", voice.tts_speed == null ? 1 : voice.tts_speed);
  document.getElementById("v-speed-val").textContent =
    (voice.tts_speed == null ? 1 : voice.tts_speed).toFixed(2);
  const uiSounds = document.getElementById("v-ui-sounds");
  if (uiSounds) uiSounds.checked = voice.ui_sounds === false;
  setCompanionSeg(((cfg.runtime || {}).companion) === "dock" ? "dock" : "pet");
  setRenderSeg(((cfg.runtime || {}).pet_render_mode) === "3d" ? "3d" : "2d");
  setv("pet-colorway", (cfg.runtime || {}).pet_colorway || "porcelain");
  note.textContent = "Loaded. Edit and press Save.";
  note.classList.remove("ok");
  setDirty(false);
  Jarvis.voiceDevices();
  Jarvis.rmState();
  Jarvis.vocabulary();
  Jarvis.dictationHistory();
  if (window.onSettingsLoaded) window.onSettingsLoaded(s);
}

function collect() {
  const s = JSON.parse(JSON.stringify(current));
  s.config = s.config || {};
  s.config.lm_studio = s.config.lm_studio || {};
  s.config.lm_studio.base_url = val("lm-url");
  s.config.lm_studio.api_key = val("lm-key");
  s.config.lm_studio.timeout_ms = (Number(val("lm-timeout")) || 30) * 1000;
  s.config.llm = s.config.llm || {};
  s.config.llm.provider = selectedProvider();
  if (typeof s.config.llm.auto_routing === "undefined") s.config.llm.auto_routing = true;
  s.config.llm.openai = Object.assign({}, s.config.llm.openai || {}, { api_key: val("prov-openai-key").trim() });
  s.config.llm.anthropic = Object.assign({}, s.config.llm.anthropic || {}, { api_key: val("prov-anthropic-key").trim() });
  s.config.resource_manager = s.config.resource_manager || {};
  s.config.resource_manager.vision_timeout_ms = (Number(val("rm-vision-timeout")) || 20) * 1000;
  s.config.resource_manager.unload_idle_ms = (Number(val("rm-unload-idle")) || 60) * 1000;
  s.config.resource_manager.cooldown_ms = (Number(val("rm-cooldown")) || 2) * 1000;
  s.config.runtime = s.config.runtime || {};
  s.config.runtime.companion = selectedCompanion();
  s.config.runtime.pet_render_mode = selectedRender();
  s.config.runtime.pet_colorway = val("pet-colorway") || "porcelain";

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
  s.config.voice.dictation_hotkey = val("v-dict-hotkey").trim() || "ctrl+alt+d";
  const uiSounds = document.getElementById("v-ui-sounds");
  if (uiSounds) s.config.voice.ui_sounds = !uiSounds.checked;
  return s;
}

Jarvis.on("settings", (d) => fill(d.payload));
let saveTimeout = null;
let ownSaveAt = 0;
Jarvis.on("settings_saved", (d) => {
  clearTimeout(saveTimeout);
  saveTimeout = null;
  fill(d.payload);
  note.textContent = "Saved.";
  note.classList.add("ok");
});
// saves made in ANOTHER window only arrive here as ui.state {settings_saved};
// refetch so companion / colorway / permission changes apply in this window too.
// Skip when we initiated the save ourselves - our direct reply already refilled.
let refetchT = null;
Jarvis.on("ui.state", (d) => {
  if (!(d.payload || {}).settings_saved) return;
  if (Date.now() - ownSaveAt < 5000) return;
  clearTimeout(refetchT);
  refetchT = setTimeout(() => Jarvis.getSettings(), 200);
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
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    saveTimeout = null;
    note.textContent = "Save didn\u2019t confirm \u2014 changes may not be stored. Try again.";
    note.classList.remove("ok");
    saveBtn.disabled = false;
  }, 8000);
  ownSaveAt = Date.now();
  Jarvis.saveSettings(collect());
};
document.getElementById("test").onclick = () => testProvider();

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
  const prov = p.provider || "lm_studio";
  Jarvis.renderConnectCard(document.getElementById("lm-test-card"), p);
  if (p.ok) {
    note.textContent =
      prov === "lm_studio"
        ? "LM Studio OK. Models: " + ((p.models || []).join(", ") || "none loaded")
        : Jarvis.providerName(prov) + " OK. " + ((p.models || []).length || 0) + " model(s) available.";
    note.classList.add("ok");
  } else {
    note.textContent =
      "Cannot reach " + Jarvis.providerName(prov) + (p.base_url ? " (" + p.base_url + ")" : "") +
      ": " + (p.error || "unknown error");
    note.classList.remove("ok");
  }
});

Jarvis.getSettings();
document.addEventListener("jarvis:connected", () => Jarvis.getSettings());

// ---- settings index nav: strict single-tab rendering (doc 31, section 4.3) ----
// Only the active section is displayed - no scroll-bleed between sections.
const secNav = document.getElementById("settings-index");
if (secNav) {
  const navBtns = Array.prototype.slice.call(secNav.querySelectorAll("button[data-sec]"));
  const showSettingsTab = (tabName) => {
    const id = tabName && tabName.indexOf("sec-") === 0 ? tabName : "sec-" + tabName;
    navBtns.forEach((b) => b.classList.toggle("active", b.dataset.sec === id));
    document.querySelectorAll("#settings-content .section").forEach((sec) => {
      const match = sec.id === id;
      // "" falls back to the stylesheet's flex layout; "none" isolates the tab
      sec.style.display = match ? "" : "none";
      if (match) {
        sec.classList.remove("fade-in");
        void sec.offsetWidth; // restart the fade animation
        sec.classList.add("fade-in");
      }
    });
  };
  window.showSettingsTab = showSettingsTab;
  navBtns.forEach((b) => {
    b.addEventListener("click", () => showSettingsTab(b.dataset.sec));
  });
  const start = navBtns.find((b) => b.classList.contains("active")) || navBtns[0];
  if (start) showSettingsTab(start.dataset.sec);
}

// ---- model memory (live load/offload status from the lifecycle manager) ----
function renderRmStatus(s) {
  const el = document.getElementById("rm-status");
  if (!el) return;
  // zero-LLM bypass counter (spec 29, Phase 3) - shown in every branch
  const fpLine = () => {
    const fp = s && s.fast_path;
    if (!fp || fp.enabled === false) return;
    const line = document.createElement("div");
    line.className = "rm-fast";
    line.textContent =
      "Fast path: " + fp.hits + " command(s) answered without the LLM" +
      (fp.last_latency_ms ? " (last " + fp.last_latency_ms + "ms)" : "") + ".";
    el.appendChild(line);
  };
  const setText = (t) => {
    el.textContent = t;
    fpLine();
  };
  if (!s || !Array.isArray(s.loaded)) { setText("Model status unavailable."); return; }
  if (!s.auto_manage) {
    setText("Automatic model memory is off. Loaded: " +
      (s.loaded.map((m) => m.id).join(", ") || "none") + ".");
    return;
  }
  const hint = document.getElementById("rm-hint");
  if (hint) {
    hint.textContent = "Models load when a task needs them and unload after " +
      s.unload_idle_s + "s idle (max " + s.max_concurrent + " at once), so memory stays free.";
  }
  if (!s.loaded.length) {
    setText("All models idle-unloaded \u2014 memory fully free. The next task loads its model on demand.");
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
  fpLine();
}
Jarvis.on("rm_state", (d) => renderRmStatus(d.payload));
// ---- phonetic dictionary (spec 29, section 3.3) ----
const vocabTable = document.getElementById("vocab-table");
const vocabHint = document.getElementById("vocab-hint");

function vocabRow(m) {
  const row = document.createElement("div");
  row.className = "vocab-row";
  row.setAttribute("role", "row");
  const heard = document.createElement("input");
  heard.type = "text";
  heard.className = "vocab-heard";
  heard.placeholder = "cube control, koob ctl";
  heard.spellcheck = false;
  heard.value = Array.isArray(m.heard_as) ? m.heard_as.join(", ") : "";
  const word = document.createElement("input");
  word.type = "text";
  word.className = "vocab-word";
  word.placeholder = "kubectl";
  word.spellcheck = false;
  word.value = m.word || "";
  const del = document.createElement("button");
  del.type = "button";
  del.className = "icon-btn vocab-del";
  del.title = "Remove mapping";
  del.setAttribute("aria-label", "Remove mapping");
  del.innerHTML = '<svg class="ic"><use href="#i-x"/></svg>';
  del.addEventListener("click", () => row.remove());
  row.appendChild(heard);
  row.appendChild(word);
  row.appendChild(del);
  return row;
}

function renderVocab(mappings) {
  if (!vocabTable) return;
  Array.prototype.slice.call(vocabTable.querySelectorAll(".vocab-row")).forEach((r) => r.remove());
  const list = Array.isArray(mappings) && mappings.length ? mappings : [{}];
  list.forEach((m) => vocabTable.appendChild(vocabRow(m || {})));
}

function collectVocab() {
  if (!vocabTable) return [];
  const out = [];
  Array.prototype.slice.call(vocabTable.querySelectorAll(".vocab-row")).forEach((r) => {
    const word = (r.querySelector(".vocab-word").value || "").trim();
    const heard = (r.querySelector(".vocab-heard").value || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (word && heard.length) out.push({ word: word, heard_as: heard });
  });
  return out;
}

Jarvis.on("vocabulary", (d) => {
  const p = d.payload || {};
  renderVocab(p.mappings);
  if (p.saved) {
    if (vocabHint) {
      vocabHint.textContent = "Dictionary saved (" + ((p.mappings || []).length) + " mapping(s)).";
      vocabHint.classList.add("ok");
    }
    note.textContent = "Dictionary saved.";
    note.classList.add("ok");
  }
});

const vocabAdd = document.getElementById("vocab-add");
if (vocabAdd) {
  vocabAdd.addEventListener("click", () => {
    const row = vocabRow({});
    if (vocabTable) vocabTable.appendChild(row);
    const w = row.querySelector(".vocab-word");
    if (w) w.focus();
  });
}
const vocabSaveBtn = document.getElementById("vocab-save");
if (vocabSaveBtn) {
  vocabSaveBtn.addEventListener("click", () => {
    if (vocabHint) {
      vocabHint.textContent = "Saving dictionary...";
      vocabHint.classList.remove("ok");
    }
    Jarvis.vocabularySave(collectVocab());
  });
}

// ---- dictation history (spec 29, section 3.2) ----
const dictHist = document.getElementById("dict-history");

function renderHistory(entries) {
  if (!dictHist) return;
  dictHist.innerHTML = "";
  if (!entries || !entries.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No dictations yet.";
    dictHist.appendChild(p);
    return;
  }
  entries.slice(0, 100).forEach((e) => {
    const row = document.createElement("div");
    row.className = "dict-row";
    const meta = document.createElement("span");
    meta.className = "dict-meta";
    const t = e.ts ? new Date(e.ts * 1000) : null;
    meta.textContent =
      (t ? t.toLocaleString() : "") +
      (e.app ? " \u00b7 " + e.app : "") +
      (e.injected === false ? " \u00b7 not injected" : "");
    const txt = document.createElement("span");
    txt.className = "dict-text";
    txt.textContent = e.text || "";
    row.appendChild(meta);
    row.appendChild(txt);
    dictHist.appendChild(row);
  });
}

Jarvis.on("dictation_history", (d) => renderHistory((d.payload || {}).entries));
Jarvis.on("dictation.result", () => Jarvis.dictationHistory());
const dictRefresh = document.getElementById("dict-history-refresh");
if (dictRefresh) dictRefresh.addEventListener("click", () => Jarvis.dictationHistory());


// ---- developer agent hook relay, jarvis-hook (spec 29, section 4) ----
function renderHookState(s) {
  const cs = document.getElementById('hook-claude-state');
  const as = document.getElementById('hook-agy-state');
  const rs = document.getElementById('hook-relay-state');
  if (cs) cs.textContent = s.installed_claude
    ? 'Installed - Claude Code relays sessions, file diffs and approvals to Jarvis.'
    : 'Not installed.';
  if (as) as.textContent = s.installed_agy
    ? 'Installed - Antigravity relays sessions and events to Jarvis.'
    : 'Not installed.';
  if (rs) {
    const st = s.stats || {};
    rs.textContent =
      (s.listening ? 'Listening on ' + s.pipe : 'Pipe starting: ' + s.pipe) +
      ' - ' + (st.events || 0) + ' event(s), ' +
      (st.approvals || 0) + ' approval card(s), ' +
      (st.auto_allowed || 0) + ' auto-allowed, ' +
      (st.denied || 0) + ' denied.';
  }
}
Jarvis.on('hook_state', (d) => renderHookState(d.payload || {}));
Jarvis.on('hook_install', (d) => {
  const p = d.payload || {};
  if (!p.ok) {
    const el = document.getElementById('hook-' + (p.target || 'claude') + '-state');
    if (el) el.textContent = 'Install failed: ' + (p.error || 'unknown error');
  }
  Jarvis.hookState();
});
Jarvis.on('hook_uninstall', () => Jarvis.hookState());
for (const t of ['claude', 'agy']) {
  const ib = document.getElementById('hook-' + t + '-install');
  const ub = document.getElementById('hook-' + t + '-uninstall');
  if (ib) ib.addEventListener('click', () => Jarvis.hookInstall(t));
  if (ub) ub.addEventListener('click', () => Jarvis.hookUninstall(t));
}
