// Rulebase 2026.2 — JARUS SORA 2.5 main body, as adopted under EU 2019/947.
//
// VERIFY BEFORE PRODUCTION: every table below was transcribed for this build and
// must be checked line by line against the published JARUS SORA 2.5 text (and the
// national annex in force) by a competent compliance reviewer. Citations are kept
// next to the values they justify so that review is a one-file job.

import type { Arc, OsoLevel, Sail } from "./types.ts";

export const RULEBASE = { version: "2026.2", date: "01 Oct 2026" } as const;

export const CITE = {
  igrc: "SORA 2.5 · Table 2",
  m1a: "SORA 2.5 · Table 5 · M1(A)",
  m1b: "SORA 2.5 · Table 5 · M1(B)",
  m1c: "SORA 2.5 · Table 5 · M1(C)",
  m2: "SORA 2.5 · Table 5 · M2",
  grcTable: "SORA 2.5 · Table 5",
  grcFloor: "SORA 2.5 · §4.3 · Step 3",
  arc: "SORA 2.5 · Figure 6",
  residualArc: "SORA 2.5 · Annex C",
  sail: "SORA 2.5 · Table 7",
  oso: "SORA 2.5 · Table 14",
  containment: "SORA 2.5 · Step 9",
} as const;

/** iGRC columns: max characteristic dimension (m) and max speed (m/s). An aircraft
 *  falls in the first column where BOTH limits hold. */
export const IGRC_COLUMNS = [
  { dim: 1, speed: 25, label: "1 m / 25 m/s" },
  { dim: 3, speed: 35, label: "3 m / 35 m/s" },
  { dim: 8, speed: 75, label: "8 m / 75 m/s" },
  { dim: 20, speed: 120, label: "20 m / 120 m/s" },
  { dim: 40, speed: 200, label: "40 m / 200 m/s" },
] as const;

/** iGRC rows by maximum population density (ppl/km²). `null` = not part of SORA. */
export const IGRC_ROWS: { label: string; maxDensity: number; values: (number | null)[] }[] = [
  { label: "Controlled ground area", maxDensity: -1, values: [1, 1, 2, 3, 3] },
  { label: "< 5 ppl/km²", maxDensity: 5, values: [2, 3, 4, 5, 6] },
  { label: "< 50 ppl/km²", maxDensity: 50, values: [3, 4, 5, 6, 7] },
  { label: "< 500 ppl/km²", maxDensity: 500, values: [4, 5, 6, 7, 8] },
  { label: "< 5,000 ppl/km²", maxDensity: 5000, values: [5, 6, 7, 8, 9] },
  { label: "< 50,000 ppl/km²", maxDensity: 50000, values: [6, 7, 8, 9, 10] },
  { label: "> 50,000 ppl/km²", maxDensity: Infinity, values: [7, 8, null, null, null] },
];

/** GRC reduction per mitigation and robustness. `null` = cannot be claimed at that level. */
export const GRC_MITIGATIONS = {
  m1a: { low: -1, medium: -2, high: null },
  m1b: { low: null, medium: -1, high: -2 },
  m1c: { low: -1, medium: null, high: null },
  m2: { low: null, medium: -1, high: -2 },
} as const;

/** SAIL by final GRC (rows, ≤2 … 7) and residual ARC (a–d). */
export const SAIL_TABLE: Record<number, Record<Arc, Sail>> = {
  2: { a: 1, b: 2, c: 4, d: 6 },
  3: { a: 2, b: 2, c: 4, d: 6 },
  4: { a: 3, b: 3, c: 4, d: 6 },
  5: { a: 4, b: 4, c: 4, d: 6 },
  6: { a: 5, b: 5, c: 5, d: 6 },
  7: { a: 6, b: 6, c: 6, d: 6 },
};

const L: OsoLevel = "low";
const M: OsoLevel = "medium";
const H: OsoLevel = "high";
const N: OsoLevel = "nr";

/** OSO robustness by SAIL I–VI. */
export const OSO_TABLE: { num: number; name: string; levels: [OsoLevel, OsoLevel, OsoLevel, OsoLevel, OsoLevel, OsoLevel] }[] = [
  { num: 1, name: "Operator is competent and/or proven", levels: [N, L, M, H, H, H] },
  { num: 2, name: "UAS manufactured by competent and/or proven entity", levels: [N, N, L, M, H, H] },
  { num: 3, name: "UAS maintained by competent and/or proven entity", levels: [L, L, M, M, H, H] },
  { num: 4, name: "UAS components essential to safe operations designed to an airworthiness design standard", levels: [N, N, N, L, M, H] },
  { num: 5, name: "UAS designed considering system safety and reliability", levels: [N, N, L, M, H, H] },
  { num: 6, name: "C3 link characteristics appropriate for the operation", levels: [N, L, L, M, H, H] },
  { num: 7, name: "Conformity check of the UAS configuration", levels: [L, L, M, M, H, H] },
  { num: 8, name: "Operational procedures defined, validated and adhered to", levels: [L, M, H, H, H, H] },
  { num: 9, name: "Remote crew trained and current", levels: [L, L, M, M, H, H] },
  { num: 13, name: "External services adequate to the operation", levels: [L, L, M, H, H, H] },
  { num: 16, name: "Multi-crew coordination", levels: [L, L, M, M, H, H] },
  { num: 17, name: "Remote crew fit to operate", levels: [L, L, M, M, H, H] },
  { num: 18, name: "Automatic protection of the flight envelope from human error", levels: [N, N, L, M, H, H] },
  { num: 19, name: "Safe recovery from human error", levels: [N, N, L, M, M, H] },
  { num: 20, name: "Human factors evaluation performed, HMI found appropriate", levels: [N, L, L, M, M, H] },
  { num: 23, name: "Environmental conditions defined, measurable and adhered to", levels: [L, L, M, M, H, H] },
  { num: 24, name: "UAS designed and qualified for adverse environmental conditions", levels: [N, N, M, H, H, H] },
];

export const ROMAN = ["I", "II", "III", "IV", "V", "VI"] as const;

/** SORA 2.5 Step 2 has a fixed iGRC 1 for very small, slow aircraft. */
export const SMALL_UA = { mtomKg: 0.25, speedMs: 25 } as const;
