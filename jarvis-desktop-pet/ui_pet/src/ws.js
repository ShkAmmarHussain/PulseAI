// Shared WS client for Jarvis UI windows
window.Jarvis = (function () {
  const URL = "ws://127.0.0.1:8765/ws";
  let ws = null;
  let handlers = {};
  let retry = 0;
  const queue = [];

  function connect() {
    try {
      ws = new WebSocket(URL);
    } catch (e) {
      setTimeout(connect, 2000);
      return;
    }
    ws.onopen = () => {
      retry = 0;
      document.dispatchEvent(new CustomEvent("jarvis:connected"));
      while (queue.length) ws.send(queue.shift());
    };
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        const fns = handlers[data.topic || data.type];
        if (Array.isArray(fns)) fns.forEach((fn) => fn(data));
        if (handlers["*"]) handlers["*"].forEach((fn) => fn(data));
      } catch (err) {}
    };
    ws.onclose = () => {
      document.dispatchEvent(new CustomEvent("jarvis:disconnected"));
      retry++;
      setTimeout(connect, Math.min(1000 * retry, 5000));
    };
    ws.onerror = () => ws.close();
  }

  function send(obj) {
    const s = JSON.stringify(obj);
    if (ws && ws.readyState === 1) ws.send(s);
    else queue.push(s);
  }

  connect();
  const providerName = (p) =>
    p === "openai" ? "OpenAI" : p === "anthropic" ? "Anthropic Claude" : "LM Studio";
  const autoRouteDetail = (p) =>
    p === "openai"
      ? "Auto-routed: Heavy tasks (GPT-4o) \u2022 Fast responses (GPT-4o-mini) \u2022 Vision (GPT-4o)"
      : p === "anthropic"
      ? "Auto-routed: Heavy tasks (Claude 3.7 Sonnet) \u2022 Fast responses (Claude 3.5 Haiku) \u2022 Vision (Claude 3.5 Sonnet)"
      : "Auto-routed across loaded models: coder \u2192 planning & tools \u2022 VL \u2192 vision \u2022 small \u2192 memory";
  // formatted provider status card (spec 33, section 5.1) - replaces raw model dumps
  function renderConnectCard(el, p, fallbackProvider) {
    if (!el) return;
    if (!p) {
      el.hidden = true;
      return;
    }
    const prov = p.provider || fallbackProvider || "lm_studio";
    const name = providerName(prov);
    el.className = "model-connect-card " + (p.ok ? "success" : "error");
    el.textContent = "";
    const head = document.createElement("div");
    head.className = "mcc-head";
    const dot = document.createElement("span");
    dot.className = "mcc-dot";
    head.appendChild(dot);
    head.appendChild(document.createTextNode(p.ok ? name + " Ready" : name + " connection failed"));
    el.appendChild(head);
    const detail = document.createElement("div");
    detail.className = "mcc-detail";
    detail.textContent = p.ok
      ? autoRouteDetail(prov)
      : p.error || "Unknown error";
    el.appendChild(detail);
    if (p.ok && Array.isArray(p.models) && p.models.length) {
      const box = document.createElement("div");
      box.className = "mcc-models";
      p.models.slice(0, 8).forEach((m) => {
        const chip = document.createElement("span");
        chip.className = "mcc-model";
        chip.textContent = m;
        box.appendChild(chip);
      });
      if (p.models.length > 8) {
        const more = document.createElement("span");
        more.className = "mcc-model";
        more.textContent = "+" + (p.models.length - 8) + " more";
        box.appendChild(more);
      }
      el.appendChild(box);
    }
    el.hidden = false;
  }
  return {
    on: (topic, fn) => {
      (handlers[topic] = handlers[topic] || []).push(fn);
    },
    send,
    providerName,
    renderConnectCard,
    text: (text, cid) => send({ type: "text_input", payload: { text }, correlation_id: cid }),
    getSettings: () => send({ type: "get_settings" }),
    saveSettings: (payload) => send({ type: "save_settings", payload }),
    approval: (allow, payload, cid) =>
      send({ type: "approval_response", payload: Object.assign({ allow }, payload), correlation_id: cid }),
    testLm: (url, provider, api_key) =>
      send({ type: "test_lm_studio", payload: { url, provider, api_key } }),
    setPet: (enabled) => send({ type: "set_pet", payload: { enabled } }),
    voiceListen: (on) => send({ type: "voice_listen", payload: { on: !!on } }),
    voiceWake: (enabled) => send({ type: "voice_wake", payload: { enabled: !!enabled } }),
    voiceDevices: () => send({ type: "voice_devices" }),
    voiceDevice: (device) => send({ type: "voice_device", payload: { device } }),
    wakeTest: (seconds) => send({ type: "wake_test", payload: { seconds } }),
    ttsTest: (voice, text) => send({ type: "tts_test", payload: { voice, text } }),
    autostart: (enabled) => send({ type: "autostart", payload: { enabled: !!enabled } }),
    autostartState: () => send({ type: "autostart_state" }),
    rmState: () => send({ type: "rm_state" }),
    dictation: (action, text) => send({ type: "dictation", payload: { action, text } }),
    dictationHistory: (limit) => send({ type: "dictation_history", payload: { limit: limit || 100 } }),
    vocabulary: () => send({ type: "vocabulary_get" }),
    vocabularySave: (mappings) => send({ type: "vocabulary_save", payload: { mappings } }),
    hookState: () => send({ type: "hook_state" }),
    hookInstall: (target) => send({ type: "hook_install", payload: { target } }),
    hookUninstall: (target) => send({ type: "hook_uninstall", payload: { target } }),
    hookTerminal: (pid) => send({ type: "hook_terminal", payload: { pid } }),
    fileIngest: (paths) => send({ type: "file_ingest", payload: { paths } }),
  };
})();