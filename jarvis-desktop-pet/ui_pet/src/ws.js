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
  return {
    on: (topic, fn) => {
      (handlers[topic] = handlers[topic] || []).push(fn);
    },
    send,
    text: (text, cid) => send({ type: "text_input", payload: { text }, correlation_id: cid }),
    getSettings: () => send({ type: "get_settings" }),
    saveSettings: (payload) => send({ type: "save_settings", payload }),
    approval: (allow, payload, cid) =>
      send({ type: "approval_response", payload: Object.assign({ allow }, payload), correlation_id: cid }),
    testLm: (url) => send({ type: "test_lm_studio", payload: { url } }),
    setPet: (enabled) => send({ type: "set_pet", payload: { enabled } }),
    voiceListen: (on) => send({ type: "voice_listen", payload: { on: !!on } }),
    voiceWake: (enabled) => send({ type: "voice_wake", payload: { enabled: !!enabled } }),
    voiceDevices: () => send({ type: "voice_devices" }),
    voiceDevice: (device) => send({ type: "voice_device", payload: { device } }),
    ttsTest: (voice, text) => send({ type: "tts_test", payload: { voice, text } }),
  };
})();