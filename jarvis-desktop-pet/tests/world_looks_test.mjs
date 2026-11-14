// Mini World look generator (doc 36 §11.3, doc 37 sprint 7).
// Run: node tests/world_looks_test.mjs   (exit 0 = pass)
import { genLook, TEAM_LOOKS, PAL } from "../ui_pet/src/world/looks.js";

const results = [];
function check(name, ok, extra) {
  results.push(!!ok);
  console.log((ok ? "PASS " : "FAIL ") + name + (extra !== undefined ? " | " + JSON.stringify(extra).slice(0, 200) : ""));
}

const key = (l) => JSON.stringify(l);
const taken = new Set(Object.values(TEAM_LOOKS).map(key));
const ten = [];
for (let i = 0; i < 10; i++) {
  const l = genLook("agent-" + i, "writer", taken);
  ten.push(l);
  taken.add(key(l));
}
check("ten generated agents all look different", new Set(ten.map(key)).size === 10);
check("none copies a regular", ten.every((l) => !Object.values(TEAM_LOOKS).map(key).includes(key(l))));
check("same seed, same look", key(genLook("seed-x", "coder")) === key(genLook("seed-x", "coder")));
check("different seed usually differs", key(genLook("a", "coder")) !== key(genLook("b", "coder")));
const parts = ten[0];
check("every part comes from the palette", PAL.skin.includes(parts.skin) && PAL.hair.includes(parts.hair) && PAL.style.includes(parts.style) && PAL.item.includes(parts.item));
const writers = Array.from({ length: 40 }, (_, i) => genLook("w" + i, "writer").outfit);
check("role tint shows up for most writers", writers.filter((o) => o === "#a78bfa").length >= 20, writers.filter((o) => o === "#a78bfa").length);
// a taken look is never handed out again, even for the same seed
const t2 = new Set([key(genLook("dup", "coder"))]);
check("taken look is rerolled", key(genLook("dup", "coder", t2)) !== [...t2][0]);
check("combinations ~12,000", PAL.skin.length * PAL.style.length * PAL.hair.length * PAL.outfit.length * PAL.item.length === 12000);

console.log(`\n${results.filter(Boolean).length}/${results.length} passed`);
process.exit(results.every(Boolean) ? 0 : 1);
