/* Standalone top-edge Dynamic Island (doc 30, section 5.2).
   Replaces the old index.html?mode=dock hack: this page IS the dock. */
(function () {
  const island = document.getElementById("dynamic-island");
  if (!island) return;

  const ta = window.__TAURI__;
  const win = ta && ta.window ? ta.window.appWindow : null;
  const COLLAPSED = [240, 36];
  const EXPANDED = [460, 150];

  async function resizeDock(w, h) {
    if (!win) return;
    const dpi = ta.dpi || ta.window;
    if (!dpi || !dpi.LogicalSize) return;
    try {
      await win.setSize(new dpi.LogicalSize(w, h));
      const mon = await (typeof win.currentMonitor === "function"
        ? win.currentMonitor()
        : ta.window.currentMonitor());
      if (mon) {
        const x = Math.round(mon.position.x + (mon.size.width - w * mon.scaleFactor) / 2);
        await win.setPosition(new dpi.PhysicalPosition(x, mon.position.y));
      }
    } catch (e) { /* monitor unavailable */ }
  }

  let expanded = false;
  function setExpanded(on) {
    if (on === expanded) return;
    expanded = on;
    island.classList.toggle("expanded", on);
    island.classList.toggle("island-collapsed", !on);
    const size = on ? EXPANDED : COLLAPSED;
    resizeDock(size[0], size[1]);
  }
  island.addEventListener("mouseenter", () => setExpanded(true));
  island.addEventListener("mouseleave", () => setExpanded(false));

  // ---- status + task headline -------------------------------------------
  const dot = document.getElementById("island-dot");
  const headline = document.getElementById("island-headline");
  const subtext = document.getElementById("island-subtext");
  const diffBadge = document.getElementById("island-diff");
  let resetTimer = null;

  function setTask(label, state, sub) {
    headline.textContent = label;
    if (subtext) subtext.textContent = sub || label;
    island.dataset.state = state;
    clearTimeout(resetTimer);
    if (state === "done" || state === "bad" || state === "warn") {
      resetTimer = setTimeout(() => {
        headline.textContent = "Jarvis Standing By";
        if (subtext) subtext.textContent = "Ready for instructions";
        island.dataset.state = "idle";
      }, state === "warn" ? 8000 : 4000);
    }
  }

  document.addEventListener("jarvis:connected", () => {
    if (dot) dot.classList.add("on");
    if (island.dataset.state === "idle") headline.textContent = "Jarvis Standing By";
  });
  document.addEventListener("jarvis:disconnected", () => {
    if (dot) dot.classList.remove("on");
    headline.textContent = "Reconnecting\u2026";
  });

  // ---- live +N -M diff badge (doc 30, section 5 / acceptance 8) --------
  let diffTimer = null;
  function showDiff(added, removed) {
    if (!diffBadge) return;
    diffBadge.textContent = "+" + (added || 0) + " -" + (removed || 0);
    diffBadge.hidden = false;
    clearTimeout(diffTimer);
    diffTimer = setTimeout(() => { diffBadge.hidden = true; }, 20000);
  }

  if (window.Jarvis) {
    Jarvis.on("*", (d) => {
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
      } else if (t === "agent.hook.diff") {
        setTask("File edited" + (p.file ? " \u2014 " + p.file.split(/[\\/]/).pop() : ""),
          "busy", "+" + (p.added || 0) + " -" + (p.removed || 0) + " lines changed");
        showDiff(p.added, p.removed);
      }
    });
    Jarvis.getSettings();
    Jarvis.on("settings", (d) => {
      const rt = (((d || {}).payload || {}).config || {}).runtime || {};
      petEnabled = rt.pet_enabled !== false;
    });
    Jarvis.on("settings_saved", (d) => {
      const rt = (((d || {}).payload || {}).config || {}).runtime || {};
      petEnabled = rt.pet_enabled !== false;
    });
    // saves made in other windows only broadcast ui.state {settings_saved}
    Jarvis.on("ui.state", (d) => {
      if ((d.payload || {}).settings_saved) Jarvis.getSettings();
    });
  }

  // ---- drawer controls ---------------------------------------------------
  function invokeCmd(cmd, args) {
    if (ta && ta.tauri) ta.tauri.invoke(cmd, args);
  }
  let micOn = false;
  const micBtn = document.getElementById("island-mic-btn");
  if (micBtn) micBtn.onclick = () => {
    if (!window.Jarvis) return;
    micOn = !micOn;
    micBtn.classList.toggle("rec", micOn);
    Jarvis.voiceListen(micOn);
  };
  if (window.Jarvis) Jarvis.on("ui.voice_state", (d) => {
    const st = ((d || {}).payload || {}).state || "idle";
    if (micBtn) {
      micBtn.classList.toggle("rec", st === "listening");
      micBtn.classList.toggle("busy", st === "transcribing");
    }
    micOn = st === "listening";
    if (st === "listening") setTask("Listening\u2026", "busy");
    else if (st === "transcribing") setTask("Transcribing\u2026", "busy");
    else if (island.dataset.state === "busy") setTask("Jarvis Standing By", "idle");
  });

  const chatBtn = document.getElementById("island-chat-btn");
  if (chatBtn) chatBtn.onclick = () => invokeCmd("open_chat");

  let petEnabled = true;
  const petBtn = document.getElementById("island-pet-btn");
  if (petBtn) petBtn.onclick = () => {
    if (!ta || !ta.tauri) return;
    ta.tauri.invoke("set_companion", { mode: "pet" });
    ta.tauri.invoke("set_pet", { visible: petEnabled });
  };

  // ---- drag-and-drop ingestion (doc 30, section 5) ----------------------
  const dropzone = document.getElementById("island-dropzone");
  function base(p) {
    const parts = String(p).split(/[\\/]/);
    return parts[parts.length - 1] || p;
  }
  function handlePaths(paths) {
    if (!paths || !paths.length) return;
    if (dropzone) dropzone.hidden = true;
    island.classList.remove("dropping");
    const label = "Inspecting " + base(paths[0]) +
      (paths.length > 1 ? " +" + (paths.length - 1) : "") + "\u2026";
    setTask(label, "busy");
    if (window.Jarvis && Jarvis.fileIngest) Jarvis.fileIngest(paths);
  }
  ["dragenter", "dragover"].forEach((ev) =>
    island.addEventListener(ev, (e) => {
      e.preventDefault();
      island.classList.add("dropping");
      if (dropzone) dropzone.hidden = false;
    }));
  island.addEventListener("dragleave", (e) => {
    if (e.target === island) {
      island.classList.remove("dropping");
      if (dropzone) dropzone.hidden = true;
    }
  });
  island.addEventListener("drop", (e) => {
    e.preventDefault();
    island.classList.remove("dropping");
    if (dropzone) dropzone.hidden = true;
    const files = e.dataTransfer ? Array.from(e.dataTransfer.files || []) : [];
    handlePaths(files.map((f) => f.path || f.name).filter(Boolean));
  });
  if (win && win.listen) {
    win.listen("tauri://file-drop-hover", () => {
      island.classList.add("dropping");
      if (dropzone) dropzone.hidden = false;
    }).catch(() => {});
    win.listen("tauri://file-drop-cancelled", () => {
      island.classList.remove("dropping");
      if (dropzone) dropzone.hidden = true;
    }).catch(() => {});
    win.listen("tauri://file-drop", (e) => handlePaths(e.payload || [])).catch(() => {});
  }

  window.__DOCK_READY = 1;
})();
