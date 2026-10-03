import * as THREE from "./vendor/three.module.js";

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
  const key = new THREE.DirectionalLight(0xffffff, 1.7);
  key.position.set(2.5, 3.5, 4);
  scene.add(key);
  const rim = new THREE.PointLight(0x8b5cf6, 26, 14);
  rim.position.set(-3, -1.2, 2.5);
  scene.add(rim);
  const fill = new THREE.PointLight(0x5b8bff, 9, 12);
  fill.position.set(3, -2, -2);
  scene.add(fill);

  const shellMat = new THREE.MeshPhysicalMaterial({
    color: 0xf0ecff,
    roughness: 0.24,
    metalness: 0.02,
    clearcoat: 0.55,
    clearcoatRoughness: 0.3,
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

  const skull = new THREE.Mesh(new THREE.SphereGeometry(1.15, 48, 32), shellMat);
  skull.scale.set(1, 0.97, 0.94);
  head.add(skull);

  const face = new THREE.Mesh(new THREE.SphereGeometry(1.1, 48, 32), faceMat);
  face.scale.set(0.88, 0.8, 0.96);
  face.position.z = 0.1;
  head.add(face);

  const EX = 0.34, EY = 0.0, EZ = 1.16;
  const eyeGeo = new THREE.CircleGeometry(0.21, 32);
  const eyeL = new THREE.Mesh(eyeGeo, glowMat);
  const eyeR = new THREE.Mesh(eyeGeo, glowMat);
  eyeL.position.set(-EX, EY, EZ);
  eyeR.position.set(EX, EY, EZ);
  head.add(eyeL, eyeR);

  const glintGeo = new THREE.CircleGeometry(0.055, 16);
  const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const glintL = new THREE.Mesh(glintGeo, glintMat);
  const glintR = new THREE.Mesh(glintGeo, glintMat);
  glintL.position.set(-EX + 0.07, EY + 0.07, EZ + 0.01);
  glintR.position.set(EX + 0.07, EY + 0.07, EZ + 0.01);
  head.add(glintL, glintR);

  const blushGeo = new THREE.CircleGeometry(0.13, 24);
  const blushL = new THREE.Mesh(blushGeo, blushMat);
  const blushR = new THREE.Mesh(blushGeo, blushMat);
  blushL.position.set(-0.64, -0.2, 1.14);
  blushR.position.set(0.64, -0.2, 1.14);
  blushL.scale.set(1, 0.7, 1);
  blushR.scale.set(1, 0.7, 1);
  head.add(blushL, blushR);

  const happyGeo = new THREE.TorusGeometry(0.17, 0.05, 10, 24, Math.PI);
  const happyL = new THREE.Mesh(happyGeo, glowMat);
  const happyR = new THREE.Mesh(happyGeo, glowMat);
  happyL.position.set(-EX, EY + 0.02, EZ);
  happyR.position.set(EX, EY + 0.02, EZ);
  happyL.rotation.z = Math.PI;
  happyR.rotation.z = Math.PI;
  happyL.visible = happyR.visible = false;
  head.add(happyL, happyR);

  const browGeo = new THREE.BoxGeometry(0.32, 0.055, 0.05);
  const browL = new THREE.Mesh(browGeo, browMat);
  const browR = new THREE.Mesh(browGeo, browMat);
  browL.position.set(-EX, 0.4, EZ - 0.06);
  browR.position.set(EX, 0.4, EZ - 0.06);
  browL.visible = browR.visible = false;
  head.add(browL, browR);

  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.038, 10, 24, Math.PI), glowMat);
  smile.position.set(0, -0.34, EZ);
  smile.rotation.z = Math.PI;
  head.add(smile);

  const mouthOpen = new THREE.Mesh(new THREE.CircleGeometry(0.12, 24), glowMat);
  mouthOpen.position.set(0, -0.36, EZ);
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

  const torso = new THREE.Mesh(new THREE.SphereGeometry(0.6, 40, 28), shellMat);
  torso.scale.set(1, 0.8, 0.88);
  body.add(torso);
  const bellyPatch = new THREE.Mesh(new THREE.CircleGeometry(0.2, 24), glowMatDim);
  bellyPatch.position.set(0, 0.02, 0.54);
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

  const PRESETS = {
    idle: { lean: 0, tilt: 0, bob: 1, bobSpeed: 1.1, eyeSX: 1, eyeSY: 1, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1, ant: 1, brows: 0, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
    listening: { lean: -0.17, tilt: 0, bob: 0.35, bobSpeed: 0.8, eyeSX: 1.1, eyeSY: 1.35, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1, ant: 3.4, brows: 0, happy: 0, rings: 1, orbs: 0, bounce: 0, nod: 0 },
    thinking: { lean: 0.02, tilt: 1, bob: 0.5, bobSpeed: 1.0, eyeSX: 1, eyeSY: 0.8, eyeX: 1, eyeY: 0, mouthO: 0, flat: 1, smileS: 0.6, ant: 1.6, brows: 1, happy: 0, rings: 0, orbs: 1, bounce: 0, nod: 0 },
    speaking: { lean: 0.04, tilt: 0, bob: 0.5, bobSpeed: 1.4, eyeSX: 1, eyeSY: 1.1, eyeX: 0, eyeY: 0, mouthO: 1, flat: 0, smileS: 1, ant: 2.6, brows: 0, happy: 0, rings: 1, orbs: 0, bounce: 0, nod: 1 },
    happy: { lean: -0.04, tilt: 0, bob: 1.2, bobSpeed: 1.7, eyeSX: 1, eyeSY: 1, eyeX: 0, eyeY: 0, mouthO: 0, flat: 0, smileS: 1.4, ant: 1.9, brows: 0, happy: 1, rings: 0, orbs: 0, bounce: 1, nod: 0 },
    concerned: { lean: 0.13, tilt: 0, bob: 0.2, bobSpeed: 0.7, eyeSX: 0.95, eyeSY: 0.9, eyeX: 0, eyeY: -0.4, mouthO: 0, flat: 1, smileS: 0.5, ant: 0.8, brows: 1.6, happy: 0, rings: 0, orbs: 0, bounce: 0, nod: 0 },
  };

  const cur = Object.assign({}, PRESETS.idle);
  let target = Object.assign({}, PRESETS.idle);
  let mood = "idle";
  let blinkAt = 2.5;
  let blink = 0;
  const look = { x: 0, next: 2 };

  window.Pet3D = {
    setMood(m) {
      if (PRESETS[m]) {
        mood = m;
        target = Object.assign({}, PRESETS[m]);
      }
    },
    mood: () => mood,
  };

  const damp = (a, b, lambda, dt) => a + (b - a) * (1 - Math.exp(-lambda * dt));

  const clock = new THREE.Clock();
  let t = 0;

  function frame() {
    const dt = Math.min(clock.getDelta(), 0.05);
    t += dt;

    for (const k of Object.keys(target)) cur[k] = damp(cur[k], target[k], 5, dt);

    robot.position.y = Math.sin(t * cur.bobSpeed * 2.1) * 0.06 * cur.bob;
    head.rotation.x = cur.lean + Math.sin(t * 7) * 0.06 * cur.nod;
    head.rotation.z = cur.tilt * Math.sin(t * 2.6) * 0.16;

    if (cur.tilt > 0.3) {
      look.next -= dt;
      if (look.next <= 0) {
        look.x = (Math.random() * 2 - 1) * 0.9;
        look.next = 1.1 + Math.random() * 1.2;
      }
    }
    const eyeShiftX = cur.eyeX > 0 ? look.x * 0.1 * cur.eyeX : cur.eyeX * 0.08;
    const eyeShiftY = cur.eyeY * 0.1;

    blinkAt -= dt;
    if (blinkAt <= 0 && mood !== "happy") {
      blink = 1;
      blinkAt = 3 + Math.random() * 3;
    }
    if (blink > 0) blink = Math.max(0, blink - dt * 9);
    const blinkCurve = 1 - Math.sin(Math.min(blink, 1) * Math.PI) * 0.96;

    const canBlink = mood === "idle" || mood === "listening" || mood === "speaking";
    const sy = cur.eyeSY * (canBlink ? blinkCurve : 1);
    eyeL.scale.set(cur.eyeSX, sy, 1);
    eyeR.scale.set(cur.eyeSX, sy, 1);
    eyeL.position.set(-EX + eyeShiftX, EY + eyeShiftY, EZ);
    eyeR.position.set(EX + eyeShiftX, EY + eyeShiftY, EZ);
    glintL.visible = glintR.visible = canBlink && blink < 0.05 && sy > 0.6;
    glintL.position.set(-EX + 0.07 + eyeShiftX, EY + 0.07 + eyeShiftY, EZ + 0.01);
    glintR.position.set(EX + 0.07 + eyeShiftX, EY + 0.07 + eyeShiftY, EZ + 0.01);

    blushL.visible = blushR.visible = mood !== "thinking" || cur.happy > 0.5;

    const happyOn = cur.happy > 0.5;
    happyL.visible = happyR.visible = happyOn;
    eyeL.visible = eyeR.visible = !happyOn;
    glintL.visible = glintR.visible = glintL.visible && !happyOn;

    const browOn = cur.brows > 0.06;
    browL.visible = browR.visible = browOn;
    if (browOn) {
      browL.position.y = 0.4 + eyeShiftY;
      browR.position.y = 0.4 + eyeShiftY;
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
    antTip.material.color.setHSL(0.74, 1, 0.55 + antPulse * 0.18);
    antTip.scale.setScalar(1 + Math.sin(t * cur.ant * 2.4) * 0.15);
    antGlow.intensity = 2.5 + antPulse * 2.5;

    const bounceS = cur.bounce > 0.05;
    if (bounceS) {
      const b = Math.abs(Math.sin(t * 6.5));
      body.scale.set(1 + b * 0.06 * cur.bounce, 1 - b * 0.08 * cur.bounce, 1 + b * 0.06 * cur.bounce);
      head.scale.set(1 - b * 0.03 * cur.bounce, 1 + b * 0.05 * cur.bounce, 1 - b * 0.03 * cur.bounce);
    } else {
      body.scale.set(1, 1, 1);
      head.scale.set(1, 1, 1);
    }
    handL.position.y = -0.1 + Math.sin(t * 1.4) * 0.05;
    handR.position.y = -0.1 + Math.sin(t * 1.4 + 0.6) * 0.05;
    if (bounceS) {
      handL.rotation.z = Math.sin(t * 9) * 0.5;
      handR.rotation.z = -Math.sin(t * 9) * 0.5;
    } else {
      handL.rotation.z = damp(handL.rotation.z, 0, 6, dt);
      handR.rotation.z = damp(handR.rotation.z, 0, 6, dt);
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
    requestAnimationFrame(frame);
  }
  frame();
}
