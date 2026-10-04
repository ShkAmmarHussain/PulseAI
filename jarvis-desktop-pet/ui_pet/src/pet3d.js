import * as THREE from "./vendor/three.module.js";
import { Spring, Taffy, volumeScales } from "./pet_springs.js";

const container = document.getElementById("pet");
if (container) {
  const W = container.clientWidth || 176;
  const H = container.clientHeight || 198;

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(W, H);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, W / H, 0.1, 100);
  camera.position.set(0, 0.12, 6.3);
  camera.lookAt(0, -0.15, 0);

  scene.add(new THREE.HemisphereLight(0xcbb8ff, 0x1a1430, 1.05));
  const key = new THREE.DirectionalLight(0xffffff, 1.7); // dual soft specular #1
  key.position.set(2.5, 3.5, 4);
  scene.add(key);
  const rim = new THREE.PointLight(0x8b5cf6, 26, 14);
  rim.position.set(-3, -1.2, 2.5);
  scene.add(rim);
  const fill = new THREE.PointLight(0x5b8bff, 9, 12); // dual soft specular #2
  fill.position.set(3, -2, -2);
  scene.add(fill);

  // ---- continuous-curvature superellipse body (spec 29, section 5.5.2) ----
  const SUPER_N = 4.2;
  function sp(w, e) {
    return w < 0 ? -Math.pow(-w, e) : Math.pow(w, e);
  }
  function superellipsoid(a, b, c, n, su, sv) {
    const e = 2 / n;
    const pos = [];
    const uv = [];
    const idx = [];
    for (let i = 0; i <= su; i++) {
      const u = -Math.PI / 2 + (Math.PI * i) / su;
      const cu = Math.cos(u);
      const sn = Math.sin(u);
      for (let j = 0; j <= sv; j++) {
        const v = -Math.PI + (2 * Math.PI * j) / sv;
        const cv = Math.cos(v);
        const sv2 = Math.sin(v);
        pos.push(a * sp(cu, e) * sp(cv, e), b * sp(sn, e), c * sp(cu, e) * sp(sv2, e));
        uv.push(j / sv, i / su);
      }
    }
    for (let i = 0; i < su; i++) {
      for (let j = 0; j < sv; j++) {
        const p0 = i * (sv + 1) + j;
        const p1 = p0 + 1;
        const p2 = p0 + sv + 1;
        const p3 = p2 + 1;
        idx.push(p0, p2, p1, p1, p2, p3);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }

  // dual-pass material: warm matte silicone shell + internal luminous core
  const shellMat = new THREE.MeshPhysicalMaterial({
    color: 0xf0ecff,
    roughness: 0.55,
    metalness: 0.0,
    sheen: 0.6,
    sheenRoughness: 0.55,
    sheenColor: new THREE.Color(0xffffff),
    clearcoat: 0.18,
    clearcoatRoughness: 0.5,
    transparent: true,
    opacity: 0.92,
  });
  const accentMat = new THREE.MeshPhysicalMaterial({
    color: 0x8b7cf6,
    roughness: 0.3,
    metalness: 0.05,
    clearcoat: 0.4,
  });
  const faceMat = new THREE.MeshPhysicalMaterial({
    color: 0x221d38,
    roughness: 0.16,
    metalness: 0.1,
    clearcoat: 0.7,
    emissive: 0x171233,
    emissiveIntensity: 0.6,
  });
  const glowMat = new THREE.MeshBasicMaterial({ color: 0x8fe3ff });
  const glowMatDim = new THREE.MeshBasicMaterial({
    color: 0x8b7cf6,
    transparent: true,
    opacity: 0.9,
  });
  const browMat = new THREE.MeshStandardMaterial({
    color: 0xbfb2ff,
    emissive: 0x5b4bd8,
    emissiveIntensity: 0.7,
    roughness: 0.4,
  });
  const blushMat = new THREE.MeshBasicMaterial({
    color: 0xff9ed8,
    transparent: true,
    opacity: 0.5,
  });

  const robot = new THREE.Group();
  scene.add(robot);

  const head = new THREE.Group();
  head.position.y = 0.78;
  robot.add(head);

  const skull = new THREE.Mesh(superellipsoid(1.16, 1.13, 1.09, SUPER_N, 48, 64), shellMat);
  head.add(skull);

  const innerCore = new THREE.Mesh(
    superellipsoid(0.9, 0.87, 0.84, SUPER_N, 24, 32),
    new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  head.add(innerCore);

  const FA = 0.968, FB = 0.88, FC = 1.056, FCZ = 0.1;
  const face = new THREE.Mesh(superellipsoid(FA, FB, FC, SUPER_N, 40, 48), faceMat);
  face.position.z = FCZ;
  head.add(face);

  // spherical surface projection of facial elements (spec 29, section 5.5.3)
  const _n = new THREE.Vector3();
  function faceSurf(dx, dy, dz, out) {
    const l = Math.hypot(dx, dy, dz) || 1;
    const x = dx / l, y = dy / l, z = dz / l;
    const k = 1.015 / Math.sqrt((x * x) / (FA * FA) + (y * y) / (FB * FB) + (z * z) / (FC * FC));
    out.set(x * k, y * k, z * k + FCZ);
    return out;
  }
  function faceNormal(p, out) {
    out.set(p.x / (FA * FA), p.y / (FB * FB), (p.z - FCZ) / (FC * FC)).normalize();
    return out;
  }

  // capsule eye geometry (rounded squircle capsules, spec 29, section 5.5.3)
  function capsuleGeo(w, h, r) {
    const s = new THREE.Shape();
    const hw = w / 2, hh = h / 2;
    r = Math.min(r, hh, hw);
    s.moveTo(-hw + r, -hh);
    s.lineTo(hw - r, -hh);
    s.quadraticCurveTo(hw, -hh, hw, -hh + r);
    s.lineTo(hw, hh - r);
    s.quadraticCurveTo(hw, hh, hw - r, hh);
    s.lineTo(-hw + r, hh);
    s.quadraticCurveTo(-hw, hh, -hw, hh - r);
    s.lineTo(-hw, -hh + r);
    s.quadraticCurveTo(-hw, -hh, -hw + r, -hh);
    return new THREE.ShapeGeometry(s, 6);
  }
  const eyeGeo = capsuleGeo(0.3, 0.34, 0.13);
  const eyeL = new THREE.Mesh(eyeGeo, glowMat);
  const eyeR = new THREE.Mesh(eyeGeo, glowMat);
  head.add(eyeL, eyeR);

  const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const glintL = new THREE.Mesh(new THREE.CircleGeometry(0.05, 12), glintMat);
  const glintR = new THREE.Mesh(new THREE.CircleGeometry(0.05, 12), glintMat);
  glintL.position.set(0.06, 0.07, 0.012);
  glintR.position.set(0.06, 0.07, 0.012);
  eyeL.add(glintL);
  eyeR.add(glintR);

  const blushGeo = new THREE.CircleGeometry(0.13, 24);
  const blushL = new THREE.Mesh(blushGeo, blushMat);
  const blushR = new THREE.Mesh(blushGeo, blushMat);
  blushL.position.set(-0.64, -0.2, 1.15);
  blushR.position.set(0.64, -0.2, 1.15);
  blushL.scale.set(1, 0.7, 1);
  blushR.scale.set(1, 0.7, 1);
  head.add(blushL, blushR);

  const happyGeo = new THREE.TorusGeometry(0.17, 0.05, 10, 24, Math.PI);
  const happyL = new THREE.Mesh(happyGeo, glowMat);
  const happyR = new THREE.Mesh(happyGeo, glowMat);
  happyL.position.set(-0.36, 0.03, 1.17);
  happyR.position.set(0.36, 0.03, 1.17);
  happyL.rotation.z = Math.PI;
  happyR.rotation.z = Math.PI;
  happyL.visible = happyR.visible = false;
  head.add(happyL, happyR);

  const browGeo = new THREE.BoxGeometry(0.3, 0.05, 0.05);
  const browL = new THREE.Mesh(browGeo, browMat);
  const browR = new THREE.Mesh(browGeo, browMat);
  browL.position.set(-0.36, 0.4, 1.19);
  browR.position.set(0.36, 0.4, 1.19);
  browL.visible = browR.visible = false;
  head.add(browL, browR);

  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.038, 10, 24, Math.PI), glowMat);
  smile.position.set(0, -0.34, 1.17);
  smile.rotation.z = Math.PI;
  head.add(smile);

  const mouthOpen = new THREE.Mesh(new THREE.CircleGeometry(0.12, 24), glowMat);
  mouthOpen.position.set(0, -0.36, 1.17);
  mouthOpen.scale.set(1, 0.5, 1);
  mouthOpen.visible = false;
  head.add(mouthOpen);

  const earGeo = new THREE.SphereGeometry(0.2, 24, 18);
  const earL = new THREE.Mesh(earGeo, accentMat);
  const earR = new THREE.Mesh(earGeo, accentMat);
  earL.position.set(-1.14, 0, 0);
  earR.position.set(1.14, 0, 0);
  earL.scale.set(0.5, 1, 1);
  earR.scale.set(0.5, 1, 1);
  head.add(earL, earR);

  const antStick = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.46, 10), accentMat);
  antStick.position.y = 1.24;
  head.add(antStick);
  const antTip = new THREE.Mesh(new THREE.SphereGeometry(0.13, 20, 16), glowMat.clone());
  antTip.position.y = 1.54;
  head.add(antTip);
  const antGlow = new THREE.PointLight(0x8b5cf6, 4, 3);
  antGlow.position.y = 1.54;
  head.add(antGlow);

  const body = new THREE.Group();
  body.position.y = -0.88;
  robot.add(body);

  const torso = new THREE.Mesh(superellipsoid(0.6, 0.48, 0.53, SUPER_N, 36, 44), shellMat);
  body.add(torso);
  const bellyPatch = new THREE.Mesh(new THREE.CircleGeometry(0.2, 24), glowMatDim);
  bellyPatch.position.set(0, 0.02, 0.56);
  body.add(bellyPatch);
  const chestLight = new THREE.PointLight(0x8b5cf6, 2.6, 2.2);
  chestLight.position.set(0, 0.02, 0.8);
  body.add(chestLight);

  const handGeo = new THREE.SphereGeometry(0.17, 20, 16);
  const handL = new THREE.Mesh(handGeo, accentMat);
  const handR = new THREE.Mesh(handGeo, accentMat);
  handL.position.set(-0.76, -0.1, 0.15);
  handR.position.set(0.76, -0.1, 0.15);
  body.add(handL, handR);

  const footGeo = new THREE.SphereGeometry(0.21, 22, 16);
  const footL = new THREE.Mesh(footGeo, accentMat);
  const footR = new THREE.Mesh(footGeo, accentMat);
  footL.position.set(-0.3, -0.55, 0.14);
  footR.position.set(0.3, -0.55, 0.14);
  footL.scale.set(1, 0.62, 1.35);
  footR.scale.set(1, 0.62, 1.35);
  body.add(footL, footR);

  const glowCanvas = document.createElement("canvas");
  glowCanvas.width = glowCanvas.height = 128;
  const gctx = glowCanvas.getContext("2d");
  const grad = gctx.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, "rgba(167,139,250,0.75)");
  grad.addColorStop(0.45, "rgba(139,92,246,0.32)");
  grad.addColorStop(1, "rgba(139,92,246,0)");
  gctx.fillStyle = grad;
  gctx.fillRect(0, 0, 128, 128);
  const groundGlow = new THREE.Mesh(
    new THREE.CircleGeometry(1.7, 40),
    new THREE.MeshBasicMaterial({
      map: new THREE.CanvasTexture(glowCanvas),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  groundGlow.rotation.x = -Math.PI / 2;
  groundGlow.position.y = -1.58;
  robot.add(groundGlow);

  const ringMat = new THREE.MeshBasicMaterial({
    color: 0xa78bfa,
    transparent: true,
    opacity: 0,
    side: THREE.DoubleSide,
  });
  const rings = [0, 1].map((i) => {
    const r = new THREE.Mesh(new THREE.TorusGeometry(1.4, 0.02, 8, 64), ringMat.clone());
    r.position.y = -0.1;
    r.userData.phase = i * 0.5;
    robot.add(r);
    return r;
  });

  const orbMat = new THREE.MeshBasicMaterial({ color: 0xc4b5fd, transparent: true, opacity: 0 });
  const orbs = [0, 1, 2].map(() => {
    const o = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 10), orbMat.clone());
    robot.add(o);
    return o;
  });

  // magnetic particle stream for file ingestion (spec 29, section 5.5.6)
  const PCOUNT = 42;
  const pPos = new Float32Array(PCOUNT * 3);
  const pState = [];
  for (let i = 0; i < PCOUNT; i++) {
    pState.push({ a: Math.random() * Math.PI * 2, r: 1.3 + Math.random() * 1.5, w: 1.4 + Math.random() * 2.2 });
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute("position", new THREE.BufferAttribute(pPos, 3));
  const pMat = new THREE.PointsMaterial({
    color: 0x00f0ff,
    size: 0.075,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const particles = new THREE.Points(pGeo, pMat);
  robot.add(particles);
  let pOpacity = 0;

  const PRESETS = {
    idle: { lean: 0, tilt: 0, bob: 1, bobSpeed: 1.1, eyeSX: 1, eyeSY: 1, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1, ant: 1, brows: 0, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    listening: { lean: -0.17, tilt: 0, bob: 0.35, bobSpeed: 0.8, eyeSX: 1.1, eyeSY: 1.35, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1, ant: 3.4, brows: 0, happy: 0, rings: 1, orbs: 0, bounce: 0, nod: 0 },
    thinking: { lean: 0.02, tilt: 1, bob: 0.5, bobSpeed: 1.0, eyeSX: 1, eyeSY: 0.8, eyeX: 1, eyeY: 0, mouthO: 0, flat: 1, smileS: 0.6, ant: 1.6, brows: 1, happy: 0, rings: 0, orbs: 1, bounce: 0, nod: 0 },
    speaking: { lean: 0.04, tilt: 0, bob: 0.5, bobSpeed: 1.4, eyeSX: 1, eyeSY: 1.1, eyeX: 0, eyeY: 0, mouthO: 1, flat: 0, smileS: 1, ant: 2.6, brows: 0, happy: 0, rings: 1, orbs: 0, bounce: 0, nod: 1 },
    happy: { lean: -0.04, tilt: 0, bob: 1.2, bobSpeed: 1.7, eyeSX: 1, eyeSY: 1, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1.4, ant: 1.9, brows: 0, happy: 1, rings: 0, orbs: 0, bounce: 1, nod: 0 },
    concerned: { lean: 0.13, tilt: 0, bob: 0.2, bobSpeed: 0.7, eyeSX: 0.95, eyeSY: 0.9, eyeX: 0, eyeY: -0.4, mouthO: 0, flat: 1, smileS: 0.5, ant: 0.8, brows: 1.6, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    // --- spec 29 section 5.5.5: 10-state emotional reactivity machine ---
    curious: { lean: -0.06, tilt: 0.5, bob: 1.15, bobSpeed: 1.5, eyeSX: 1.25, eyeSY: 1.25, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1.2, ant: 2.2, brows: 0.4, happy: 0, rings: 0, orbs: 1, bounce: 0, nod: 0 },
    sleep: { lean: 0.17, tilt: 0, bob: 0.15, bobSpeed: 0.35, eyeSX: 1, eyeSY: 0.06, eyeX: 0, eyeY: 0.3, mouthO: 0, flat: 0.35, smileS: 0.7, ant: 0.35, brows: 0, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    poked: { lean: -0.02, tilt: 0, bob: 0.35, bobSpeed: 2.2, eyeSX: 1.15, eyeSY: 0.7, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1.6, ant: 3.0, brows: 0.8, happy: 1, rings: 0, orbs: 0, bounce: 1, nod: 0 },
    dizzy: { lean: 0.05, tilt: 1, bob: 0.6, bobSpeed: 3.6, eyeSX: 1.05, eyeSY: 1.05, eyeX: 1, eyeY: 0, mouthO: 0, flat: 1, smileS: 0.4, ant: 4.5, brows: 1.8, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    ingesting: { lean: -0.14, tilt: 0, bob: 0.45, bobSpeed: 1.9, eyeSX: 1.15, eyeSY: 1.3, eyeX: 0, eyeY: 0, mouthO: 1, flat: 0, smileS: 1, ant: 4.2, brows: 0.3, happy: 0.6, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    executing: { lean: 0.08, tilt: 0, bob: 0.55, bobSpeed: 1.25, eyeSX: 1, eyeSY: 0.82, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0.4, smileS: 0.9, ant: 3.0, brows: 0.9, happy: 0, rings: 0, orbs: 1, bounce: 0, nod: 0.6 },
    approval: { lean: 0.03, tilt: 0, bob: 0.4, bobSpeed: 1.3, eyeSX: 1.1, eyeSY: 1.22, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 0.8, ant: 5, brows: 1.3, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
  };

  const cur = Object.assign({}, PRESETS.idle);
  let target = Object.assign({}, PRESETS.idle);
  let mood = "idle";
  let blinkAt = 2.5;
  let blink = 0;

  // saccadic gaze: spring-damped micro-steps toward the cursor (section 5.5.3)
  const sac = {
    x: new Spring(38, 0.8, 0),
    y: new Spring(38, 0.8, 0),
    next: 0,
    cursor: { x: 0, y: 0, in: false },
  };
  window.addEventListener("mousemove", (e) => {
    const cw = container.clientWidth || W;
    const ch = container.clientHeight || H;
    if (e.clientX >= 0 && e.clientX <= cw && e.clientY >= 0 && e.clientY <= ch) {
      sac.cursor.x = (e.clientX / cw) * 2 - 1;
      sac.cursor.y = -((e.clientY / ch) * 2 - 1);
      sac.cursor.in = true;
    } else {
      sac.cursor.in = false;
    }
  }, { passive: true });

  // internal luminous core colour per state (spec 29, section 5.5.2)
  const CORE = {
    idle: 0x00f0ff, listening: 0x00f0ff, thinking: 0xa855f7, speaking: 0x00f0ff,
    happy: 0x10b981, concerned: 0xf59e0b, curious: 0x00f0ff, sleep: 0xf59e0b,
    poked: 0x10b981, dizzy: 0xa855f7, ingesting: 0xa855f7, executing: 0xa855f7,
    approval: 0xf59e0b,
  };
  const coreCol = new THREE.Color(CORE.idle);
  const whiteCol = new THREE.Color(0xffffff);
  let glowTargetMul = 1;
  let glowMul = 1;
  let coreFlash = 0;
  function applyCore(m) {
    coreCol.setHex(CORE[m] || CORE.idle);
    rim.color.copy(coreCol);
    chestLight.color.copy(coreCol);
    innerCore.material.color.copy(coreCol);
    pMat.color.copy(coreCol);
    glowTargetMul = m === "sleep" ? 0.15 : 1; // eco-sleep dims the rim to an ember
  }

  // modular colorway / theme engine (spec 29, sections 5.5.7 / roadmap h)
  const COLORWAYS = {
    obsidian: { shell: 0x17181d, accent: 0x00f0ff, face: 0x0a0b10, glow: 0x8fe3ff, rough: 0.45, opacity: 0.94, blush: 0.4 },
    porcelain: { shell: 0xf4efe7, accent: 0xc4b5fd, face: 0x3a3550, glow: 0xd8ccff, rough: 0.68, opacity: 0.96, blush: 0.8 },
    cyberpunk: { shell: 0x2a1440, accent: 0xff3d9a, face: 0x160b26, glow: 0xf59e0b, rough: 0.32, opacity: 0.93, blush: 0.55 },
    titanium: { shell: 0xdfe6ee, accent: 0x9fd8ff, face: 0x9aa8b8, glow: 0xbfeaff, rough: 0.2, opacity: 0.72, blush: 0.3 },
  };
  let colorway = "obsidian";
  function applyColorway(key) {
    const cw = COLORWAYS[key];
    if (!cw) return;
    colorway = key;
    shellMat.color.setHex(cw.shell);
    shellMat.roughness = cw.rough;
    shellMat.opacity = cw.opacity;
    accentMat.color.setHex(cw.accent);
    faceMat.color.setHex(cw.face);
    glowMat.color.setHex(cw.glow);
    glowMatDim.color.setHex(cw.glow);
    bellyPatch.material.color.setHex(cw.glow);
    blushMat.opacity = cw.blush;
  }
  applyColorway("obsidian");

  // file ingestion animation state (spec 29, sections 5.2 / 5.5.6)
  const ingest = { active: false, x: 0, y: 0, dropAt: -1e9 };
  let gulpAmt = 0;

  // tactile physics: squash spring + poke wobble + taffy drag (section 5.5.4)
  const sq = new Spring(18.5, 0.65, 1);
  const leanS = new Spring(20, 0.55, 0);
  const taffy = new Taffy();
  let taffyIdle = 0;

  window.Pet3D = {
    setMood(m) {
      if (PRESETS[m]) {
        mood = m;
        target = Object.assign({}, PRESETS[m]);
        applyCore(m);
        if (m === "happy") sq.impulse(-1.4);
        if (m === "poked") sq.impulse(-1.8);
      }
    },
    mood: () => mood,
    poke(nx, ny) {
      nx = Math.max(-1, Math.min(1, nx || 0));
      ny = Math.max(-1, Math.min(1, ny || 0));
      sq.impulse(-(1.8 + Math.random() * 0.6));           // 1.8-2.4 impulse (section 5.5.4)
      leanS.impulse(nx * 1.5 + (Math.random() - 0.5) * 0.6);
      coreFlash = 1;
    },
    stretch(vx, vy) {
      taffy.drag(vx, vy);
      taffyIdle = 0;
    },
    stretchEnd() {
      taffy.release();
    },
    applyColorway,
    ingestHover(pos) {
      ingest.active = true;
      if (pos && pos.length >= 2) {
        const cw = container.clientWidth || W;
        const ch = container.clientHeight || H;
        if (pos[0] >= 0 && pos[0] <= cw) ingest.x = (pos[0] / cw) * 2 - 1;
        if (pos[1] >= 0 && pos[1] <= ch) ingest.y = (pos[1] / ch) * 2 - 1;
      }
    },
    ingestDrop() {
      ingest.dropAt = performance.now();
      gulpAmt = 1;
      coreFlash = 1.4;
      sq.impulse(-2.2);                                    // gulp/crunch bounce
      ingest.active = false;
    },
    ingestEnd() {
      ingest.active = false;
      ingest.x = ingest.y = 0;
    },
    debug() {
      return {
        mood,
        colorway,
        geometry: "superellipse",
        n: SUPER_N,
        eyeL: [eyeL.position.x, eyeL.position.y, eyeL.position.z].map((v) => +v.toFixed(3)),
        eyeR: [eyeR.position.x, eyeR.position.y, eyeR.position.z].map((v) => +v.toFixed(3)),
        squash: +sq.x.toFixed(4),
        squashV: +sq.v.toFixed(3),
        taffy: [+taffy.x.x.toFixed(4), +taffy.y.x.toFixed(4)],
        particles: +pOpacity.toFixed(2),
        fpsInterval: Math.round(renderBudget),
        renders: renderCount,
        core: "#" + coreCol.getHexString(),
        glowMul: +glowMul.toFixed(3),
        coreFlash: +coreFlash.toFixed(2),
      };
    },
  };
  applyCore("idle");

  const damp = (a, b, lambda, dt) => a + (b - a) * (1 - Math.exp(-lambda * dt));
  const _ep = new THREE.Vector3();
  const _q = new THREE.Quaternion();
  const _zAxis = new THREE.Vector3(0, 0, 1);
  const baseDirL = new THREE.Vector3(-0.36, 0.01, 1).normalize();
  const baseDirR = new THREE.Vector3(0.36, 0.01, 1).normalize();

  // adaptive 60 / 10 / 1 FPS render loop (spec 29, section 5.5.8)
  let renderBudget = 1000 / 60;
  let renderCount = 0;
  let lastFrameAt = performance.now();
  let t = 0;

  function frame(now) {
    requestAnimationFrame(frame);
    const interval = document.hidden ? 1000 : renderBudget;
    if (now - lastFrameAt < interval) return;
    const rawDt = (now - lastFrameAt) / 1000;
    lastFrameAt = now;
    renderCount++;
    const dt = Math.min(rawDt, 0.1);
    t += dt;

    for (const k of Object.keys(target)) cur[k] = damp(cur[k], target[k], 5, dt);

    sq.step(dt);
    leanS.step(dt);
    taffy.step(dt);
    taffyIdle += dt;
    if (taffyIdle > 0.12 && taffy.x.target !== 0) taffy.release(); // snap-back when drag events stop

    const vs = volumeScales(sq.x);
    const tsx = 1 + taffy.x.x;
    const tsy = 1 + taffy.y.x;
    const tsz = 1 - (taffy.x.x + taffy.y.x) * 0.45;
    body.scale.set(vs.sx * tsx, vs.sy * tsy, vs.sz * tsz);
    head.scale.set(1 + (1 - vs.sx * tsx) * 0.5, 1 + (1 - vs.sy * tsy) * 0.35, 1 + (1 - vs.sz * tsz) * 0.5);

    robot.position.y = Math.sin(t * cur.bobSpeed * 2.1) * 0.06 * cur.bob;
    head.rotation.x = cur.lean + Math.sin(t * 7) * 0.06 * cur.nod;
    head.rotation.z = cur.tilt * Math.sin(t * 2.6) * 0.16 + leanS.x * 0.2;

    // saccadic gaze target: cursor + preset bias + micro-jitter (section 5.5.3)
    sac.next -= dt;
    if (mood === "dizzy") {
      // spinning spiral eyes (spec 29, section 5.5.5)
      sac.x.target = Math.sin(t * 9) * 0.9;
      sac.y.target = Math.cos(t * 9) * 0.75;
      sac.next = 0.4;
    } else if (sac.next <= 0) {
      const biasX = cur.eyeX * 0.6;
      const biasY = cur.eyeY * 0.55 + (cur.eyeX > 0.5 ? 0.45 : 0);
      const jx = (Math.random() - 0.5) * 0.4;
      const jy = (Math.random() - 0.5) * 0.3;
      const cx = sac.cursor.in ? sac.cursor.x * 0.75 : 0;
      const cy = sac.cursor.in ? sac.cursor.y * 0.7 : 0;
      sac.x.target = Math.max(-1, Math.min(1, biasX + cx + jx));
      sac.y.target = Math.max(-1, Math.min(1, biasY + cy + jy));
      sac.next = 0.4 + Math.random() * 0.7;
    }
    sac.x.step(dt);
    sac.y.step(dt);

    blinkAt -= dt;
    if (blinkAt <= 0 && mood !== "happy" && mood !== "dizzy" && mood !== "poked") {
      blink = 1;
      blinkAt = (Math.random() < 0.22 ? 0.18 : 0) + 2.5 + Math.random() * 3.5; // occasional double-blink
    }
    if (blink > 0) blink = Math.max(0, blink - dt * 9);
    const blinkCurve = 1 - Math.sin(Math.min(blink, 1) * Math.PI) * 0.96;
    const halfLid = mood === "idle" ? 0.93 + Math.sin(t * 0.55) * 0.07 : 1; // relaxed half-lids

    const canBlink = mood === "idle" || mood === "listening" || mood === "speaking" || mood === "curious" || mood === "executing";
    const sy = cur.eyeSY * (canBlink ? blinkCurve : 1) * halfLid;
    eyeL.scale.set(cur.eyeSX, sy, 1);
    eyeR.scale.set(cur.eyeSX, sy, 1);

    // spherical projection: place each eye on the face ellipsoid along the gaze dir
    const gx = sac.x.x * 0.2;
    const gy = sac.y.x * 0.16;
    for (const [eye, base] of [[eyeL, baseDirL], [eyeR, baseDirR]]) {
      _n.copy(base);
      _n.x += gx;
      _n.y += gy;
      faceSurf(_n.x, _n.y, _n.z, _ep);
      eye.position.copy(_ep);
      faceNormal(_ep, _n);
      _q.setFromUnitVectors(_zAxis, _n);
      eye.quaternion.copy(_q);
    }

    const blinkVisible = canBlink && blink < 0.05 && sy > 0.6;
    blushL.visible = blushR.visible = mood !== "thinking" || cur.happy > 0.5;

    const happyOn = cur.happy > 0.5;
    happyL.visible = happyR.visible = happyOn;
    eyeL.visible = eyeR.visible = !happyOn;
    glintL.visible = glintR.visible = blinkVisible && !happyOn;

    const browOn = cur.brows > 0.06;
    browL.visible = browR.visible = browOn;
    if (browOn) {
      browL.position.y = 0.4 + gy * 0.4;
      browR.position.y = 0.4 + gy * 0.4;
      browL.rotation.z = -0.42 * cur.brows;
      browR.rotation.z = 0.42 * cur.brows;
    }

    const openMouth = cur.mouthO > 0.5;
    mouthOpen.visible = openMouth;
    smile.visible = !openMouth;
    if (openMouth) {
      const osc = 0.55 + Math.abs(Math.sin(t * 11)) * 0.75;
      mouthOpen.scale.set(1.05 - (osc - 0.55) * 0.25, osc, 1);
    } else {
      smile.scale.set(cur.smileS, (1 - cur.flat * 0.7) * cur.smileS, 1);
    }

    const antPulse = 0.85 + Math.sin(t * cur.ant * 2.4) * 0.35;
    glowMul = glowMul + (glowTargetMul - glowMul) * (1 - Math.exp(-3 * dt));
    coreFlash = Math.max(0, coreFlash - dt * 2.4);
    const flash = 1 + coreFlash;
    rim.intensity = 26 * glowMul;
    chestLight.intensity = 2.6 * glowMul * flash;
    innerCore.material.opacity = (0.12 + coreFlash * 0.45) * glowMul;
    innerCore.scale.setScalar(1 + coreFlash * 0.05);
    antTip.material.color.copy(coreCol).lerp(whiteCol, antPulse * 0.22);
    antTip.scale.setScalar(1 + Math.sin(t * cur.ant * 2.4) * 0.15 + coreFlash * 0.3);
    antGlow.intensity = (2.5 + antPulse * 2.5) * glowMul;
    if (ingest.active) {
      head.rotation.x += ingest.y * 0.1;
      head.rotation.z += ingest.x * 0.14;
    }

    gulpAmt *= Math.exp(-dt * 6);
    const hop = Math.max(cur.bounce, gulpAmt);
    if (hop > 0.05) {
      const b = Math.abs(Math.sin(t * 6.5));
      robot.position.y += b * 0.1 * hop;
    }
    handL.position.y = -0.1 + Math.sin(t * 1.4) * 0.05;
    handR.position.y = -0.1 + Math.sin(t * 1.4 + 0.6) * 0.05;
    if (hop > 0.05) {
      handL.rotation.z = Math.sin(t * 9) * 0.5;
      handR.rotation.z = -Math.sin(t * 9) * 0.5;
    } else {
      handL.rotation.z = damp(handL.rotation.z, 0, 6, dt);
      handR.rotation.z = damp(handR.rotation.z, 0, 6, dt);
    }

    // ingestion particle stream: cursor -> core spiral (spec 29, section 5.5.6)
    const pTarget = ingest.active ? 0.9 : 0;
    pOpacity = pOpacity + (pTarget - pOpacity) * (1 - Math.exp(-6 * dt));
    pMat.opacity = pOpacity;
    if (pOpacity > 0.02) {
      for (let i = 0; i < PCOUNT; i++) {
        const p = pState[i];
        p.a += p.w * dt * (ingest.active ? 2.4 : 0.6);
        if (ingest.active) {
          p.r -= dt * (1.7 + p.w * 0.5);
          if (p.r < 0.18) {
            p.r = 1.5 + Math.random() * 1.3;
            p.a = Math.atan2(-ingest.y, ingest.x) + (Math.random() - 0.5) * 1.2;
          }
        }
        const biasX = ingest.x * 0.9;
        const biasY = -ingest.y * 0.75;
        pPos[i * 3] = Math.cos(p.a) * p.r * 0.75 + biasX * (2 - p.r) * 0.3;
        pPos[i * 3 + 1] = 0.2 + Math.sin(p.a) * p.r * 0.6 + biasY * (2 - p.r) * 0.3;
        pPos[i * 3 + 2] = Math.sin(p.a * 1.7) * 0.4 + 0.6;
      }
      pGeo.attributes.position.needsUpdate = true;
    }

    groundGlow.material.opacity = 0.75 + Math.sin(t * 1.3) * 0.12;

    for (const r of rings) {
      const amt = cur.rings;
      if (amt < 0.03) {
        r.material.opacity = 0;
        continue;
      }
      const p = (t * 0.75 + r.userData.phase) % 1;
      const s = 0.55 + p * 0.85;
      r.scale.set(s, s, s);
      r.material.opacity = (1 - p) * 0.55 * amt;
    }

    for (let i = 0; i < orbs.length; i++) {
      const o = orbs[i];
      if (cur.orbs < 0.03) {
        o.material.opacity = 0;
        continue;
      }
      const a = t * 1.7 + (i * Math.PI * 2) / 3;
      o.position.set(Math.cos(a) * 1.5, 0.85 + Math.sin(a * 1.7) * 0.28, Math.sin(a) * 0.9);
      o.material.opacity = 0.85 * cur.orbs;
    }

    renderer.render(scene, camera);

    // adaptive throttling: 60 FPS active, 10 FPS static idle, 1 FPS hidden
    const busy =
      mood !== "idle" || ingest.active ||
      Math.abs(sq.x - 1) > 0.002 || Math.abs(sq.v) > 0.02 ||
      Math.abs(taffy.x.x) > 0.002 || Math.abs(taffy.y.x) > 0.002 ||
      Math.abs(leanS.x) > 0.002 || pOpacity > 0.03 ||
      blink > 0 || cur.rings > 0.03 || cur.orbs > 0.03 ||
      sac.cursor.in || taffyIdle < 1.2;
    renderBudget = busy ? 1000 / 60 : 1000 / 10;
  }
  requestAnimationFrame(frame);
}
