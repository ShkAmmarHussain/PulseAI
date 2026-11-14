// PulseAI HQ: 3 floors x 3x3 rooms, cut away at the front (doc 36 §11.2).
// Room ids match core/world/runtime.py: f{floor}r{row}c{col}, row 1 = front.
import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { toon } from "./chibi.js";

export const W = 4, DR = 3.4, H = 3, CORR = 1.4;
export const DEPTH = DR * 3 + CORR; // 11.6
export const CZ = DR * 3 + CORR / 2; // corridor lane z
export const LIFT = { x: 13.2, z: 10.55 };
export const DOOR = { x: -1.8, z: CZ };

const DEFAULTS = {
  f1r1c1: { name: "Lobby", c: "#f5a524", props: "lobby" },
  f1r1c2: { name: "Archive", c: "#f472b6", props: "archive" },
  f1r1c3: { name: "Watch room", c: "#c084fc", props: "watch" },
  f2r1c1: { name: "Research lab", c: "#38bdf8", props: "research" },
  f2r1c2: { name: "Ops room", c: "#22c55e", props: "ops" },
  f3r1c1: { name: "Planning room", c: "#818cf8", props: "planning" },
  f3r1c2: { name: "Director's office", c: "#f5a524", props: "director" },
  f3r1c3: { name: "Workshop", c: "#fb923c", props: "workshop" },
};
const ROW_LETTER = { 1: "A", 2: "B", 3: "C" };

export function roomGeom(id) {
  const m = /^f(\d)r(\d)c(\d)$/.exec(id || "");
  if (!m) return null;
  const f = +m[1], r = +m[2], c = +m[3];
  const x0 = (c - 1) * W, zBack = (3 - r) * DR;
  const d = DEFAULTS[id];
  return {
    id, f, r, c, x0, cx: x0 + W / 2, y: (f - 1) * H, zBack, zc: zBack + DR / 2,
    name: d ? d.name : id === "f2r1c3" ? "Studio" : `Room ${f}${ROW_LETTER[r]}${c}`,
    color: d ? d.c : "#9aa3b2", props: d ? d.props : "spare", spare: !d,
  };
}
export const ALL_ROOMS = [];
for (let f = 1; f <= 3; f++) for (let r = 1; r <= 3; r++) for (let c = 1; c <= 3; c++) ALL_ROOMS.push(roomGeom(`f${f}r${r}c${c}`));

let seedN = 7;
const rnd = () => ((seedN = (seedN * 16807) % 2147483647) - 1) / 2147483646;
const col = (c) => new THREE.Color(c);
const mix = (a, b, t) => col(a).lerp(col(b), t);
const std = (c, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.85, metalness: 0 }, o));
const glow = (c, i = 2.4) => new THREE.MeshStandardMaterial({ color: "#111", emissive: c, emissiveIntensity: i, roughness: 0.5 });

function canvasTex(w, h, draw, repeat) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) {
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeat[0], repeat[1]);
  }
  return t;
}
function textTex(text, w, h, size, color, bg) {
  return canvasTex(w, h, (g) => {
    if (bg) {
      g.fillStyle = bg;
      g.fillRect(0, 0, w, h);
    }
    g.fillStyle = color;
    g.font = `600 ${size}px "Segoe UI", system-ui, sans-serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.letterSpacing = `${Math.round(size * 0.28)}px`;
    g.fillText(text, w / 2, h / 2 + 2);
  });
}

export function buildBuilding(scene) {
  const M = {
    slab: std("#2a2521", { roughness: 0.7 }), edge: std("#3a3129", { roughness: 0.6 }),
    wall: std("#1e1b18"), metal: std("#3b3d43", { roughness: 0.4, metalness: 0.6 }), dark: std("#17181b", { roughness: 0.6 }),
    desk: std("#6b4a32", { roughness: 0.55 }), top: std("#d9cbb8", { roughness: 0.45 }), chair: std("#2c2e33", { roughness: 0.5 }),
    white: std("#e9e6df", { roughness: 0.4 }), pot: std("#c9b9a3", { roughness: 0.7 }), leaf: toon("#3f8f5b"), leaf2: toon("#2f7a49"),
    glass: new THREE.MeshStandardMaterial({ color: "#a9c4d6", transparent: true, opacity: 0.13, roughness: 0.08, metalness: 0.2, depthWrite: false }),
    amber: glow("#f5a524", 2.6),
  };
  const wood = canvasTex(512, 512, (g, w, h) => {
    const rows = 8, ph = h / rows;
    for (let r = 0; r < rows; r++) {
      let x = -rnd() * 200;
      while (x < w) {
        const len = 160 + rnd() * 180;
        g.fillStyle = `hsl(28 32% ${34 + rnd() * 14}%)`;
        g.fillRect(x, r * ph, len, ph);
        g.fillStyle = "rgba(0,0,0,.45)";
        g.fillRect(x, r * ph, 2, ph);
        x += len;
      }
      g.fillStyle = "rgba(0,0,0,.5)";
      g.fillRect(0, r * ph, w, 2);
    }
  }, [1.4, 1.2]);

  const box = (w, h, d, mat, x, y, z, r, parent) => {
    const m = new THREE.Mesh(r > 0 ? new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2)) : new THREE.BoxGeometry(w, h, d), mat);
    m.position.set(x, y, z);
    m.castShadow = m.receiveShadow = true;
    parent.add(m);
    return m;
  };
  const cyl = (rt, rb, h, mat, x, y, z, parent, seg = 18) => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
    m.position.set(x, y, z);
    m.castShadow = m.receiveShadow = true;
    parent.add(m);
    return m;
  };
  const plant = (g, x, y, z, s = 1) => {
    cyl(0.16 * s, 0.12 * s, 0.32 * s, M.pot, x, y + 0.16 * s, z, g);
    for (let k = 0; k < 4; k++) {
      const b = new THREE.Mesh(new THREE.IcosahedronGeometry(0.2 * s, 1), k % 2 ? M.leaf : M.leaf2);
      b.position.set(x + (rnd() - 0.5) * 0.22 * s, y + (0.45 + rnd() * 0.35) * s, z + (rnd() - 0.5) * 0.22 * s);
      b.castShadow = true;
      g.add(b);
    }
  };
  const desk = (g, x, y, z, c, screens = 1, wide = 1.4) => {
    box(wide, 0.07, 0.7, M.top, x, y + 0.76, z, 0.02, g);
    for (const sx of [-1, 1]) box(0.06, 0.74, 0.62, M.desk, x + sx * (wide / 2 - 0.08), y + 0.37, z, 0.01, g);
    for (let s = 0; s < screens; s++) {
      const off = (s - (screens - 1) / 2) * 0.62;
      box(0.58, 0.36, 0.04, M.dark, x + off, y + 1.17, z - 0.2, 0.015, g);
      const scr = new THREE.Mesh(new THREE.PlaneGeometry(0.52, 0.3), glow(c, 1.4));
      scr.position.set(x + off, y + 1.17, z - 0.177);
      g.add(scr);
    }
    box(0.42, 0.06, 0.42, M.chair, x + 0.1, y + 0.46, z + 0.6, 0.03, g);
  };
  const shelf = (g, x, y, z, w = 1.6) => {
    box(w, 2.1, 0.4, M.desk, x, y + 1.05, z, 0.02, g);
    const books = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), std("#ffffff", { roughness: 0.7 }), 50);
    const mtx = new THREE.Matrix4();
    const pal = ["#f472b6", "#38bdf8", "#f5a524", "#e5e7eb", "#a78bfa", "#22c55e"];
    let n = 0;
    for (let row = 0; row < 4; row++) {
      let bx = x - w / 2 + 0.12;
      while (bx < x + w / 2 - 0.15 && n < 50) {
        const bw = 0.06 + rnd() * 0.06, bh = 0.3 + rnd() * 0.12;
        mtx.compose(new THREE.Vector3(bx + bw / 2, y + 0.2 + row * 0.5 + bh / 2, z + 0.04), new THREE.Quaternion(), new THREE.Vector3(bw, bh, 0.28));
        books.setMatrixAt(n, mtx);
        books.setColorAt(n, col(pal[Math.floor(rnd() * pal.length)]));
        n++;
        bx += bw + 0.01;
      }
    }
    books.count = n;
    books.castShadow = true;
    g.add(books);
  };

  const floors = [new THREE.Group(), new THREE.Group(), new THREE.Group()];
  const roof = new THREE.Group();
  floors.forEach((g) => scene.add(g));
  scene.add(roof);
  const rooms = {};

  const slab = (y, g) => {
    box(12.5, 0.3, DEPTH + 0.2, M.slab, 6, y - 0.15, DEPTH / 2, 0.05, g);
    box(12.5, 0.05, 0.05, M.amber, 6, y - 0.06, DEPTH + 0.12, 0, g).castShadow = false;
  };

  for (let f = 0; f < 3; f++) {
    const g = floors[f], y = f * H;
    slab(y, g);
    box(12.2, H, 0.2, M.wall, 6, y + H / 2, -0.1, 0, g);
    if (f === 0) {
      box(0.2, H, DR * 3, M.wall, -0.1, y + H / 2, (DR * 3) / 2, 0, g);
      box(0.2, 0.8, CORR, M.wall, -0.1, y + H - 0.4, DR * 3 + CORR / 2, 0, g);
      box(0.06, 2.2, 0.06, M.amber, 0.02, y + 1.1, DR * 3 + 0.1, 0, g);
      box(0.06, 2.2, 0.06, M.amber, 0.02, y + 1.1, DEPTH - 0.1, 0, g);
    } else box(0.2, H, DEPTH, M.wall, -0.1, y + H / 2, DEPTH / 2, 0, g);
    box(0.2, H, DR * 3, M.wall, 12.1, y + H / 2, (DR * 3) / 2, 0, g);
    // column walls between rooms (seen edge-on from the front)
    for (const x of [4, 8]) box(0.12, H, DR * 3, std("#24211d"), x, y + H / 2, (DR * 3) / 2, 0.02, g);
    // low glass between rows, with a door gap on each room's centre lane
    for (const z of [DR, DR * 2, DR * 3]) {
      for (let c = 0; c < 3; c++) {
        const x0 = c * W;
        for (const [a, b] of [[x0 + 0.1, x0 + W / 2 - 0.55], [x0 + W / 2 + 0.55, x0 + W - 0.1]]) {
          const pane = new THREE.Mesh(new THREE.BoxGeometry(b - a, 1.05, 0.04), M.glass);
          pane.position.set((a + b) / 2, y + 0.53, z);
          g.add(pane);
          box(b - a, 0.04, 0.06, M.metal, (a + b) / 2, y + 1.06, z, 0, g);
        }
      }
    }
  }
  slab(9, roof);
  box(12.5, 0.4, 0.14, M.edge, 6, 9.2, 0.07, 0.03, roof);
  const signMat = new THREE.MeshStandardMaterial({ color: "#000", emissive: "#fff", emissiveMap: textTex("PULSEAI HQ", 1024, 180, 92, "#f5a524"), emissiveIntensity: 2.2, transparent: true, alphaMap: textTex("PULSEAI HQ", 1024, 180, 92, "#fff", "#000") });
  box(4.9, 1.05, 0.14, M.dark, 6, 9.72, DEPTH - 1.6, 0.05, roof);
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 0.8), signMat);
  sign.position.set(6, 9.72, DEPTH - 1.52);
  roof.add(sign);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), glow("#ff4d5e", 4));
  beacon.position.set(11.2, 10.4, 1.0);
  roof.add(beacon);
  cyl(0.03, 0.03, 1.3, M.metal, 11.2, 9.7, 1.0, roof);

  // lift
  const shaft = new THREE.Group();
  scene.add(shaft);
  const lx0 = 12.25, lx1 = 14.15, lz0 = DR * 3 - 0.1, lz1 = DEPTH;
  for (const [x, z] of [[lx0, lz0], [lx1, lz0], [lx0, lz1], [lx1, lz1]]) cyl(0.05, 0.05, 9.4, M.metal, x, 4.55, z, shaft, 10);
  const g1 = new THREE.Mesh(new THREE.PlaneGeometry(lx1 - lx0, 9.4), M.glass);
  g1.position.set((lx0 + lx1) / 2, 4.55, lz0);
  shaft.add(g1);
  const g2 = new THREE.Mesh(new THREE.PlaneGeometry(lz1 - lz0, 9.4), M.glass);
  g2.rotation.y = Math.PI / 2;
  g2.position.set(lx1, 4.55, (lz0 + lz1) / 2);
  shaft.add(g2);
  for (let f = 0; f < 4; f++) box(2.0, 0.3, lz1 - lz0 + 0.1, M.slab, (lx0 + lx1) / 2, f * H - 0.15, (lz0 + lz1) / 2, 0.04, shaft);
  const car = new THREE.Group();
  box(1.6, 0.08, 1.35, M.metal, 0, 0.04, 0, 0.02, car);
  box(1.6, 0.08, 1.35, M.metal, 0, 2.3, 0, 0.02, car);
  box(0.05, 2.3, 0.05, M.metal, -0.78, 1.17, -0.64, 0, car);
  box(0.05, 2.3, 0.05, M.metal, 0.78, 1.17, -0.64, 0, car);
  box(1.3, 0.04, 0.04, glow("#ffd79a", 3), 0, 2.24, 0.55, 0, car);
  const carLight = new THREE.PointLight("#ffd7a0", 3, 3.5, 2);
  carLight.position.set(0, 1.9, 0);
  car.add(carLight);
  car.position.set(LIFT.x, 0, LIFT.z);
  scene.add(car);

  // per-row lights (9 total) + per-room ceiling panels and LED lines
  const rowLights = [];
  for (let f = 0; f < 3; f++) {
    for (let r = 1; r <= 3; r++) {
      const L = new THREE.PointLight("#ffe2b8", r === 1 ? 9 : 6, 10, 1.7);
      L.position.set(6, f * H + H - 0.5, (3 - r) * DR + DR / 2);
      floors[f].add(L);
      rowLights.push(L);
    }
  }

  for (const R of ALL_ROOMS) {
    const g = floors[R.f - 1], y = R.y, x0 = R.x0, cx = R.cx, zb = R.zBack;
    const fl = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.02, DR), new THREE.MeshStandardMaterial({ map: wood, color: mix("#ffffff", R.color, R.spare ? 0.0 : 0.06), roughness: 0.62 }));
    fl.rotation.x = -Math.PI / 2;
    fl.position.set(cx, y + 0.002, R.zc);
    fl.receiveShadow = true;
    g.add(fl);
    const panelMat = glow("#fff1d6", R.spare ? 0.25 : 2.0);
    const panel = box(1.3, 0.07, 0.42, panelMat, cx, y + H - 0.05, R.zc, 0.03, g);
    panel.castShadow = false;
    let led = null;
    if (R.r === 3) {
      led = box(W - 0.3, 0.04, 0.04, glow(R.color, R.spare ? 0.3 : 2.0), cx, y + H - 0.12, 0.02, 0, g);
      led.castShadow = false;
    }
    if (!R.spare) {
      const rug = new THREE.Mesh(new THREE.CircleGeometry(0.95, 40), std(mix("#2a2622", R.color, 0.32), { roughness: 1 }));
      rug.scale.set(1.25, 0.8, 1);
      rug.rotation.x = -Math.PI / 2;
      rug.position.set(cx + 0.5, y + 0.006, R.zc + 0.3);
      g.add(rug);
    }
    // props, kept off the centre lane (x = cx) so agents can walk through
    const P = R.props, bz = zb + 0.6;
    if (P === "lobby") {
      box(1.6, 0.9, 0.55, M.desk, cx + 0.7, y + 0.45, R.zc + 0.6, 0.08, g);
      box(1.7, 0.06, 0.62, M.top, cx + 0.7, y + 0.93, R.zc + 0.6, 0.03, g);
      const logo = new THREE.Mesh(new THREE.PlaneGeometry(2.1, 0.42), new THREE.MeshStandardMaterial({ color: "#000", emissive: "#fff", emissiveMap: textTex("PULSEAI", 512, 100, 58, "#f5a524"), emissiveIntensity: 1.8, transparent: true, alphaMap: textTex("PULSEAI", 512, 100, 58, "#fff", "#000") }));
      logo.position.set(cx, y + 2.0, zb + 0.02);
      if (R.r === 3) g.add(logo);
      plant(g, x0 + 0.5, y, bz, 1.1);
    } else if (P === "archive") {
      shelf(g, x0 + 1.0, y, zb + 0.3, 1.4);
      shelf(g, x0 + 3.1, y, zb + 0.3, 1.2);
    } else if (P === "watch") {
      for (let a = 0; a < 2; a++)
        for (let b = 0; b < 2; b++) {
          box(0.8, 0.48, 0.05, M.dark, x0 + 0.8 + b * 0.9, y + 1.35 + a * 0.56, zb + 0.4, 0.02, g);
          const s = new THREE.Mesh(new THREE.PlaneGeometry(0.72, 0.4), glow(["#c084fc", "#38bdf8"][(a + b) % 2], 1.2));
          s.position.set(x0 + 0.8 + b * 0.9, y + 1.35 + a * 0.56, zb + 0.43);
          g.add(s);
        }
    } else if (P === "research") {
      desk(g, x0 + 1.0, y, bz + 0.3, R.color, 1);
      shelf(g, x0 + 3.2, y, zb + 0.3, 1.0);
    } else if (P === "ops") desk(g, x0 + 1.1, y, bz + 0.3, R.color, 2, 1.6);
    else if (P === "planning") {
      box(1.6, 1.1, 0.06, M.white, x0 + 1.0, y + 1.6, zb + 0.32, 0.02, g);
      ["#818cf8", "#f472b6", "#38bdf8"].forEach((c, k) => box(0.5 + k * 0.25, 0.03, 0.01, glow(c, 0.9), x0 + 0.8 + k * 0.1, y + 1.9 - k * 0.2, zb + 0.36, 0, g));
    } else if (P === "director") {
      desk(g, x0 + 1.0, y, bz + 0.3, "#f5a524", 1, 1.6);
      plant(g, x0 + 3.5, y, bz, 0.9);
    } else if (P === "workshop") {
      box(1.8, 0.1, 0.7, M.desk, x0 + 1.1, y + 0.82, bz + 0.2, 0.02, g);
      box(1.7, 0.8, 0.6, M.dark, x0 + 1.1, y + 0.4, bz + 0.2, 0.04, g);
      box(0.6, 0.6, 0.6, std("#8b6a45", { roughness: 0.8 }), x0 + 3.4, y + 0.3, bz + 0.2, 0.04, g);
    } else {
      desk(g, x0 + 1.0, y, bz + 0.3, "#6b7280", 1, 1.2);
      if (rnd() < 0.5) plant(g, x0 + 3.5, y, bz, 0.8);
    }
    let label = null;
    const el = document.createElement("div");
    el.className = "wt-room-label";
    el.style.setProperty("--c", R.color);
    el.innerHTML = "<i></i>" + R.name;
    label = new CSS2DObject(el);
    label.position.set(x0 + 0.25, y + 0.05, zb + DR - 0.05);
    label.center.set(0, 0);
    label.visible = !R.spare;
    g.add(label);
    rooms[R.id] = Object.assign({}, R, { panelMat, led, label });
  }

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), std("#0b0a09", { roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.32;
  ground.receiveShadow = true;
  scene.add(ground);

  return {
    floors, roof, car, beacon, rooms,
    // light a spare room while someone uses it
    setOccupied(id, on) {
      const R = rooms[id];
      if (!R || !R.spare) return;
      R.panelMat.emissiveIntensity = on ? 2.0 : 0.25;
      if (R.led) R.led.material.emissiveIntensity = on ? 2.0 : 0.3;
      R.label.visible = on;
    },
  };
}
