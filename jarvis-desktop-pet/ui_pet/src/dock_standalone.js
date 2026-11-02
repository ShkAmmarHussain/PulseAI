/* Standalone top-edge Dynamic Island (doc 30, section 5; spec 34 section 3).
   Replaces the old index.html?mode=dock hack: this page IS the dock.

   Sizes: hidden wake strip 240x6 (after a quiet spell), compact pill 240x36,
   expanded 460 wide with a height measured from the visible card. Expanded
   shows a Home / Chat / + header and one card per state: overview, approval,
   question, result, error, chat. Approvals and questions pin the island open
   until answered; results and errors pin it for a few seconds. */
(function () {
  const island = document.getElementById("dynamic-island");
  if (!island) return;

  const ta = window.__TAURI__;
  const win = ta && ta.window ? ta.window.appWindow : null;
  const COLLAPSED = [240, 36];
  const HIDDEN = [240, 6];
  const DROP = [320, 72];
  const EXPANDED_W = 460;
  const EXPANDED_MIN_H = 150;
  const IDLE_HIDE_MS = 12000;
  const RESULT_MS = 6000;
  const ERROR_MS = 10000;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s)
    .replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const trunc = (s, n) => { s = String(s || "").trim(); return s.length > n ? s.slice(0, n - 1) + "\u2026" : s; };

  let lastSize = "";
  async function resizeDock(w, h) {
    const key = w + "x" + h;
    if (key === lastSize) return;
    lastSize = key;
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

  // ---- view state ----------------------------------------------------------
  let hovered = false;
  let expanded = false;
  let view = "home";          // header tab: home | chat
  let pendingApproval = null; // { payload, cid }
  let pendingQuestion = null; // { title, options, cid, choice }
  let flash = null;           // { card: "result" | "error", until }
  let flashTimer = null;
  let chatPinned = false;     // composer focused or holding a draft
  let dropping = false;

  function homeCard() {
    if (pendingApproval) return "approval";
    if (pendingQuestion) return "question";
    if (flash && flash.until > Date.now()) return flash.card;
    return "overview";
  }
  function currentCard() { return view === "chat" ? "chat" : homeCard(); }
  function pinned() {
    return !!(pendingApproval || pendingQuestion || chatPinned ||
      (flash && flash.until > Date.now()));
  }

  function sizeFor() {
    if (dropping) return DROP;
    if (expanded) {
      const h = Math.ceil(island.getBoundingClientRect().height);
      return [EXPANDED_W, Math.max(EXPANDED_MIN_H, h)];
    }
    if (island.classList.contains("island-hidden")) return HIDDEN;
    return COLLAPSED;
  }

  function render() {
    const card = currentCard();
    island.dataset.card = card;
    document.querySelectorAll(".island-tab[data-view]").forEach((b) => {
      const on = b.dataset.view === view;
      b.classList.toggle("on", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    const kbd = $("island-kbd");
    if (kbd) kbd.hidden = card !== "approval";
    const want = (hovered || pinned()) && !dropping;
    if (want !== expanded) {
      expanded = want;
      island.classList.toggle("expanded", want);
      island.classList.toggle("island-collapsed", !want);
    }
    if (want) wake();
    // measure after layout so the window fits the visible card
    requestAnimationFrame(() => { const s = sizeFor(); resizeDock(s[0], s[1]); });
    armIdle();
  }

  function setExpanded(on) {
    hovered = on;
    render();
  }
  // the width animates, which rewraps text: re-measure once it settles
  island.addEventListener("transitionend", (e) => {
    if (e.target === island && expanded) { const s = sizeFor(); resizeDock(s[0], s[1]); }
  });
  island.addEventListener("mouseenter", () => setExpanded(true));
  island.addEventListener("mouseleave", () => setExpanded(false));

  document.querySelectorAll(".island-tab[data-view]").forEach((b) => {
    b.addEventListener("click", () => {
      view = b.dataset.view;
      render();
      if (view === "chat") setTimeout(() => { const i = $("ichat-input"); if (i) i.focus(); }, 30);
    });
  });
  const newBtn = $("island-new");
  if (newBtn) newBtn.onclick = () => {
    chatLog = [];
    renderChat();
    view = "chat";
    render();
    setTimeout(() => { const i = $("ichat-input"); if (i) { i.value = ""; i.focus(); } }, 30);
  };

  // ---- hidden wake strip: a quiet island tucks into a 6px strip ------------
  let idleTimer = null;
  const diffBadge = $("island-diff");
  function wake() {
    if (island.classList.contains("island-hidden")) {
      island.classList.remove("island-hidden");
      if (!expanded) requestAnimationFrame(() => resizeDock(COLLAPSED[0], COLLAPSED[1]));
    }
  }
  function armIdle() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      const quiet = !hovered && !pinned() && !dropping && island.dataset.state === "idle" &&
        (!diffBadge || diffBadge.hidden);
      if (!quiet) { armIdle(); return; }
      island.classList.add("island-hidden");
      resizeDock(HIDDEN[0], HIDDEN[1]);
    }, IDLE_HIDE_MS);
  }

  // ---- status + task headline -------------------------------------------
  const dot = $("island-dot");
  const headline = $("island-headline");
  const subtext = $("island-subtext");
  let resetTimer = null;

  function setTask(label, state, sub) {
    headline.textContent = label;
    if (subtext) subtext.textContent = sub || label;
    island.dataset.state = state;
    wake();
    armIdle();
    clearTimeout(resetTimer);
    if (state === "done" || state === "bad" || state === "warn") {
      resetTimer = setTimeout(() => {
        headline.textContent = "Jarvis Standing By";
        if (subtext) subtext.textContent = "Ready for instructions";
        island.dataset.state = "idle";
        armIdle();
      }, state === "warn" ? 8000 : 4000);
    }
  }

  document.addEventListener("jarvis:connected", () => {
    if (dot) dot.classList.add("on");
    if (island.dataset.state === "idle") headline.textContent = "Jarvis Standing By";
  });
  document.addEventListener("jarvis:reconnecting", (e) => {
    if (dot && dot.classList.contains("on")) return;
    const s = (e.detail || {}).seconds || 0;
    headline.textContent = s > 0 ? "Offline — retrying in " + s + "s" : "Reconnecting…";
  });  document.addEventListener("jarvis:disconnected", () => {
    if (dot) dot.classList.remove("on");
    headline.textContent = "Reconnecting\u2026";
    wake();
  });

  // ---- overview: live step list (current bright, past dim) ---------------
  const stepsEl = $("island-steps");
  let steps = [];
  function addStep(icon, text, opts) {
    steps.forEach((s) => { s.cur = false; });
    const last = steps[steps.length - 1];
    if (last && last.icon === icon && last.text === trunc(text, 70)) { renderSteps(); return; }
    steps.push({ icon: icon, text: trunc(text, 70), cur: !(opts && opts.past), bad: !!(opts && opts.bad) });
    if (steps.length > 4) steps = steps.slice(-4);
    renderSteps();
  }
  function settleSteps() {
    steps.forEach((s) => { s.cur = false; });
    renderSteps();
  }
  function renderSteps() {
    if (!stepsEl) return;
    stepsEl.innerHTML = steps.map((s) =>
      '<li class="island-step' + (s.cur ? " cur" : "") + (s.bad ? " bad" : "") + '">' +
      '<svg class="ic"><use href="#i-' + s.icon + '"/></svg><span>' + esc(s.text) + "</span></li>").join("");
    render();
  }

  // ---- live +N -M diff badge (doc 30, section 5 / acceptance 8) --------
  let diffTimer = null;
  function showDiff(added, removed) {
    if (!diffBadge) return;
    diffBadge.textContent = "+" + (added || 0) + " -" + (removed || 0);
    diffBadge.hidden = false;
    wake();
    clearTimeout(diffTimer);
    diffTimer = setTimeout(() => { diffBadge.hidden = true; }, 20000);
  }

  // ---- approval card (replaces the pet card while the island is the companion)
  const AT = window.ApprovalText;
  let approvalTick = null;
  function showApproval(d) {
    const pp = d.payload || {};
    pendingApproval = { payload: pp, cid: d.correlation_id };
    const fa = AT ? AT.friendlyAction(pp) : { title: "Run an action" };
    const band = AT ? AT.riskBand(pp.risk) : { cls: "med", label: "Unknown risk" };
    const act = (pp.action && typeof pp.action === "object" && pp.action) || {};
    const tgt = act.cmd || act.target || act.path || act.url || "";
    const extra = AT ? AT.extraMessage(pp) : "";
    $("ia-title").textContent = fa.title;
    const risk = $("ia-risk");
    risk.className = "ic-risk risk " + band.cls;
    risk.textContent = band.label;
    risk.title = pp.risk == null ? "Risk unknown" : "Risk " + pp.risk + "/10";
    const chip = $("ia-chip");
    chip.textContent = tgt;
    chip.hidden = !tgt;
    const ex = $("ia-extra");
    ex.textContent = extra;
    ex.hidden = !extra;
    // "Always" is a session grant, which only coding-agent hooks support
    $("ia-always").hidden = !pp.hook;
    ["ia-allow", "ia-deny", "ia-always"].forEach((id) => { $(id).disabled = false; });
    let left = Math.round(pp.timeout || 30);
    const timer = $("ia-timer");
    timer.textContent = left + "s";
    clearInterval(approvalTick);
    approvalTick = setInterval(() => {
      left -= 1;
      timer.textContent = Math.max(0, left) + "s";
      if (left <= 0) clearInterval(approvalTick);
    }, 1000);
    view = "home";
    addStep("shield", "Waiting for your OK: " + fa.title);
    setTask("Needs approval", "warn", fa.title);
    render();
  }
  function clearApproval() {
    if (!pendingApproval) return;
    pendingApproval = null;
    clearInterval(approvalTick);
    render();
  }
  function answer(allow, remember) {
    if (!pendingApproval || !window.Jarvis) return;
    const p = pendingApproval.payload;
    const extra = { action: p.action };
    if (remember) extra.remember = true;
    Jarvis.approval(allow, extra, pendingApproval.cid);
    ["ia-allow", "ia-deny", "ia-always"].forEach((id) => { $(id).disabled = true; });
    addStep(allow ? "check" : "x", allow ? "Allowed" : "Denied", { past: !allow });
    setTask(allow ? "Working on it\u2026" : "Denied", allow ? "busy" : "warn");
    clearApproval();
  }
  $("ia-allow").onclick = () => answer(true, false);
  $("ia-deny").onclick = () => answer(false, false);
  $("ia-always").onclick = () => answer(true, true);

  // ---- question / choose card (ui.question {title, options, correlation_id})
  function showQuestion(d) {
    const p = d.payload || {};
    const opts = (p.options || []).map((o) => (typeof o === "object" ? o : { label: String(o), value: o }));
    pendingQuestion = { title: p.title || p.question || "Jarvis has a question", options: opts, cid: d.correlation_id, choice: null };
    $("iq-title").textContent = pendingQuestion.title;
    const box = $("iq-options");
    box.innerHTML = "";
    opts.forEach((o, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "ic-option";
      b.setAttribute("role", "radio");
      b.setAttribute("aria-checked", "false");
      b.innerHTML = '<span class="ic-radio" aria-hidden="true"></span><span></span><kbd>' + (i + 1) + "</kbd>";
      b.children[1].textContent = o.label || String(o.value);
      b.onclick = () => pickOption(i);
      box.appendChild(b);
    });
    $("iq-confirm").disabled = true;
    view = "home";
    addStep("dots", pendingQuestion.title);
    setTask("Needs your answer", "warn", pendingQuestion.title);
    render();
  }
  function pickOption(i) {
    if (!pendingQuestion) return;
    pendingQuestion.choice = i;
    document.querySelectorAll("#iq-options .ic-option").forEach((b, j) => {
      b.classList.toggle("on", j === i);
      b.setAttribute("aria-checked", j === i ? "true" : "false");
    });
    $("iq-confirm").disabled = false;
  }
  function answerQuestion(skip) {
    if (!pendingQuestion) return;
    const q = pendingQuestion;
    const o = skip || q.choice == null ? null : q.options[q.choice];
    if (window.Jarvis) {
      Jarvis.send({ type: "question_response",
        payload: { choice: o ? (o.value != null ? o.value : o.label) : null, skipped: !o },
        correlation_id: q.cid });
    }
    pendingQuestion = null;
    addStep(o ? "check" : "x", o ? "Answered: " + (o.label || o.value) : "Skipped", { past: true });
    render();
  }
  $("iq-confirm").onclick = () => answerQuestion(false);
  $("iq-skip").onclick = () => answerQuestion(true);

  // ---- result / error cards ---------------------------------------------
  function showFlash(card, ms) {
    flash = { card: card, until: Date.now() + ms };
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => { flash = null; render(); }, ms + 50);
    if (view !== "chat") view = "home";
    render();
  }
  function friendlyStep(s) {
    if (!s) return "";
    const fa = AT ? AT.friendlyAction({ action: s }) : { title: s.action || "Step" };
    return fa.title;
  }
  function showResult(p) {
    const lines = String(p.summary || "").split(/\n+/).map((l) => l.trim()).filter(Boolean);
    $("ir-title").textContent = trunc(lines[0] || "Done", 80);
    const rows = (p.steps || []).map(friendlyStep).filter(Boolean);
    const extra = lines.slice(1);
    const ul = $("ir-rows");
    ul.innerHTML = "";
    rows.concat(extra).slice(0, 3).forEach((r) => {
      const li = document.createElement("li");
      li.textContent = trunc(r, 90);
      ul.appendChild(li);
    });
    ul.hidden = !ul.children.length;
    showFlash("result", RESULT_MS);
  }
  let lastUserText = "";
  function showError(cause, title) {
    $("ie-title").textContent = title || "That didn\u2019t work";
    $("ie-cause").textContent = trunc(cause || "Something went wrong.", 140);
    $("ie-retry").hidden = !lastUserText;
    showFlash("error", ERROR_MS);
  }
  $("ir-close").onclick = () => { flash = null; render(); };
  $("ir-open").onclick = () => { flash = null; invokeCmd("open_chat"); render(); };
  $("ie-details").onclick = () => { flash = null; invokeCmd("open_tab", { tab: "activity" }); render(); };
  $("ie-retry").onclick = () => {
    flash = null;
    if (lastUserText && window.Jarvis) Jarvis.text(lastUserText);
    render();
  };

  // ---- inline chat --------------------------------------------------------
  let chatLog = [];
  const LONG_REPLY = 280;
  function renderChat() {
    const log = $("ichat-log");
    if (!log) return;
    if (!chatLog.length) {
      log.innerHTML = '<p class="ichat-empty">Ask anything. Long answers open in the window.</p>';
    } else {
      log.innerHTML = "";
      chatLog.slice(-3).forEach((m) => {
        const el = document.createElement("div");
        el.className = "ichat-msg " + (m.role === "user" ? "user" : "assistant");
        const long = m.role !== "user" && m.text.length > LONG_REPLY;
        el.textContent = long ? trunc(m.text, LONG_REPLY) : m.text;
        if (long) {
          const more = document.createElement("button");
          more.type = "button";
          more.className = "ichat-more";
          more.textContent = "Continue in window";
          more.onclick = () => invokeCmd("open_chat");
          el.appendChild(more);
        }
        log.appendChild(el);
      });
    }
    render();
  }
  const chatForm = $("ichat-form");
  const chatInput = $("ichat-input");
  if (chatForm) chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = (chatInput.value || "").trim();
    if (!text || !window.Jarvis) return;
    Jarvis.text(text);
    chatInput.value = "";
    chatPinned = document.activeElement === chatInput;
    render();
  });
  if (chatInput) {
    chatInput.addEventListener("focus", () => { chatPinned = true; render(); });
    chatInput.addEventListener("blur", () => { chatPinned = !!chatInput.value.trim(); render(); });
  }

  // ---- keyboard: Y / N on approvals, 1-9 on questions, Esc collapses ------
  document.addEventListener("keydown", (e) => {
    const typing = e.target && e.target.tagName === "INPUT";
    const card = currentCard();
    if (card === "approval" && !typing) {
      if (e.key === "y" || e.key === "Y") { e.preventDefault(); answer(true, false); }
      else if (e.key === "n" || e.key === "N") { e.preventDefault(); answer(false, false); }
    } else if (card === "question" && !typing && /^[1-9]$/.test(e.key)) {
      pickOption(Number(e.key) - 1);
    } else if (card === "question" && e.key === "Enter" && pendingQuestion && pendingQuestion.choice != null) {
      answerQuestion(false);
    }
    if (e.key === "Escape") {
      if (typing) chatInput.blur();
      chatPinned = false;
      flash = null;
      view = "home";
      render();
    }
  });

  // ---- backend events -----------------------------------------------------
  if (window.Jarvis) {
    Jarvis.on("*", (d) => {
      const t = d.topic || d.type;
      const p = d.payload || {};
      if (t === "ui.chat" && p.role === "user") {
        lastUserText = p.text || lastUserText;
        steps = [];
        addStep("chat", "You asked: " + (p.text || ""), { past: true });
        addStep("dots", "Thinking\u2026");
        setTask("Working on it\u2026", "busy");
      } else if (t === "tool.result") {
        (p.steps || []).slice(0, 2).forEach((s) => addStep("bolt", friendlyStep(s), { past: true }));
        addStep(p.ok === false ? "x" : "check", p.ok === false ? "Failed" : "Done", { past: true, bad: p.ok === false });
        setTask(p.ok === false ? "Action failed" : "Done", p.ok === false ? "bad" : "done");
        if (p.ok === false) {
          const why = String(p.summary || "").split(/\n+/).find((l) => /fail/i.test(l)) || p.summary;
          showError(String(why || "").replace(/^Failed:\s*/i, ""));
        } else {
          showResult(p);
        }
      }
      else if (t === "ui.approval") showApproval(d);
      else if (t === "ui.approval_cancelled") {
        if (pendingApproval && String(pendingApproval.cid) === String(d.correlation_id)) {
          addStep("x", "Approval expired", { past: true });
          clearApproval();
        }
        setTask("Approval expired", "warn");
      }
      else if (t === "ui.question") showQuestion(d);
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
        addStep("file", "Edited " + (p.file ? p.file.split(/[\\/]/).pop() : "a file") +
          " +" + (p.added || 0) + " -" + (p.removed || 0), { past: true });
        showDiff(p.added, p.removed);
      }
    });
    // answered here or elsewhere: the outcome arrives as ui.chat on the same cid
    Jarvis.on("ui.chat", (d) => {
      const p = d.payload || {};
      if (pendingApproval && d.correlation_id && String(pendingApproval.cid) === String(d.correlation_id)) clearApproval();
      if (p.text && (p.role === "user" || p.role === "assistant")) {
        chatLog.push({ role: p.role, text: String(p.text) });
        if (chatLog.length > 20) chatLog = chatLog.slice(-20);
        if (p.role === "assistant") { addStep("chat", "Replied", { past: true }); settleSteps(); }
        renderChat();
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
  const micBtn = $("island-mic-btn");
  if (micBtn) micBtn.onclick = () => {
    if (!window.Jarvis) return;
    micOn = !micOn;
    micBtn.classList.toggle("rec", micOn);
    Jarvis.voiceListen(micOn);
  };
  if (window.Jarvis) Jarvis.on("ui.voice_state", (d) => {
    const pl = (d || {}).payload || {};
    const st = pl.state || "idle";
    if (micBtn) {
      micBtn.classList.toggle("rec", st === "listening");
      micBtn.classList.toggle("busy", st === "transcribing");
    }
    micOn = st === "listening";
    if (st === "listening") setTask("Listening\u2026", "busy");
    else if (st === "transcribing") setTask("Transcribing\u2026", "busy");
    else if (st === "error") showError(pl.error || "The microphone isn\u2019t available.", "Voice stopped");
    else if (island.dataset.state === "busy") setTask("Jarvis Standing By", "idle");
  });

  const chatBtn = $("island-chat-btn");
  if (chatBtn) chatBtn.onclick = () => invokeCmd("open_chat");

  let petEnabled = true;
  const petBtn = $("island-pet-btn");
  if (petBtn) petBtn.onclick = () => {
    if (!ta || !ta.tauri) return;
    ta.tauri.invoke("set_companion", { mode: "pet" });
    ta.tauri.invoke("set_pet", { visible: petEnabled });
  };

  // ---- drag-and-drop ingestion (doc 30, section 5) ----------------------
  // the island swells and the character "catches" the file
  const dropzone = $("island-dropzone");
  function setDropping(on) {
    if (on === dropping) return;
    dropping = on;
    island.classList.toggle("dropping", on);
    if (dropzone) dropzone.hidden = !on;
    if (on) { hovered = false; wake(); }
    render();
  }
  function base(p) {
    const parts = String(p).split(/[\\/]/);
    return parts[parts.length - 1] || p;
  }
  function handlePaths(paths) {
    if (!paths || !paths.length) return;
    setDropping(false);
    const label = "Inspecting " + base(paths[0]) +
      (paths.length > 1 ? " +" + (paths.length - 1) : "") + "\u2026";
    island.classList.add("caught");
    setTimeout(() => island.classList.remove("caught"), 700);
    addStep("file", label);
    setTask(label, "busy");
    if (window.Jarvis && Jarvis.fileIngest) Jarvis.fileIngest(paths);
  }
  ["dragenter", "dragover"].forEach((ev) =>
    island.addEventListener(ev, (e) => {
      e.preventDefault();
      setDropping(true);
    }));
  island.addEventListener("dragleave", (e) => {
    if (e.target === island) setDropping(false);
  });
  island.addEventListener("drop", (e) => {
    e.preventDefault();
    setDropping(false);
    const files = e.dataTransfer ? Array.from(e.dataTransfer.files || []) : [];
    handlePaths(files.map((f) => f.path || f.name).filter(Boolean));
  });
  if (win && win.listen) {
    win.listen("tauri://file-drop-hover", () => setDropping(true)).catch(() => {});
    win.listen("tauri://file-drop-cancelled", () => setDropping(false)).catch(() => {});
    win.listen("tauri://file-drop", (e) => handlePaths(e.payload || [])).catch(() => {});
  }

  // ---- inspection hook: scripts/inspect_states.py stages each card --------
  window.islandDemo = function (name) {
    hovered = false;
    flash = null;
    pendingQuestion = null;
    chatPinned = false;
    view = "home";
    setDropping(false);
    island.classList.remove("island-hidden");
    steps = [];
    if (name === "hidden") {
      island.classList.remove("expanded");
      island.classList.add("island-collapsed", "island-hidden");
      expanded = false;
      resizeDock(HIDDEN[0], HIDDEN[1]);
      return true;
    }
    if (name === "compact") { render(); return true; }
    if (name === "overview") {
      addStep("chat", "You asked: tidy my Downloads folder", { past: true });
      addStep("bolt", "List files in Downloads", { past: true });
      addStep("file", "Move 14 installers to Downloads\\Installers", { past: true });
      addStep("dots", "Sorting screenshots by date");
      setTask("Tidying Downloads\u2026", "busy", "Tidying your Downloads folder");
      hovered = true;
    } else if (name === "question") {
      showQuestion({ correlation_id: "demo-q", payload: { title: "Which folder should I clean up?",
        options: ["Downloads", "Desktop", "Documents"] } });
      pickOption(0);
    } else if (name === "result") {
      setTask("Done", "done");
      showResult({ ok: true, summary: "Downloads tidied\nMoved 14 installers\nSorted 32 screenshots",
        steps: [{ action: "list_dir", target: "C:\\Users\\me\\Downloads" }] });
    } else if (name === "error") {
      lastUserText = lastUserText || "summarize report.pdf";
      setTask("Action failed", "bad");
      showError("report.pdf is open in another program, so it can't be read.");
    } else if (name === "chat") {
      chatLog = [{ role: "user", text: "what's on my calendar after lunch?" },
        { role: "assistant", text: "Two things: a design review at 2:00 and a call with Sam at 3:30." }];
      setTask("Jarvis Standing By", "idle");
      view = "chat";
      chatPinned = true;
      renderChat();
    } else if (name === "drop") {
      setDropping(true);
      return true;
    }
    render();
    return true;
  };

  // one-off notices from Rust (e.g. "closed to the tray")
  window.islandHint = (text) => { setTask(String(text || ""), "warn"); render(); };

  // shown again as the companion (Rust evals this after set_companion):
  // start from the compact pill, not a strip that tucked away while hidden
  window.onCompanionChanged = (mode) => {
    if (mode !== "dock") return;
    wake();
    render();
  };

  render();
  window.__DOCK_READY = 1;
})();
