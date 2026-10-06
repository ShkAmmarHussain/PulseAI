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
  const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 100);
  camera.position.set(0, 0.3, 9.8);
  camera.lookAt(0, 0.22, 0);

  // warm diffuse desk-lamp lighting (doc 30, section 4.3)
  scene.add(new THREE.HemisphereLight(0xfff6ea, 0x584a52, 1.2));
  const key = new THREE.DirectionalLight(0xffeedd, 1.8);
  key.position.set(2.5, 4.0, 4.5);
  scene.add(key);
  const rim = new THREE.PointLight(0xffb07c, 18, 12);
  rim.position.set(-3.2, -1.0, 2.5);
  scene.add(rim);
  const fillLight = new THREE.PointLight(0xffe4c4, 5, 12);
  fillLight.position.set(1.8, -1.4, 3.6);
  scene.add(fillLight);

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

  // cozy soft matte ceramic material with subsurface-scattering feel (doc 30, 4.3)
  const shellMat = new THREE.MeshPhysicalMaterial({
    color: 0xfcf9f2,
    roughness: 0.38,
    metalness: 0.04,
    transmission: 0.08,
    ior: 1.45,
    sheen: 1.0,
    sheenRoughness: 0.5,
    sheenColor: new THREE.Color(0xffdfd0),
    clearcoat: 0.12,
    clearcoatRoughness: 0.4,
    transparent: true,
    opacity: 0.95,
  });
  const accentMat = new THREE.MeshPhysicalMaterial({
    color: 0xfb923c,
    roughness: 0.4,
    metalness: 0.02,
    clearcoat: 0.2,
  });
  // dark warm ink for eyes / smile / brows on the light face
  const featureMat = new THREE.MeshStandardMaterial({
    color: 0x35292a,
    roughness: 0.55,
    metalness: 0.0,
  });
  const glowMat = new THREE.MeshBasicMaterial({ color: 0xffc98a });
  const glowMatDim = new THREE.MeshBasicMaterial({
    color: 0xffc98a,
    transparent: true,
    opacity: 0.9,
  });
  const browMat = new THREE.MeshStandardMaterial({
    color: 0x8a6a4c,
    roughness: 0.6,
  });
  const blushMat = new THREE.MeshBasicMaterial({
    color: 0xff9e9e,
    transparent: true,
    opacity: 0.65,
  });
  const innerEarMat = new THREE.MeshStandardMaterial({
    color: 0xf0c9a8,
    roughness: 0.55,
    metalness: 0.0,
  });

  const robot = new THREE.Group();
  scene.add(robot);

  // single-piece squishy "Mochi" body (doc 30 course correction): one seamless
  // squircle dumpling with soft ear nubs - no antenna, screen face, or torso
  const body = new THREE.Group();
  body.position.y = 0.1;
  robot.add(body);

  const shell = new THREE.Mesh(superellipsoid(1.2, 1.16, 1.1, SUPER_N, 48, 64), shellMat);
  body.add(shell);

  const innerCore = new THREE.Mesh(
    superellipsoid(0.94, 0.9, 0.86, SUPER_N, 24, 32),
    new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  body.add(innerCore);

  // soft warm inner glow (state colour) living inside the marshmallow
  const innerLight = new THREE.PointLight(0xf59e0b, 2.2, 4.5);
  innerLight.position.set(0, 0, 0.55);
  body.add(innerLight);

  // projection surface = the body itself (no separate face panel)
  const FA = 1.2, FB = 1.16, FC = 1.1, FCZ = 0;
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

  // soft rounded bunny ear nubs - same shell colour so the piece reads seamless
  const earGeo = new THREE.SphereGeometry(0.3, 24, 18);
  const earL = new THREE.Mesh(earGeo, shellMat);
  const earR = new THREE.Mesh(earGeo, shellMat);
  earL.position.set(-0.58, 1.16, -0.02);
  earR.position.set(0.58, 1.16, -0.02);
  earL.scale.set(0.6, 0.95, 0.55);
  earR.scale.set(0.6, 0.95, 0.55);
  earL.rotation.z = 0.3;
  earR.rotation.z = -0.3;
  body.add(earL, earR);
  const innerEarGeo = new THREE.SphereGeometry(0.16, 16, 12);
  const innerEarL = new THREE.Mesh(innerEarGeo, innerEarMat);
  const innerEarR = new THREE.Mesh(innerEarGeo, innerEarMat);
  innerEarL.position.set(-0.6, 1.19, 0.11);
  innerEarR.position.set(0.6, 1.19, 0.11);
  innerEarL.scale.set(0.5, 0.75, 0.45);
  innerEarR.scale.set(0.5, 0.75, 0.45);
  body.add(innerEarL, innerEarR);

  // spherical surface projection helpers for facial elements (spec 29, 5.5.3)
  const _n = new THREE.Vector3();

  // large expressive squircle eyes (not slits!) with curved eyelid rims
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
  const eyeGeo = capsuleGeo(0.4, 0.48, 0.2);
  const eyeL = new THREE.Mesh(eyeGeo, featureMat);
  const eyeR = new THREE.Mesh(eyeGeo, featureMat);
  body.add(eyeL, eyeR);

  // curved upper-eyelid rim riding the top edge of each eye
  const lidGeo = new THREE.TorusGeometry(0.2, 0.034, 8, 24, Math.PI);
  const lidL = new THREE.Mesh(lidGeo, featureMat);
  const lidR = new THREE.Mesh(lidGeo, featureMat);
  lidL.position.set(0, 0.2, 0.012);
  lidR.position.set(0, 0.2, 0.012);
  eyeL.add(lidL);
  eyeR.add(lidR);

  const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const glintL = new THREE.Mesh(new THREE.CircleGeometry(0.08, 14), glintMat);
  const glintR = new THREE.Mesh(new THREE.CircleGeometry(0.08, 14), glintMat);
  glintL.position.set(0.08, 0.1, 0.014);
  glintR.position.set(0.08, 0.1, 0.014);
  eyeL.add(glintL);
  eyeR.add(glintR);
  const sparkL = new THREE.Mesh(new THREE.CircleGeometry(0.042, 10), glintMat);
  const sparkR = new THREE.Mesh(new THREE.CircleGeometry(0.042, 10), glintMat);
  sparkL.position.set(-0.07, -0.09, 0.014);
  sparkR.position.set(-0.07, -0.09, 0.014);
  sparkL.userData.spark = sparkR.userData.spark = true;
  eyeL.add(sparkL);
  eyeR.add(sparkR);

  // warm soft blush cheeks on the body front (oriented to the surface normal)
  const blushGeo = new THREE.CircleGeometry(0.2, 24);
  const blushL = new THREE.Mesh(blushGeo, blushMat);
  const blushR = new THREE.Mesh(blushGeo, blushMat);
  const _bp = new THREE.Vector3();
  const _bn = new THREE.Vector3();
  const _fwd = new THREE.Vector3(0, 0, 1);
  faceSurf(-0.56, -0.17, 1, _bp);
  faceNormal(_bp, _bn);
  blushL.position.copy(_bp).addScaledVector(_bn, 0.05);
  blushL.quaternion.setFromUnitVectors(_fwd, _bn);
  faceSurf(0.56, -0.17, 1, _bp);
  faceNormal(_bp, _bn);
  blushR.position.copy(_bp).addScaledVector(_bn, 0.05);
  blushR.quaternion.setFromUnitVectors(_fwd, _bn);
  blushL.scale.set(1, 0.7, 1);
  blushR.scale.set(1, 0.7, 1);
  body.add(blushL, blushR);

  // closed happy eyes (curved arcs at eye level)
  const happyGeo = new THREE.TorusGeometry(0.2, 0.05, 10, 24, Math.PI);
  const happyL = new THREE.Mesh(happyGeo, featureMat);
  const happyR = new THREE.Mesh(happyGeo, featureMat);
  faceSurf(-0.34, 0.16, 1, _bp);
  happyL.position.set(_bp.x, _bp.y, _bp.z + 0.05);
  faceSurf(0.34, 0.16, 1, _bp);
  happyR.position.set(_bp.x, _bp.y, _bp.z + 0.05);
  happyL.rotation.z = Math.PI;
  happyR.rotation.z = Math.PI;
  happyL.visible = happyR.visible = false;
  body.add(happyL, happyR);

  const browGeo = new THREE.BoxGeometry(0.28, 0.055, 0.05);
  const browL = new THREE.Mesh(browGeo, browMat);
  const browR = new THREE.Mesh(browGeo, browMat);
  faceSurf(-0.36, 0.52, 1, _bp);
  browL.position.set(_bp.x, _bp.y, _bp.z + 0.05);
  faceSurf(0.36, 0.52, 1, _bp);
  browR.position.set(_bp.x, _bp.y, _bp.z + 0.05);
  browL.visible = browR.visible = false;
  body.add(browL, browR);

  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.042, 10, 24, Math.PI), featureMat);
  faceSurf(0, -0.34, 1, _bp);
  smile.position.set(_bp.x, _bp.y, _bp.z + 0.045);
  smile.rotation.z = Math.PI;
  body.add(smile);

  const mouthOpen = new THREE.Mesh(new THREE.CircleGeometry(0.13, 24), featureMat);
  faceSurf(0, -0.36, 1, _bp);
  mouthOpen.position.set(_bp.x, _bp.y, _bp.z + 0.045);
  mouthOpen.scale.set(1, 0.5, 1);
  mouthOpen.visible = false;
  body.add(mouthOpen);

  const glowCanvas = document.createElement("canvas");
  glowCanvas.width = glowCanvas.height = 128;
  const gctx = glowCanvas.getContext("2d");
  const grad = gctx.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, "rgba(251,146,60,0.7)");
  grad.addColorStop(0.45, "rgba(245,158,11,0.3)");
  grad.addColorStop(1, "rgba(245,158,11,0)");
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
  groundGlow.position.y = -1.14;
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
    idle: 0xf59e0b, listening: 0xfbbf24, thinking: 0xa855f7, speaking: 0xfbbf24,
    happy: 0x10b981, concerned: 0xf59e0b, curious: 0xffb07c, sleep: 0xf59e0b,
    poked: 0x10b981, dizzy: 0xa855f7, ingesting: 0xa855f7, executing: 0xa855f7,
    approval: 0xf59e0b,
  };
  const coreCol = new THREE.Color(CORE.idle);
  let glowTargetMul = 1;
  let glowMul = 1;
  let coreFlash = 0;
  function applyCore(m) {
    coreCol.setHex(CORE[m] || CORE.idle);
    innerLight.color.copy(coreCol);
    innerCore.material.color.copy(coreCol);
    pMat.color.copy(coreCol);
    glowTargetMul = m === "sleep" ? 0.15 : 1; // eco-sleep dims the rim to an ember
  }

  // modular colorway / theme engine (spec 29, sections 5.5.7 / roadmap h;
  // `ink` is the dark/light feature color for eyes + smile on the face panel)
  const COLORWAYS = {
    porcelain: { shell: 0xfcf9f2, accent: 0xfb923c, face: 0xf0e2cf, ink: 0x35292a, glow: 0xffc98a, rough: 0.38, opacity: 0.95, blush: 0.85 },
    obsidian: { shell: 0x17181d, accent: 0x00f0ff, face: 0x0a0b10, ink: 0x8fe3ff, glow: 0x8fe3ff, rough: 0.45, opacity: 0.94, blush: 0.4 },
    cyberpunk: { shell: 0x2a1440, accent: 0xff3d9a, face: 0x160b26, ink: 0xffc2d9, glow: 0xf59e0b, rough: 0.32, opacity: 0.93, blush: 0.55 },
    titanium: { shell: 0xdfe6ee, accent: 0x9fd8ff, face: 0x9aa8b8, ink: 0x2e3742, glow: 0xbfeaff, rough: 0.2, opacity: 0.72, blush: 0.3 },
  };
  let colorway = "porcelain";
  function applyColorway(key) {
    const cw = COLORWAYS[key];
    if (!cw) return;
    colorway = key;
    shellMat.color.setHex(cw.shell);
    shellMat.roughness = cw.rough;
    shellMat.opacity = cw.opacity;
    accentMat.color.setHex(cw.accent);
    innerEarMat.color.setHex(cw.accent);
    featureMat.color.setHex(cw.ink || 0x35292a);
    glowMat.color.setHex(cw.glow);
    glowMatDim.color.setHex(cw.glow);
    blushMat.opacity = cw.blush;
  }
  applyColorway("porcelain");

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
  const baseDirL = new THREE.Vector3(-0.34, 0.14, 1).normalize();
  const baseDirR = new THREE.Vector3(0.34, 0.14, 1).normalize();

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

    robot.position.y = Math.sin(t * cur.bobSpeed * 2.1) * 0.06 * cur.bob;
    body.rotation.x = cur.lean + Math.sin(t * 7) * 0.06 * cur.nod;
    body.rotation.z = cur.tilt * Math.sin(t * 2.6) * 0.16 + leanS.x * 0.2;

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
      faceNormal(_ep, _n);
      eye.position.copy(_ep).addScaledVector(_n, 0.055); // keep flat eye proud of the curved shell
      _q.setFromUnitVectors(_zAxis, _n);
      eye.quaternion.copy(_q);
    }

    const blinkVisible = canBlink && blink < 0.05 && sy > 0.6;
    blushL.visible = blushR.visible = mood !== "thinking" || cur.happy > 0.5;

    const happyOn = cur.happy > 0.5;
    happyL.visible = happyR.visible = happyOn;
    eyeL.visible = eyeR.visible = !happyOn;
    glintL.visible = glintR.visible = blinkVisible && !happyOn;
    sparkL.visible = sparkR.visible = blinkVisible && !happyOn;

    const browOn = cur.brows > 0.06;
    browL.visible = browR.visible = browOn;
    if (browOn) {
      browL.position.y = 0.52 + gy * 0.4;
      browR.position.y = 0.52 + gy * 0.4;
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

    glowMul = glowMul + (glowTargetMul - glowMul) * (1 - Math.exp(-3 * dt));
    coreFlash = Math.max(0, coreFlash - dt * 2.4);
    const flash = 1 + coreFlash;
    rim.intensity = 18 * glowMul;
    innerLight.intensity = (2.2 + coreFlash * 2.5) * glowMul;
    innerCore.material.opacity = (0.12 + coreFlash * 0.45) * glowMul;
    innerCore.scale.setScalar(1 + coreFlash * 0.05);
    if (ingest.active) {
      body.rotation.x += ingest.y * 0.1;
      body.rotation.z += ingest.x * 0.14;
    }

    gulpAmt *= Math.exp(-dt * 6);
    const hop = Math.max(cur.bounce, gulpAmt);
    if (hop > 0.05) {
      const b = Math.abs(Math.sin(t * 6.5));
      robot.position.y += b * 0.1 * hop;
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
