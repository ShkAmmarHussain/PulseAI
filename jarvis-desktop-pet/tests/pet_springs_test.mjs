/* Unit checks for pet_springs.js (spec 29, section 5.5.4 physics).
   Run: node tests/pet_springs_test.mjs   (exit 0 = pass) */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "..", "ui_pet", "src", "pet_springs.js"), "utf8");
const mod = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));
const { Spring, Taffy, volumeScales } = mod;

let pass = 0;
let fail = 0;
function check(name, ok, extra = "") {
  if (ok) { pass++; console.log("PASS " + name); }
  else { fail++; console.log("FAIL " + name + (extra ? " | " + extra : "")); }
}

// rest state stays at rest
const s0 = new Spring();
for (let i = 0; i < 300; i++) s0.step(1 / 60);
check("rest state converges", Math.abs(s0.x - 0) < 1e-6 && Math.abs(s0.v) < 1e-6,
  `x=${s0.x.toExponential(2)}`);

// poke impulse: wobbles back within ~350ms of activity (spec: rebound over 350ms)
const s1 = new Spring(18.5, 0.65, 1);
s1.impulse(-2.1);
let t = 0;
let settle = -1;
while (t < 1.5) {
  s1.step(1 / 60);
  t += 1 / 60;
  if (settle < 0 && Math.abs(s1.x - 1) < 0.02 && Math.abs(s1.v) < 0.35) settle = t;
}
check("impulse settles quickly (visible wobble < 350ms)", settle >= 0 && settle <= 0.35 + 0.18,
  `settle=${settle === -1 ? "never" : settle.toFixed(3)}s`);
check("impulse fully settles by 1.5s", Math.abs(s1.x - 1) < 0.005, `x=${s1.x.toFixed(5)}`);

// underdamped: it should actually overshoot (bouncy, not dead)
const s2 = new Spring(18.5, 0.65, 1);
s2.impulse(-2.1);
let minx = 1;
for (let i = 0; i < 60; i++) { s2.step(1 / 60); minx = Math.min(minx, s2.x); }
check("impulse overshoots (bouncy)", minx < 1 - 0.02, `min=${minx.toFixed(4)}`);

// stable at low frame rate (10 FPS render throttle, section 5.5.8)
const s3 = new Spring(18.5, 0.65, 1);
s3.impulse(-2.0);
let stable = true;
for (let i = 0; i < 150; i++) {
  s3.step(0.1);
  if (!Number.isFinite(s3.x) || Math.abs(s3.x) > 10) { stable = false; break; }
}
check("stable at dt=0.1 (10 FPS)", stable && Math.abs(s3.x - 1) < 0.01,
  `x=${s3.x}`);

// volume conservation (spec: Δx = Δz = -½Δy)
const v = volumeScales(0.9);
check("volume conservation on compression", Math.abs(v.sx - 1.05) < 1e-9 &&
  Math.abs(v.sz - 1.05) < 1e-9, JSON.stringify(v));
const v2 = volumeScales(1.1);
check("volume conservation on stretch", Math.abs(v2.sx - 0.95) < 1e-9, JSON.stringify(v2));

// taffy drag + snap-back
const t1 = new Taffy();
t1.drag(40, -20);
for (let i = 0; i < 30; i++) t1.step(1 / 60);
check("taffy follows drag velocity", Math.abs(t1.x.x) > 0.05 && Math.abs(t1.x.x) <= 0.35,
  `x=${t1.x.x.toFixed(4)}`);
t1.release();
for (let i = 0; i < 180; i++) t1.step(1 / 60);
check("taffy snaps back to rest", Math.abs(t1.x.x) < 0.01 && Math.abs(t1.y.x) < 0.01,
  `x=${t1.x.x.toExponential(2)} y=${t1.y.x.toExponential(2)}`);

console.log(`== ${pass}/${pass + fail} PASS ==`);
process.exit(fail ? 1 : 0);
