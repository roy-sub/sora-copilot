// The chart scene for the demo region (Mur valley, north of Graz). A local planar
// frame in metres, 16 × 10 km, north up. In production the same layers point at a
// vector source; the design and the analysis hold offline.

import type { Cell, Pt } from "@/engine/geometry";

export const WORLD = { w: 16000, h: 10000 };
export const CELL = 500;

export const DEFAULT_LINE: Pt[] = [
  { x: 1000, y: 6000 }, { x: 4500, y: 5200 }, { x: 8000, y: 5600 }, { x: 11500, y: 4600 }, { x: 15000, y: 4900 },
];
export const DEFAULT_HALF_WIDTH = 85;

export const RIVER: Pt[] = [
  { x: 0, y: 6600 }, { x: 2400, y: 6000 }, { x: 4200, y: 6500 }, { x: 7000, y: 6200 }, { x: 9500, y: 6900 }, { x: 12500, y: 6400 }, { x: 16000, y: 6800 },
];
export const ROAD: Pt[] = [
  { x: 0, y: 2400 }, { x: 3500, y: 3000 }, { x: 5500, y: 2100 }, { x: 8500, y: 2500 }, { x: 12000, y: 1800 }, { x: 16000, y: 2600 },
];

export const GEO_ZONES = [
  { id: "AT-R-114", label: "AT-R-114 restricted", x: 12600, y: 3000, w: 3000, h: 1650 },
];

export const AERODROME = { icao: "LOWG", name: "Graz", x: 5000, y: 12700 };

const BUMPS = [
  { x: 3250, y: 5750, peak: 84, s: 300 },     // scattered houses under the corridor
  { x: 6750, y: 5250, peak: 46, s: 300 },
  { x: 12750, y: 4750, peak: 38, s: 300 },
  { x: 9750, y: 4250, peak: 1800, s: 200 },   // Gratkorn, north-east of the line
  { x: 2250, y: 9250, peak: 6000, s: 900 },   // Graz, south-west
  { x: 13750, y: 7750, peak: 900, s: 350 },
];

const hash = (i: number, j: number) => {
  let h = (i * 374761393 + j * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
};

export const CELLS: Cell[] = (() => {
  const out: Cell[] = [];
  for (let i = 0; i < WORLD.w / CELL; i++)
    for (let j = 0; j < WORLD.h / CELL; j++) {
      const cx = i * CELL + CELL / 2, cy = j * CELL + CELL / 2;
      let d = 2 + Math.round(hash(i, j) * 38);
      for (const b of BUMPS) d = Math.max(d, Math.round(b.peak * Math.exp(-((cx - b.x) ** 2 + (cy - b.y) ** 2) / (2 * b.s * b.s))));
      out.push({ x: i * CELL, y: j * CELL, size: CELL, density: d });
    }
  return out;
})();
