// Chibi character kit + Pip, and the look generator (doc 36 §11.3).
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const GRAD = (() => {
  const t = new THREE.DataTexture(new Uint8Array([70, 150, 215, 255]), 4, 1, THREE.RedFormat);
  t.minFilter = t.magFilter = THREE.NearestFilter;
  t.needsUpdate = true;
  return t;
})();
export const toon = (c, o = {}) => new THREE.MeshToonMaterial(Object.assign({ color: c, gradientMap: GRAD }, o));
const OUTLINE = new THREE.MeshBasicMaterial({ color: "#08080a", side: THREE.BackSide });

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

function outlined(mesh, s = 1.045) {
  const o = new THREE.Mesh(mesh.geometry, OUTLINE);
  o.scale.setScalar(s);
  mesh.add(o);
  return mesh;
}

export function buildChibi(look) {
  const root = new THREE.Group();
  const rig = {};
  const skin = toon(look.skin), cloth = toon(look.outfit), hair = toon(look.hair, { side: THREE.DoubleSide }), acc = toon(look.acc || "#f5a524"), shoe = toon("#26272c");
  const legGeo = new THREE.CapsuleGeometry(0.075, 0.13, 4, 10);
  for (const s of [-1, 1]) {
    const hip = new THREE.Group();
    hip.position.set(s * 0.09, 0.27, 0);
    root.add(hip);
    const leg = outlined(new THREE.Mesh(legGeo, shoe));
    leg.position.y = -0.12;
    hip.add(leg);
    rig[s < 0 ? "hipL" : "hipR"] = hip;
  }
  const body = outlined(new THREE.Mesh(new THREE.CapsuleGeometry(0.19, 0.2, 6, 14), cloth));
  body.position.y = 0.47;
  body.scale.z = 0.86;
  root.add(body);
  rig.body = body;
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.03, 8, 18), toon("#f4f1ea"));
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 0.64;
  root.add(collar);
  for (const s of [-1, 1]) {
    const sh = new THREE.Group();
    sh.position.set(s * 0.225, 0.6, 0);
    root.add(sh);
    const arm = outlined(new THREE.Mesh(new THREE.CapsuleGeometry(0.055, 0.15, 4, 8), cloth));
    arm.position.y = -0.1;
    sh.add(arm);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.058, 12, 8), skin);
    hand.position.y = -0.22;
    sh.add(hand);
    sh.rotation.z = s * 0.18;
    rig[s < 0 ? "shL" : "shR"] = sh;
  }
  const head = new THREE.Group();
  head.position.y = 0.98;
  root.add(head);
  rig.head = head;
  const skull = outlined(new THREE.Mesh(new THREE.SphereGeometry(0.34, 36, 26), skin), 1.035);
  skull.scale.set(1, 0.94, 0.96);
  head.add(skull);
  const eyeMat = toon("#16171b"), white = new THREE.MeshBasicMaterial({ color: "#ffffff" });
  for (const s of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.058, 16, 12), eyeMat);
    e.scale.set(1, 1.42, 0.5);
    e.position.set(s * 0.12, -0.03, 0.305);
    e.rotation.y = s * 0.32;
    head.add(e);
    const hl = new THREE.Mesh(new THREE.SphereGeometry(0.018, 8, 6), white);
    hl.position.set(s * 0.12 + 0.022, 0.012, 0.33);
    head.add(hl);
    const bl = new THREE.Mesh(new THREE.CircleGeometry(0.045, 16), new THREE.MeshBasicMaterial({ color: "#ff8fa3", transparent: true, opacity: 0.5 }));
    bl.position.set(s * 0.205, -0.11, 0.27);
    bl.rotation.y = s * 0.62;
    bl.scale.y = 0.6;
    head.add(bl);
  }
  const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.028, 0.008, 6, 12, Math.PI), toon("#6b2f2f"));
  mouth.position.set(0, -0.13, 0.318);
  mouth.rotation.z = Math.PI;
  head.add(mouth);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.365, 36, 16, 0, Math.PI * 2, 0, Math.PI * 0.44), hair);
  cap.rotation.x = -0.2;
  head.add(cap);
  const st = look.style;
  if (st === "spiky") {
    for (let k = 0; k < 9; k++) {
      const th = 0.22 * Math.PI + (k % 2) * 0.12, ph = -Math.PI * 0.1 + (k * Math.PI * 1.2) / 8 + Math.PI * 0.9;
      const dir = new THREE.Vector3(-Math.cos(ph) * Math.sin(th), Math.cos(th), Math.sin(ph) * Math.sin(th)).normalize();
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.26, 7), hair);
      cone.position.copy(dir.clone().multiplyScalar(0.36));
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      head.add(cone);
    }
  }
  if (st === "bob" || st === "long") {
    head.add(new THREE.Mesh(new THREE.SphereGeometry(0.372, 36, 16, Math.PI / 2 + 0.95, Math.PI * 2 - 1.9, 0.3 * Math.PI, (st === "long" ? 0.5 : 0.38) * Math.PI), hair));
    if (st === "long") {
      const back = new THREE.Mesh(new THREE.CapsuleGeometry(0.26, 0.32, 6, 14), hair);
      back.position.set(0, -0.36, -0.16);
      back.scale.z = 0.55;
      head.add(back);
    }
  }
  if (st === "bun") {
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 12), hair);
    b.position.set(0, 0.36, -0.12);
    head.add(b);
  }
  head.add(new THREE.Mesh(new THREE.SphereGeometry(0.37, 24, 8, Math.PI / 2 - 0.7, 1.4, 0.28 * Math.PI, 0.14 * Math.PI), hair));
  const it = look.item;
  if (it === "glasses") {
    const fm = toon(look.acc || "#e5e7eb");
    for (const s of [-1, 1]) {
      const r = new THREE.Mesh(new THREE.TorusGeometry(0.078, 0.013, 8, 22), fm);
      r.position.set(s * 0.12, -0.03, 0.348);
      r.rotation.y = s * 0.3;
      head.add(r);
    }
  } else if (it === "headset") {
    head.add(new THREE.Mesh(new THREE.TorusGeometry(0.385, 0.024, 8, 30, Math.PI), toon("#2d3038")));
    for (const s of [-1, 1]) {
      const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.07, 18), acc);
      cup.rotation.z = Math.PI / 2;
      cup.position.set(s * 0.37, -0.03, 0);
      head.add(cup);
    }
  } else if (it === "hat") {
    const crown = new THREE.Mesh(new THREE.SphereGeometry(0.38, 30, 12, 0, Math.PI * 2, 0, Math.PI * 0.36), acc);
    crown.rotation.x = -0.18;
    head.add(crown);
    const brim = new THREE.Mesh(new RoundedBoxGeometry(0.4, 0.03, 0.24, 2, 0.012), acc);
    brim.position.set(0, 0.14, 0.36);
    brim.rotation.x = 0.25;
    head.add(brim);
  } else if (it === "bow") {
    for (const s of [-1, 1]) {
      const w = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.14, 10), acc);
      w.rotation.z = (s * Math.PI) / 2;
      w.position.set(0.2 + s * 0.07, 0.3, 0.1);
      head.add(w);
    }
  }
  root.traverse((o) => {
    if (o.isMesh && o.material !== OUTLINE) o.castShadow = true;
  });
  return { root, rig };
}

export function buildPip() {
  const root = new THREE.Group();
  const rig = {};
  const pts = [];
  for (let i = 0; i <= 28; i++) {
    const a = (i / 28) * Math.PI;
    pts.push(new THREE.Vector2(Math.sin(a) * 0.44 * (1 + 0.1 * Math.cos(a)), 0.58 - Math.cos(a) * 0.58));
  }
  const egg = new THREE.Mesh(new THREE.LatheGeometry(pts, 48), new THREE.MeshStandardMaterial({ color: "#f5a524", emissive: "#f5a524", emissiveIntensity: 0.42, roughness: 0.38 }));
  egg.castShadow = true;
  root.add(egg);
  rig.body = egg;
  const head = new THREE.Group();
  root.add(head);
  rig.head = head;
  for (const s of [-1, 1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 12), toon("#141414"));
    e.scale.set(1, 1.35, 0.5);
    e.position.set(s * 0.13, 0.72, 0.4);
    head.add(e);
  }
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.018, 0.24, 8), toon("#5b8f4e"));
  stem.position.y = 1.27;
  head.add(stem);
  const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), toon("#7cc56a"));
  leaf.scale.set(1.5, 0.5, 0.9);
  leaf.position.set(0.07, 1.39, 0);
  leaf.rotation.z = 0.5;
  head.add(leaf);
  const pl = new THREE.PointLight("#ffb347", 2, 2.6, 2);
  pl.position.set(0, 0.6, 0.6);
  root.add(pl);
  root.scale.setScalar(1.05);
  return { root, rig };
}

// small offscreen renderer for roster/inspector portraits
let pr = null, pScene = null, pCam = null;
const portraitCache = new Map();
export function portrait(key, look, isPip) {
  if (portraitCache.has(key)) return portraitCache.get(key);
  try {
    if (!pr) {
      pr = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
      pr.setSize(128, 128);
      pr.toneMapping = THREE.ACESFilmicToneMapping;
      pScene = new THREE.Scene();
      pScene.add(new THREE.HemisphereLight("#ffffff", "#3a2a1a", 1.4));
      const k = new THREE.DirectionalLight("#ffe9cc", 2.2);
      k.position.set(1.5, 2.5, 3);
      pScene.add(k);
      pCam = new THREE.PerspectiveCamera(26, 1, 0.1, 20);
    }
    const m = isPip ? buildPip() : buildChibi(look);
    pScene.add(m.root);
    m.root.rotation.y = 0.3;
    if (isPip) {
      pCam.position.set(0, 0.75, 3.0);
      pCam.lookAt(0, 0.62, 0);
    } else {
      pCam.position.set(0, 1.0, 2.4);
      pCam.lookAt(0, 0.86, 0);
    }
    pr.render(pScene, pCam);
    const url = pr.domElement.toDataURL();
    pScene.remove(m.root);
    portraitCache.set(key, url);
    return url;
  } catch (e) {
    return "";
  }
}
export function forgetPortrait(key) {
  portraitCache.delete(key);
}
