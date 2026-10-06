// 2D vector Mochi animation engine (doc 31, section 2.4).
// Natural blinking, saccadic eye tracking, click squish spring, reactive moods.
window.Pet2D = (function () {
  const root = document.getElementById("pet-2d");
  if (!root) return null;
  const svg = root.querySelector(".pet-svg-character");
  const eyes = root.querySelector(".p2d-eyes");
  const lids = root.querySelector(".p2d-lids");
  const mouth = root.querySelector(".p2d-mouth");
  const cheeks = root.querySelector(".p2d-cheeks");
  const moodHost = document.getElementById("pet");

  const MOUTH_SMILE = "M57 92 Q64 99.5 71 92";
  const MOUTH_HAPPY = "M54 91 Q64 101.5 74 91";

  let mood = (moodHost && moodHost.dataset.mood) || "idle";
  let blinkTimer = null;
  let sqTimer = null;

  // ---- natural blink: every 3-5s, 120ms close, occasional double blink ----
  function blink(on) {
    if (lids) lids.classList.toggle("blink", !!on);
  }
  function scheduleBlink() {
    clearTimeout(blinkTimer);
    blinkTimer = setTimeout(() => {
      if (mood !== "sleep") {
        blink(true);
        setTimeout(() => blink(false), 120);
        if (Math.random() < 0.22) {
          setTimeout(() => {
            blink(true);
            setTimeout(() => blink(false), 110);
          }, 250);
        }
      }
      scheduleBlink();
    }, 3000 + Math.random() * 2000);
  }
  scheduleBlink();

  // ---- saccadic eye tracking toward the pointer ----
  let tx = 0, ty = 0, cx = 0, cy = 0;
  document.addEventListener("mousemove", (e) => {
    const r = root.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const nx = Math.max(-1, Math.min(1, (e.clientX - (r.left + r.width / 2)) / (r.width / 2)));
    const ny = Math.max(-1, Math.min(1, (e.clientY - (r.top + r.height / 2)) / (r.height / 2)));
    tx = nx * 3.2;
    ty = ny * 3.2 + (mood === "thinking" ? -2.6 : 0);
  }, { passive: true });
  (function saccade() {
    cx += (tx - cx) * 0.14;
    cy += (ty - cy) * 0.14;
    if (eyes) eyes.setAttribute("transform", "translate(" + cx.toFixed(2) + " " + cy.toFixed(2) + ")");
    requestAnimationFrame(saccade);
  })();

  // ---- click squish & jiggle (squash-and-stretch spring) ----
  function squish() {
    if (!svg) return;
    svg.classList.remove("squish");
    void svg.getBoundingClientRect(); // force layout so the animation restarts
    svg.classList.add("squish");
    clearTimeout(sqTimer);
    sqTimer = setTimeout(() => svg.classList.remove("squish"), 360);
  }
  root.addEventListener("click", squish);

  // ---- mood morphing ----
  function setMood(m) {
    mood = m || "idle";
    root.classList.toggle("tilt", mood === "thinking");
    root.classList.toggle("dim", mood === "sleep");
    root.classList.toggle("sleeping", mood === "sleep");
    const bright = mood === "happy" || mood === "poked" || mood === "curious";
    if (cheeks) cheeks.classList.toggle("bright", bright);
    if (mouth) mouth.setAttribute("d", bright ? MOUTH_HAPPY : MOUTH_SMILE);
    if (mood === "sleep") tx = ty = 0;
  }
  setMood(mood);

  return {
    setMood,
    squish,
    getMood: () => mood,
  };
})();
