// Shared approval wording (spec 34 section 7.2 + UI review item 1): every
// surface names the action in plain words ("Delete zz_probe.txt") and shows
// the risk exactly once, instead of echoing the backend's raw
// "Allow this action? (delete_file, risk 9/10)" string.
(function () {
  const VERBS = {
    launch_app: "Open", open_app: "Open", close_app: "Close",
    delete_file: "Delete", move_file: "Move", create_file: "Create",
    list_dir: "List files in", open_url: "Open in your browser",
    web_search: "Search the web", run_shell: "Run a command",
    vision_describe: "Describe your screen", type_text: "Type text",
    vision_file: "Analyze image file", summarize_file: "Summarize file",
    press_hotkey: "Press a shortcut", click: "Click on screen", move_mouse: "Move the mouse",
    shutdown: "Shut down the PC", restart: "Restart the PC",
    respond: "Respond", noop: "Run",
  };

  function actionName(p) {
    const a = p && p.action;
    if (!a) return "";
    if (typeof a === "string") return a;
    return a.action || a.name || a.tool || "";
  }

  function friendlyAction(p) {
    const a = actionName(p);
    const verb = VERBS[a] || (a ? a.replace(/[_-]+/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "Run an action");
    const act = (p && typeof p.action === "object" && p.action) || {};
    let tgt = act.target || act.path || act.url || act.cmd || "";
    if (tgt) {
      const parts = String(tgt).split(/[\\/]/);
      tgt = parts[parts.length - 1] || String(tgt);
      if (tgt.length > 46) tgt = tgt.slice(0, 43) + "…";
    }
    return { verb: verb, tgt: tgt, title: (verb + (tgt ? " " + tgt : "")).trim() };
  }

  function riskBand(r) {
    const n = Number(r);
    if (r == null || !isFinite(n)) return { cls: "med", label: "Unknown risk", short: "Unknown" };
    if (n <= 2) return { cls: "low", label: "Low risk", short: "Low" };
    if (n <= 6) return { cls: "med", label: "Medium risk", short: "Medium" };
    return { cls: "high", label: "High risk", short: "High" };
  }

  // the backend's stock prompt carries no information beyond the action name
  // and risk, which the card already shows - treat it as absent
  function extraMessage(p) {
    const m = String((p && p.message) || "").trim();
    if (!m || /^Allow this action\?/i.test(m)) return "";
    return m;
  }

  window.ApprovalText = { VERBS: VERBS, friendlyAction: friendlyAction, riskBand: riskBand, extraMessage: extraMessage };
})();
