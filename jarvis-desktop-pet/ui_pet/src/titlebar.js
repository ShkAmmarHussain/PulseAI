// Bespoke frameless titlebar controls (spec 33, section 2.3).
// Reads window.__TAURI__ (withGlobalTauri) — inert in dev/mirror tabs.
(function initTitlebar() {
  const ta = window.__TAURI__;
  const win = ta && ta.window ? ta.window.appWindow : null;
  if (!win) return;

  const min = document.getElementById("win-min");
  const max = document.getElementById("win-max");
  const close = document.getElementById("win-close");
  if (min) min.addEventListener("click", () => win.minimize());
  if (max) {
    max.addEventListener("click", async () => {
      try {
        const isMax = await win.isMaximized();
        if (isMax) win.unmaximize();
        else win.maximize();
      } catch (e) {
        win.maximize();
      }
    });
  }
  if (close) close.addEventListener("click", () => win.close());

  // double-click on the drag area toggles maximize (native titlebar parity)
  document.querySelectorAll("#window-titlebar .titlebar-left, #window-titlebar .titlebar-center").forEach((el) => {
    el.addEventListener("dblclick", async () => {
      try {
        const isMax = await win.isMaximized();
        if (isMax) win.unmaximize();
        else win.maximize();
      } catch (e) { /* ignore */ }
    });
  });
})();
