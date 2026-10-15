// Operational volumes on the chart surface. The flight geography is a corridor:
// a centreline with a half-width. The contingency volume and ground risk buffer
// are offsets of it, sized from the aircraft and the altitude — derived, not typed.
//
// Units are metres in a local planar frame. The chart maps 1 unit = 1 m.

export type Pt = { x: number; y: number };

export interface Volumes {
  fgHalfWidth: number;
  cvMargin: number;
  grbMargin: number;
}

const G = 9.81;

/** Contingency margin: reaction distance + turn radius at 30° bank + 3 m position error.
 *  Ground risk buffer: the 1:1 rule against the contingency-volume height. */
export function deriveVolumes(fgHalfWidth: number, vmax: number, altitudeM: number): Volumes {
  const reaction = vmax * 1.0;
  const turn = (vmax * vmax) / (G * Math.tan((30 * Math.PI) / 180));
  const cvMargin = Math.round(reaction + turn / 2 + 3);
  const grbMargin = Math.round(altitudeM + cvMargin * 0.25);
  return { fgHalfWidth, cvMargin, grbMargin };
}

/** Closed outline of a polyline buffered by r: mitred sides, round end caps. */
export function bufferOutline(line: Pt[], r: number, capSteps = 10): Pt[] {
  if (line.length < 2) return [];
  const n = line.length;
  const normal = (a: Pt, b: Pt) => {
    const dx = b.x - a.x, dy = b.y - a.y, l = Math.hypot(dx, dy) || 1;
    return { x: -dy / l, y: dx / l };
  };
  const side = (sign: 1 | -1) => {
    const pts: Pt[] = [];
    for (let i = 0; i < n; i++) {
      const n1 = i > 0 ? normal(line[i - 1], line[i]) : normal(line[0], line[1]);
      const n2 = i < n - 1 ? normal(line[i], line[i + 1]) : n1;
      const mx = n1.x + n2.x, my = n1.y + n2.y, ml = Math.hypot(mx, my) || 1;
      const cos = (mx / ml) * n1.x + (my / ml) * n1.y;
      const k = r / Math.max(cos, 0.35); // cap the mitre on sharp bends
      pts.push({ x: line[i].x + sign * (mx / ml) * k, y: line[i].y + sign * (my / ml) * k });
    }
    return pts;
  };
  const cap = (c: Pt, from: Pt) => {
    const a0 = Math.atan2(from.y - c.y, from.x - c.x);
    const pts: Pt[] = [];
    for (let s = 1; s < capSteps; s++) {
      const a = a0 - (Math.PI * s) / capSteps;
      pts.push({ x: c.x + r * Math.cos(a), y: c.y + r * Math.sin(a) });
    }
    return pts;
  };
  const left = side(1), right = side(-1).reverse();
  return [...left, ...cap(line[n - 1], left[n - 1]), ...right, ...cap(line[0], right[n - 1])];
}

export function polygonArea(pts: Pt[]): number {
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length];
    s += a.x * b.y - b.x * a.y;
  }
  return Math.abs(s) / 2;
}

export const toPath = (pts: Pt[]) => (pts.length ? "M" + pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join("L") + "Z" : "");

export function lineLength(line: Pt[]): number {
  let s = 0;
  for (let i = 1; i < line.length; i++) s += Math.hypot(line[i].x - line[i - 1].x, line[i].y - line[i - 1].y);
  return s;
}

/** Nearest point on the polyline to p. */
export function nearestOnLine(p: Pt, line: Pt[]): { pt: Pt; dist: number } {
  let best = { pt: line[0], dist: Infinity };
  for (let i = 1; i < line.length; i++) {
    const a = line[i - 1], b = line[i];
    const dx = b.x - a.x, dy = b.y - a.y, l2 = dx * dx + dy * dy || 1;
    const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2));
    const q = { x: a.x + t * dx, y: a.y + t * dy };
    const d = Math.hypot(p.x - q.x, p.y - q.y);
    if (d < best.dist) best = { pt: q, dist: d };
  }
  return best;
}

export const distToLine = (p: Pt, line: Pt[]) => nearestOnLine(p, line).dist;

/** Shortest distance from an axis-aligned rectangle to the polyline (0 = touching). */
export function rectDistToLine(r: { x: number; y: number; w: number; h: number }, line: Pt[]): number {
  let best = Infinity;
  for (let i = 1; i < line.length; i++) {
    const a = line[i - 1], b = line[i];
    const n = Math.max(2, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / 25));
    for (let k = 0; k <= n; k++) {
      const p = { x: a.x + ((b.x - a.x) * k) / n, y: a.y + ((b.y - a.y) * k) / n };
      const dx = Math.max(r.x - p.x, 0, p.x - (r.x + r.w)), dy = Math.max(r.y - p.y, 0, p.y - (r.y + r.h));
      best = Math.min(best, Math.hypot(dx, dy));
    }
  }
  return best;
}

export function compass(from: Pt, to: Pt): string {
  const a = (Math.atan2(to.x - from.x, from.y - to.y) * 180) / Math.PI; // 0 = north, y grows south
  return ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][Math.round(((a + 360) % 360) / 45) % 8];
}

// ------------------------------------------------------------- population cells

export interface Cell { x: number; y: number; size: number; density: number }

export const DENSITY_BANDS = [
  { max: 5, label: "< 5", spacing: 0 },
  { max: 50, label: "5–50", spacing: 14 },
  { max: 500, label: "50–500", spacing: 9 },
  { max: 5000, label: "500–5,000", spacing: 6 },
  { max: Infinity, label: "> 5,000", spacing: 4 },
] as const;

export const bandOf = (d: number) => DENSITY_BANDS.findIndex((b) => d < b.max);

/** Area readout and adjacency, computed against the population cells. */
export function analyse(line: Pt[], v: Volumes, cells: Cell[]) {
  const rFg = v.fgHalfWidth, rCv = rFg + v.cvMargin, rGrb = rCv + v.grbMargin;
  const km2 = (r: number) => polygonArea(bufferOutline(line, r, 24)) / 1e6;
  let peak = 0;
  let adjacent: { distance: number; density: number; direction: string } | null = null;
  for (const c of cells) {
    const centre = { x: c.x + c.size / 2, y: c.y + c.size / 2 };
    const near = nearestOnLine(centre, line);
    const d = near.dist - c.size / 2;
    if (d <= rGrb) peak = Math.max(peak, c.density);
    else if (d <= rGrb + 500 && c.density >= 500) {
      const out = Math.round(d - rGrb);
      if (!adjacent || out < adjacent.distance) adjacent = { distance: Math.max(out, 0), density: c.density, direction: compass(near.pt, centre) };
    }
  }
  return { fg: km2(rFg), cv: km2(rCv), grb: km2(rGrb), peak, adjacent, lengthKm: lineLength(line) / 1000 };
}
