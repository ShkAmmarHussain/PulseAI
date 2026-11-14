// Pure look generator (no three.js) so node tests can import it (doc 37 sprint 7).
export const PAL = {
  skin: ["#fde2cf", "#f6d2b8", "#f1c9a5", "#e0ac86", "#a8754f", "#7b4f35"],
  hair: ["#1a1a1d", "#7c2d12", "#b45309", "#facc15", "#e5e7eb", "#3b82f6", "#16a34a", "#ec4899"],
  style: ["cap", "spiky", "bob", "bun", "long"],
  item: ["none", "glasses", "headset", "hat", "bow"],
  acc: ["#f5a524", "#38bdf8", "#f472b6", "#22c55e", "#e5e7eb"],
  outfit: ["#818cf8", "#38bdf8", "#22c55e", "#c084fc", "#f472b6", "#2dd4bf", "#fb923c", "#a78bfa", "#64748b", "#facc15"],
};
const ROLE_TINT = { writer: "#a78bfa", coder: "#64748b", translator: "#facc15", analyst: "#2dd4bf", designer: "#f472b6" };

// fixed looks for the eight regulars (doc 36 §11.3); Pip is the egg
export const TEAM_LOOKS = {
  thinker: { skin: "#f6d2b8", hair: "#4c3a8f", outfit: "#818cf8", style: "spiky", item: "glasses", acc: "#e5e7eb" },
  bodie: { skin: "#a8754f", hair: "#1a1a1d", outfit: "#fb923c", style: "cap", item: "hat", acc: "#facc15" },
  rhea: { skin: "#f1c9a5", hair: "#b45309", outfit: "#38bdf8", style: "long", item: "none", acc: "#38bdf8" },
  otto: { skin: "#e0ac86", hair: "#3f3f46", outfit: "#22c55e", style: "cap", item: "headset", acc: "#22c55e" },
  vee: { skin: "#fde2cf", hair: "#e5e7eb", outfit: "#c084fc", style: "bob", item: "bow", acc: "#c084fc" },
  ada: { skin: "#7b4f35", hair: "#1a1a1d", outfit: "#f472b6", style: "bun", item: "none", acc: "#f472b6" },
  remy: { skin: "#c68d62", hair: "#7c2d12", outfit: "#2dd4bf", style: "spiky", item: "none", acc: "#2dd4bf" },
};

function seeded(str) {
  let h = 2166136261;
  for (const ch of String(str)) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619);
  }
  let t = h >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (R, a) => a[Math.floor(R() * a.length)];

// unique look per new agent: seeded by its id, rerolled while another active agent has it
export function genLook(seed, role, taken = new Set()) {
  for (let k = 0; k < 40; k++) {
    const R = seeded(seed + ":" + k);
    const tint = ROLE_TINT[String(role || "").toLowerCase()];
    const look = { skin: pick(R, PAL.skin), hair: pick(R, PAL.hair), style: pick(R, PAL.style), item: pick(R, PAL.item), acc: pick(R, PAL.acc), outfit: tint && R() < 0.7 ? tint : pick(R, PAL.outfit) };
    if (!taken.has(JSON.stringify(look))) return look;
  }
  return { skin: PAL.skin[0], hair: PAL.hair[0], style: "cap", item: "none", acc: PAL.acc[0], outfit: PAL.outfit[0] };
}

