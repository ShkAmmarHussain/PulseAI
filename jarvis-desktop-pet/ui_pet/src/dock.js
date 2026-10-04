/* Top-edge dock companion (spec 29, section 5.1).
   Active only when this window was opened as index.html?mode=dock;
   in the main window this file exits immediately. */
(function () {
  const island = document.getElementById("dock-island");
  if (!island) return;
  if (!/[?&]mode=dock/.test(location.search)) return;
  document.body.classList.add("dock-mode");

  const ta = window.__TAURI__;
  const win = ta && ta.window ? ta.window.appWindow : null;
  const COLLAPSED = [220, 38];
  const EXPANDED = [460, 120];

  async function resizeDock(w, h) {
    if (!win || !ta.dpi) return;
    try {
      await win.setSize(new ta.dpi.LogicalSize(w, h));
      const mon = await win.currentMonitor();
      if (mon) {
        const x = Math.round(mon.position.x + (mon.size.width - w * mon.scaleFactor) / 2);
        await win.setPosition(new ta.dpi.PhysicalPosition(x, mon.position.y));
      }
    } catch (e) { /* monitor unavailable */ }
  }

  let expanded = false;
  function setExpanded(on) {
    if (on === expanded) return;
    expanded = on;
    island.classList.toggle("expanded", on);
    const size = on ? EXPANDED : COLLAPSED;
    resizeDock(size[0], size[1]);
    if (on && window.Earcons && window.Earcons.play) window.Earcons.play("snd_dock_peek");
  }
  island.addEventListener("mouseenter", () => setExpanded(true));
  island.addEventListener("mouseleave", () => setExpanded(false));

  const dot = document.getElementById("dock-dot");
  const status = document.getElementById("dock-status");
  const task = document.getElementById("dock-task");
  let resetTimer = null;
  function setTask(label, state) {
    task.textContent = label;
    status.textContent = label;
    island.dataset.state = state;
    clearTimeout(resetTimer);
    if (state === "done" || state === "bad" || state === "warn") {
      resetTimer = setTimeout(() => {
        task.textContent = "Idle";
        status.textContent = "Ready";
        island.dataset.state = "idle";
      }, state === "warn" ? 8000 : 4000);
    }
  }
  document.addEventListener("jarvis:connected", () => {
    dot.classList.add("on");
    if (island.dataset.state === "idle") status.textContent = "Ready";
  });
  document.addEventListener("jarvis:disconnected", () => {
    dot.classList.remove("on");
    status.textContent = "Reconnecting\u2026";
  });

  if (window.Jarvis) Jarvis.on("*", (d) => {
    const t = d.topic || d.type;
    const p = d.payload || {};
    if (t === "ui.chat" && p.role === "user") setTask("Working on it\u2026", "busy");
    else if (t === "tool.result") setTask(p.ok === false ? "Action failed" : "Done", p.ok === false ? "bad" : "done");
    else if (t === "ui.approval") setTask("Needs approval", "warn");
    else if (t === "ui.approval_cancelled") setTask("Approval expired", "warn");
    else if (t === "dictation.start") setTask("Listening\u2026", "busy");
    else if (t === "dictation.stop") setTask("Transcribing\u2026", "busy");
    else if (t === "dictation.result") setTask("Ready", "idle");
    else if (t === "agent.hook.session") {
      const st = p.status || "update";
      setTask("Coding " + st + (p.agent ? " \u2014 " + p.agent : ""),
        st === "running" ? "busy" : st === "waiting" ? "warn" : "idle");
    }
  });

  const micBtn = document.getElementById("top-mic");
  const mic = document.getElementById("dock-mic");
  if (mic) mic.addEventListener("click", () => { if (micBtn) micBtn.click(); });
  function invokeCmd(cmd) {
    if (ta && ta.tauri) ta.tauri.invoke(cmd);
  }
  const chatBtn = document.getElementById("dock-chat");
  if (chatBtn) chatBtn.addEventListener("click", () => invokeCmd("open_chat"));
  const settingsBtn = document.getElementById("dock-settings");
  if (settingsBtn) settingsBtn.addEventListener("click", () => invokeCmd("open_settings"));

  // ---- drag-and-drop ingestion target (spec 29, section 5.2) ----
  const toast = document.getElementById("dock-toast");
  let toastTimer = null;
  function base(p) {
    const parts = String(p).split(/[\\/]/);
    return parts[parts.length - 1] || p;
  }
  function handlePaths(paths) {
    if (!paths || !paths.length) return;
    island.classList.remove("dropping");
    const label = "Inspecting " + base(paths[0]) +
      (paths.length > 1 ? " +" + (paths.length - 1) : "") + "\u2026";
    setTask(label, "busy");
    if (toast) {
      toast.hidden = false;
      toast.textContent = label;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
    }
    if (window.Jarvis && Jarvis.fileIngest) Jarvis.fileIngest(paths);
  }
  ["dragenter", "dragover"].forEach((ev) =>
    island.addEventListener(ev, (e) => { e.preventDefault(); island.classList.add("dropping"); }));
  island.addEventListener("dragleave", (e) => {
    if (e.target === island) island.classList.remove("dropping");
  });
  island.addEventListener("drop", (e) => {
    e.preventDefault();
    island.classList.remove("dropping");
    const files = e.dataTransfer ? Array.from(e.dataTransfer.files || []) : [];
    handlePaths(files.map((f) => f.path || f.name).filter(Boolean));
  });
  if (win && win.listen) {
    win.listen("tauri://file-drop-hover", () => island.classList.add("dropping")).catch(() => {});
    win.listen("tauri://file-drop-cancelled", () => island.classList.remove("dropping")).catch(() => {});
    win.listen("tauri://file-drop", (e) => handlePaths(e.payload || [])).catch(() => {});
  }
})();
