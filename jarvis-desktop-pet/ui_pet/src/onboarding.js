// First-run onboarding (spec 32, section 5): a 3-step modal over index.html —
// companion style -> microphone check -> local model verification. Shown when
// the backend says this install has not completed setup yet (config
// runtime.first_run is not false AND data/onboarded.json is absent).
(function () {
  const root = document.getElementById("onboarding");
  if (!root) return;

  const steps = [1, 2, 3].map((n) => document.getElementById("ob-step-" + n));
  const stepbar = document.getElementById("ob-stepbar");
  const backBtn = document.getElementById("ob-back");
  const nextBtn = document.getElementById("ob-next");
  const finishBtn = document.getElementById("ob-finish");
  const micBtn = document.getElementById("ob-mic-test");
  const micStatus = document.getElementById("ob-mic-status");
  const levelBar = document.getElementById("ob-level");
  const lmBtn = document.getElementById("ob-lm-test");
  const lmStatus = document.getElementById("ob-lm-status");
  const lmUrl = document.getElementById("ob-lm-url");
  const choices = document.getElementById("ob-choices");

  let step = 1;
  let petStyle = "2d";
  let micPeak = 0;
  let micStopTimer = null;
  let opened = false;

  function setStep(n) {
    step = Math.max(1, Math.min(3, n));
    steps.forEach((s) => {
      if (s) s.hidden = Number(s.id.split("-").pop()) !== step;
    });
    if (stepbar) {
      stepbar.querySelectorAll("li").forEach((li) => {
        li.classList.toggle("on", Number(li.dataset.step) <= step);
      });
    }
    if (backBtn) backBtn.hidden = step === 1;
    if (nextBtn) nextBtn.hidden = step === 3;
    if (finishBtn) finishBtn.hidden = step !== 3;
  }

  function open() {
    if (opened) return;
    opened = true;
    root.hidden = false;
    setStep(1);
  }

  function close() {
    opened = false;
    root.hidden = true;
    if (micStopTimer) {
      clearTimeout(micStopTimer);
      micStopTimer = null;
      try { Jarvis.voiceListen(false); } catch (e) { /* voice optional */ }
    }
  }

  // ---- backend decides whether setup is still pending ----
  function askState() {
    Jarvis.send({ type: "onboarding_state" });
  }
  Jarvis.on("onboarding_state", (d) => {
    if ((d.payload || {}).show) open();
  });
  Jarvis.on("onboarding_done", () => close());
  document.addEventListener("jarvis:connected", askState);
  askState();

  // ---- step 1: companion style ----
  if (choices) {
    choices.addEventListener("click", (e) => {
      const b = e.target.closest(".ob-choice");
      if (!b) return;
      petStyle = b.dataset.render === "3d" ? "3d" : "2d";
      choices.querySelectorAll(".ob-choice").forEach((c) => c.classList.toggle("active", c === b));
    });
  }

  // ---- step 2: microphone check ----
  Jarvis.on("ui.mic_level", (d) => {
    if (!opened || step !== 2 || !levelBar) return;
    const lvl = Math.max(0, Math.min(1, ((d.payload || {}).level || 0)));
    if (lvl > micPeak) micPeak = lvl;
    levelBar.style.width = (20 + lvl * 80).toFixed(0) + "%";
  });
  if (micBtn) {
    micBtn.onclick = () => {
      micPeak = 0;
      if (micStatus) micStatus.textContent = "Listening \u2014 say \u201cHey Jarvis\u201d\u2026";
      micBtn.disabled = true;
      try { Jarvis.voiceListen(true); } catch (e) { /* ignore */ }
      clearTimeout(micStopTimer);
      micStopTimer = setTimeout(() => {
        micBtn.disabled = false;
        try { Jarvis.voiceListen(false); } catch (e) { /* ignore */ }
        if (micStatus) {
          micStatus.textContent = micPeak > 0.03
            ? "Microphone works \u2014 level peaked at " + Math.round(micPeak * 100) + "%."
            : "No signal detected \u2014 check your input device in Settings.";
        }
      }, 6000);
    };
  }

  // ---- step 3: local model check ----
  Jarvis.on("lm_test", (d) => {
    const p = d.payload || {};
    if (lmStatus) {
      lmStatus.textContent = p.ok
        ? "Connected \u2014 " + (p.models && p.models.length ? p.models.join(", ") : "endpoint reachable") + "."
        : "Could not reach the endpoint: " + (p.error || "unknown error");
      lmStatus.classList.toggle("ok", !!p.ok);
    }
  });
  if (lmBtn) {
    lmBtn.onclick = () => {
      if (lmStatus) lmStatus.textContent = "Checking\u2026";
      Jarvis.testLm(lmUrl ? lmUrl.value : "");
    };
  }

  // ---- navigation ----
  if (nextBtn) nextBtn.onclick = () => setStep(step + 1);
  if (backBtn) backBtn.onclick = () => setStep(step - 1);
  if (finishBtn) {
    finishBtn.onclick = () => {
      finishBtn.disabled = true;
      Jarvis.send({ type: "onboarding_done", payload: { pet_style: petStyle } });
      // persist the chosen companion style with the regular settings payload
      let saved = false;
      const once = (d) => {
        if (saved) return;
        const s = d.payload;
        if (!s || !s.config) return;
        saved = true;
        s.config.runtime = s.config.runtime || {};
        const cur = s.config.runtime.pet_render_mode || "2d";
        if (cur === petStyle) {
          close();
          return;
        }
        s.config.runtime.pet_render_mode = petStyle;
        Jarvis.saveSettings(s);
        close();
      };
      Jarvis.on("settings", once);
      Jarvis.getSettings();
      setTimeout(() => {
        finishBtn.disabled = false;
        close();
      }, 1500);
    };
  }
})();
