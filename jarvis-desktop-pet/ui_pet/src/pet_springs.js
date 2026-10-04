/* RK4 spring-damper physics for the pet (spec 29, section 5.5.4).
   d²x/dt² + 2·ζ·ωn·dx/dt + ωn²·(x − target) = 0
   Defaults: ωn = 18.5, ζ = 0.65 (bouncy organic jiggle). */

export class Spring {
  constructor(omega = 18.5, zeta = 0.65, x = 0) {
    this.w = omega;
    this.z = zeta;
    this.x = x;
    this.v = 0;
    this.target = x;
  }

  impulse(dv) {
    this.v += dv;
  }

  // one RK4 step over (x, v); substeps keep it stable at low frame rates
  step(dt) {
    if (dt <= 0) return;
    const steps = Math.max(1, Math.ceil(dt / (1 / 120)));
    const h = dt / steps;
    const w2 = this.w * this.w;
    const c = 2 * this.z * this.w;
    const deriv = (x, v) => v;               // dx/dt
    const acc = (x, v) => -c * v - w2 * (x - this.target);
    for (let i = 0; i < steps; i++) {
      const x = this.x;
      const v = this.v;
      const k1x = deriv(x, v);
      const k1v = acc(x, v);
      const k2x = deriv(x + (h / 2) * k1x, v + (h / 2) * k1v);
      const k2v = acc(x + (h / 2) * k1x, v + (h / 2) * k1v);
      const k3x = deriv(x + (h / 2) * k2x, v + (h / 2) * k2v);
      const k3v = acc(x + (h / 2) * k2x, v + (h / 2) * k2v);
      const k4x = deriv(x + h * k3x, v + h * k3v);
      const k4v = acc(x + h * k3x, v + h * k3v);
      this.x += (h / 6) * (k1x + 2 * k2x + 2 * k3x + k4x);
      this.v += (h / 6) * (k1v + 2 * k2v + 2 * k3v + k4v);
    }
    if (!Number.isFinite(this.x)) { this.x = this.target; this.v = 0; }
  }

  energy() {
    return Math.abs(this.v) + Math.abs(this.x - this.target);
  }
}

/* Volume-conserving squash & stretch (spec 29, section 5.5.4):
   vertical compression Δy < 0 expands horizontally Δx = Δz = -½Δy. */
export function volumeScales(sy) {
  const dy = sy - 1;
  const sx = 1 - 0.5 * dy;
  return { sx, sz: sx, sy };
}

/* Taffy stretch helper: spring toward a velocity-derived deformation target. */
export class Taffy {
  constructor() {
    this.x = new Spring(16, 0.65, 0);
    this.y = new Spring(16, 0.65, 0);
  }

  drag(vx, vy, k = 0.012) {
    this.x.target = Math.max(-0.35, Math.min(0.35, vx * k));
    this.y.target = Math.max(-0.35, Math.min(0.35, vy * k));
  }

  release() {
    this.x.target = 0;
    this.y.target = 0;
  }

  step(dt) {
    this.x.step(dt);
    this.y.step(dt);
  }
}
