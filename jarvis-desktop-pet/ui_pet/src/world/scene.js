// World tab 3D scene: renderer, camera, building, agent actors (doc 37 task 4.3).
// Actors are created, moved and removed only from store state (syncAgents).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { buildBuilding, roomGeom, CZ, LIFT, DOOR, H } from "./building.js";
import { buildChibi, buildPip } from "./chibi.js";

const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const HOME = { pos: new THREE.Vector3(20, 15.5, 33), target: new THREE.Vector3(6.4, 4.0, 5.8) };
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const easeOut = (p) => 1 - Math.pow(1 - p, 4);

export function slotFor(roomId, index = 0) {
  const R = roomGeom(roomId);
  if (!R) return null;
  return { x: R.cx + 0.75 + index * 0.6, y: R.y, z: R.zc + 0.35, room: R };
}

export function createScene(host, { lookFor, onPick } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  host.appendChild(renderer.domElement);
  const labels = new CSS2DRenderer();
  labels.domElement.className = "wt-labels";
  host.appendChild(labels.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#060607");
  scene.fog = new THREE.Fog("#060607", 40, 100);
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 220);
  camera.position.copy(HOME.pos);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(HOME.target);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 8, maxDistance: 60, minPolarAngle: 0.5, maxPolarAngle: 1.42, minAzimuthAngle: -1.0, maxAzimuthAngle: 1.05, screenSpacePanning: true });

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(256, 256), 0.36, 0.5, 0.9));
  composer.addPass(new OutputPass());

  scene.add(new THREE.HemisphereLight("#c3d3ff", "#3a2611", 0.55));
  const key = new THREE.DirectionalLight("#ffe3bf", 1.5);
  key.position.set(-10, 24, 30);
  key.target.position.set(6, 3, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -16, right: 16, top: 16, bottom: -14, near: 1, far: 90 });
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.03;
  scene.add(key, key.target);

  const B = buildBuilding(scene);
  const lift = { y: 0, target: 0 };
  let shownFloors = 3;
  const floorVisible = (y) => Math.floor((y + 0.5) / H) < shownFloors;

  const ring = (color, inner, outer, opacity) => {
    const m = new THREE.Mesh(new THREE.RingGeometry(inner, outer, 48), new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
    m.rotation.x = -Math.PI / 2;
    m.visible = false;
    scene.add(m);
    return m;
  };
  const selRing = ring("#f5f6f8", 0.4, 0.46, 0.9);
  let selected = null;

  // ---- actors ----
  const actors = new Map();

  function makeActor(agent, entering) {
    const isPip = agent.id === "pip";
    const model = isPip ? buildPip() : buildChibi(lookFor(agent));
    const group = new THREE.Group();
    group.add(model.root);
    model.root.traverse((o) => (o.userData.agentId = agent.id));
    scene.add(group);
    const el = document.createElement("div");
    el.className = "wt-tag";
    el.innerHTML = '<span class="wt-chip" hidden></span><span class="wt-name"></span>';
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      onPick && onPick(agent.id);
    });
    const tag = new CSS2DObject(el);
    tag.center.set(0.5, 1);
    scene.add(tag);
    const a = {
      id: agent.id, isPip, model, group, el, tag, queue: [], pos: new THREE.Vector3(), face: 0.3, restFace: 0.3,
      alpha: 1, hop: 0, t0: Math.random() * 10, vis: "idle", label: "", room: agent.room, leaving: false,
      lookKey: isPip ? "pip" : JSON.stringify(lookFor(agent)),
      approvalRing: ring("#f5a524", 0.36, 0.5, 0.8),
    };
    const s = slotFor(agent.room, 0);
    if (entering && s) {
      a.pos.set(DOOR.x, 0, DOOR.z);
      a.alpha = 0.01;
      a.queue.push({ fade: 1 }, ...route(a, s));
    } else if (s) a.pos.set(s.x, s.y, s.z);
    a.restFace = agent.room === "f1r1c1" ? 0 : 0.3;
    group.rotation.y = a.restFace;
    actors.set(agent.id, a);
    return a;
  }

  function route(a, s) {
    const steps = [];
    const here = roomGeom(a.room);
    const sameFloor = Math.abs(a.pos.y - s.y) < 0.1;
    if (a.pos.z < CZ - 0.2) steps.push({ to: [here ? here.cx : a.pos.x, a.pos.z] }, { to: [here ? here.cx : a.pos.x, CZ] });
    else steps.push({ to: [a.pos.x, CZ] });
    if (!sameFloor) steps.push({ to: [11.6, CZ] }, { call: true }, { to: [LIFT.x, LIFT.z] }, { ride: s.y }, { to: [11.6, CZ] });
    steps.push({ to: [s.room.cx, CZ] }, { to: [s.room.cx, s.z] }, { to: [s.x, s.z] });
    return steps;
  }

  function leave(a) {
    if (a.leaving) return;
    a.leaving = true;
    a.queue = [];
    const steps = [];
    const here = roomGeom(a.room);
    if (here && a.pos.z < CZ - 0.2) steps.push({ to: [here.cx, a.pos.z] }, { to: [here.cx, CZ] });
    if (a.pos.y > 0.1) steps.push({ to: [11.6, CZ] }, { call: true }, { to: [LIFT.x, LIFT.z] }, { ride: 0 }, { to: [11.6, CZ] });
    steps.push({ to: [0.4, CZ] }, { to: [DOOR.x, DOOR.z] }, { fade: 0 }, { remove: true });
    a.queue.push(...steps);
  }

  function disposeActor(a) {
    scene.remove(a.group, a.tag, a.approvalRing);
    a.el.remove();
    actors.delete(a.id);
    if (selected === a.id) selRing.visible = false;
  }

  function stepActor(a, dt, t) {
    const st = a.queue[0];
    let moving = false;
    if (st) {
      if (st.to) {
        const dx = st.to[0] - a.pos.x, dz = st.to[1] - a.pos.z, dist = Math.hypot(dx, dz), sp = 2.0 * dt;
        if (dist <= sp) {
          a.pos.x = st.to[0];
          a.pos.z = st.to[1];
          a.queue.shift();
        } else {
          a.pos.x += (dx / dist) * sp;
          a.pos.z += (dz / dist) * sp;
          a.face = Math.atan2(dx, dz);
          moving = true;
        }
      } else if (st.call) {
        lift.target = a.pos.y;
        if (Math.abs(lift.y - a.pos.y) < 0.01) a.queue.shift();
      } else if (st.ride !== undefined) {
        lift.target = st.ride;
        a.pos.y = lift.y;
        if (Math.abs(lift.y - st.ride) < 0.01) {
          a.pos.y = st.ride;
          a.queue.shift();
        }
      } else if (st.fade !== undefined) {
        a.alpha += Math.sign(st.fade - a.alpha) * dt * 2.4;
        if ((st.fade === 1 && a.alpha >= 1) || (st.fade === 0 && a.alpha <= 0.02)) {
          a.alpha = st.fade;
          a.queue.shift();
        }
      } else if (st.remove) {
        disposeActor(a);
        return;
      }
    }
    const g = a.group, r = a.model.rig, k = t + a.t0, amp = REDUCED ? 0 : 1;
    g.position.copy(a.pos);
    g.rotation.y += wrap((moving ? a.face : a.restFace) - g.rotation.y) * Math.min(1, dt * 8);
    if (a.hop > 0) {
      a.hop = Math.max(0, a.hop - dt);
      g.position.y += Math.sin((1 - a.hop / 0.6) * Math.PI) * 0.35;
    }
    g.scale.setScalar(Math.max(0.01, a.alpha));
    if (a.isPip) {
      r.body.scale.y = 1 + Math.sin(k * 2) * 0.025 * amp;
      g.position.y += Math.sin(k * 1.6) * 0.03 * amp;
    } else {
      const s = moving ? "walk" : a.vis;
      let lx = 0, rx = 0, rz = -0.18, hip = 0, tilt = 0, turn = 0;
      if (s === "walk") {
        const w = Math.sin(k * 11) * 0.7;
        hip = w;
        lx = -w * 0.8;
        rx = w * 0.8;
        g.position.y += Math.abs(Math.cos(k * 11)) * 0.05 * amp;
      } else if (s === "work") {
        lx = -1.15 + Math.sin(k * 14) * 0.12 * amp;
        rx = -1.15 + Math.cos(k * 15) * 0.12 * amp;
        tilt = 0.14;
      } else if (s === "approval") {
        rx = -2.95 + Math.sin(k * 6) * 0.12 * amp;
        rz = -0.25 + Math.sin(k * 6) * 0.2 * amp;
      } else if (s === "fail") tilt = 0.3;
      else {
        turn = Math.sin(k * 0.7) * 0.18 * amp;
        lx = Math.sin(k * 1.4) * 0.05 * amp;
        rx = -lx;
      }
      const e = Math.min(1, dt * 10);
      r.shL.rotation.x += (lx - r.shL.rotation.x) * e;
      r.shR.rotation.x += (rx - r.shR.rotation.x) * e;
      r.shR.rotation.z += (rz - r.shR.rotation.z) * e;
      r.hipL.rotation.x = hip;
      r.hipR.rotation.x = -hip;
      r.head.rotation.x += (tilt - r.head.rotation.x) * e;
      r.head.rotation.y += (turn - r.head.rotation.y) * e;
      r.body.scale.y = 1 + Math.sin(k * 2.2) * 0.02 * amp;
    }
    const vis = floorVisible(a.pos.y) && a.alpha > 0.02;
    g.visible = vis;
    a.tag.visible = vis;
    a.tag.position.set(a.pos.x, g.position.y + (a.isPip ? 1.62 : 1.5), a.pos.z);
    a.approvalRing.visible = vis && a.vis === "approval";
    if (a.approvalRing.visible) {
      const p = (t * 1.1) % 1;
      a.approvalRing.scale.setScalar(0.8 + p * 0.7);
      a.approvalRing.material.opacity = 0.85 * (1 - p);
      a.approvalRing.position.set(a.pos.x, a.pos.y + 0.02, a.pos.z);
    }
  }

  // ---- public sync from the store ----
  function syncAgents(agents, { synced, fresh, approvalAgent, labelFor }) {
    const ids = new Set(Object.keys(agents));
    for (const [id, a] of actors) if (!ids.has(id)) leave(a);
    const occupied = new Set();
    for (const ag of Object.values(agents)) {
      let a = actors.get(ag.id);
      if (!a) a = makeActor(ag, fresh && ag.kind !== "default");
      else if (a.leaving) continue;
      if (!a.isPip) {
        const lk = JSON.stringify(lookFor(ag));
        if (lk !== a.lookKey) {
          a.group.remove(a.model.root);
          a.model = buildChibi(lookFor(ag));
          a.model.root.traverse((o) => (o.userData.agentId = ag.id));
          a.group.add(a.model.root);
          a.lookKey = lk;
          a.hop = 0.6;
        }
      }
      if (ag.room !== a.room) {
        const s = slotFor(ag.room, 0);
        if (s) a.queue.push(...route(a, s));
        a.room = ag.room;
      }
      occupied.add(ag.room);
      const prev = a.vis;
      a.vis = ag.id === approvalAgent ? "approval" : ag.state === "working" ? "work" : "idle";
      if (prev === "work" && a.vis === "idle") a.hop = 0.6;
      const lab = a.vis === "approval" ? "needs you" : a.vis === "work" ? labelFor(ag) : "";
      const chip = a.el.querySelector(".wt-chip");
      chip.hidden = !lab;
      chip.textContent = lab;
      chip.className = "wt-chip " + a.vis;
      a.el.querySelector(".wt-name").textContent = ag.name;
      a.el.classList.toggle("temp", ag.kind === "temp");
      a.el.classList.toggle("sel", ag.id === selected);
    }
    for (const id of Object.keys(B.rooms)) B.setOccupied(id, occupied.has(id));
  }

  // ---- camera ----
  let camTween = null;
  function flyTo(target, pos, ms = 700) {
    const t0 = controls.target.clone(), p0 = camera.position.clone(), start = performance.now();
    camTween = (now) => {
      const p = REDUCED ? 1 : Math.min(1, (now - start) / ms), e = easeOut(p);
      controls.target.lerpVectors(t0, target, e);
      camera.position.lerpVectors(p0, pos, e);
      if (p >= 1) camTween = null;
    };
  }
  function setFloor(n) {
    shownFloors = n === 0 ? 3 : n;
    B.floors.forEach((g, i) => (g.visible = i < shownFloors));
    B.roof.visible = n === 0;
    if (n === 0) flyTo(HOME.target.clone(), HOME.pos.clone());
    else {
      const tgt = new THREE.Vector3(6.2, (n - 1) * H + 0.9, 5.6);
      flyTo(tgt, tgt.clone().add(new THREE.Vector3(10, 11, 19)));
    }
  }
  function focus(id) {
    const a = actors.get(id);
    if (!a) return;
    if (!floorVisible(a.pos.y)) setFloor(0);
    const tgt = new THREE.Vector3(a.pos.x, a.pos.y + 0.9, a.pos.z);
    flyTo(tgt, tgt.clone().add(new THREE.Vector3(4.5, 3.4, 9)));
  }
  function select(id) {
    selected = id;
    for (const [aid, a] of actors) a.el.classList.toggle("sel", aid === id);
  }

  // ---- picking ----
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  let downAt = null;
  renderer.domElement.addEventListener("pointerdown", (e) => (downAt = [e.clientX, e.clientY]));
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
    const rc = renderer.domElement.getBoundingClientRect();
    ptr.set(((e.clientX - rc.left) / rc.width) * 2 - 1, -((e.clientY - rc.top) / rc.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects([...actors.values()].map((a) => a.group), true).find((h) => h.object.visible && h.object.userData.agentId);
    if (hit && onPick) onPick(hit.object.userData.agentId);
  });

  // ---- loop (paused while the tab is hidden) ----
  let active = true, raf = 0;
  const clock = new THREE.Clock();
  function resize() {
    const w = host.clientWidth, h = host.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    labels.setSize(w, h);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.fov = w / h < 0.9 ? 46 : 32;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(host);
  resize();
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
    if (!active || document.hidden) return;
    if (camTween) camTween(now);
    controls.update();
    const ld = lift.target - lift.y;
    if (Math.abs(ld) > 0.001) lift.y += Math.sign(ld) * Math.min(Math.abs(ld), dt * 2.2);
    B.car.position.y = lift.y;
    for (const a of [...actors.values()]) stepActor(a, dt, t);
    const s = selected && actors.get(selected);
    selRing.visible = !!(s && s.group.visible);
    if (s) selRing.position.set(s.pos.x, s.pos.y + 0.015, s.pos.z);
    B.beacon.material.emissiveIntensity = 1 + (Math.sin(t * 3) > 0.6 ? 4 : 0);
    composer.render();
    labels.render(scene, camera);
  }
  raf = requestAnimationFrame(frame);

  return {
    syncAgents, setFloor, focus, select,
    home: () => setFloor(0),
    setActive(on) {
      active = !!on;
      if (on) resize();
    },
    hop(id) {
      const a = actors.get(id);
      if (a) a.hop = 0.6;
    },
    destroy() {
      cancelAnimationFrame(raf);
      renderer.dispose();
    },
  };
}
