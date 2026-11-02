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
  // never win.close(): that destroys the main window, after which nothing can
  // reopen it (docs/35 B2). Rust hides it to the tray or quits, per Settings.
  if (close) close.addEventListener("click", () => {
    if (ta.tauri && ta.tauri.invoke) ta.tauri.invoke("close_main_window");
    else win.hide();
  });

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
