// Free category checker. Three answers → open / specific / certified, plus an
// indicative SAIL for the specific category. It runs the same engine as the
// product, against a typical aircraft for the chosen mass band.

import { counterfactuals, determine } from "./engine.ts";
import type { Determination, GroundEnvironment, OperationInput, OperationType } from "./types.ts";

export type MassBand = "sub250" | "c-marked" | "4to25" | "over25";

export interface CheckerAnswers {
  mass: MassBand;
  ground: GroundEnvironment;
  operation: OperationType;
}

export type CheckerResult =
  | { category: "open"; subcategory: "A1" | "A2" | "A3"; reason: string }
  | { category: "specific"; reason: string; determination: Determination; hint?: string }
  | { category: "certified"; reason: string; determination: Determination };

export const MASS_BANDS: { id: MassBand; label: string }[] = [
  { id: "sub250", label: "Under 250 g" },
  { id: "c-marked", label: "250 g to 4 kg, class marked" },
  { id: "4to25", label: "4 kg to 25 kg" },
  { id: "over25", label: "Over 25 kg" },
];

const TYPICAL: Record<MassBand, { dim: number; speed: number; mtom: number }> = {
  sub250: { dim: 0.25, speed: 19, mtom: 0.249 },
  "c-marked": { dim: 0.9, speed: 23, mtom: 3 },
  "4to25": { dim: 1.5, speed: 25, mtom: 15 },
  over25: { dim: 2.5, speed: 30, mtom: 40 },
};

const DENSITY: Record<GroundEnvironment, number> = { controlled: 0, sparsely: 100, populated: 1500, assembly: 60000 };

export function checkerInput(a: CheckerAnswers): OperationInput {
  const t = TYPICAL[a.mass];
  const urban = a.ground === "populated" || a.ground === "assembly";
  return {
    aircraft: { model: "Typical aircraft", registration: "—", maxDimensionM: t.dim, maxSpeedMs: t.speed, mtomKg: t.mtom },
    operationType: a.operation,
    maxAltitudeM: 120,
    durationMin: 30,
    ground: { environment: a.ground, peakDensity: DENSITY[a.ground] },
    airspace: { airspaceClass: "G", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban, geoZones: [] },
    mitigations: { m1a: "none", m1b: "none", m1c: "none", m2: "none", strategic: false },
  };
}

export function checkCategory(a: CheckerAnswers): CheckerResult {
  // Open category: VLOS, below 25 kg, never over an assembly of people (EU 2019/947 Art. 4).
  if (a.operation === "VLOS" && a.mass !== "over25" && a.ground !== "assembly") {
    if (a.mass === "sub250") return { category: "open", subcategory: "A1", reason: "Under 250 g in VLOS may fly over uninvolved people, never over assemblies." };
    if (a.mass === "c-marked") return { category: "open", subcategory: "A2", reason: "A class-marked aircraft up to 4 kg keeps 30 m from uninvolved people." };
    if (a.ground !== "populated") return { category: "open", subcategory: "A3", reason: "Up to 25 kg, far from people and 150 m from residential, commercial or industrial areas." };
  }

  const input = checkerInput(a);
  const d = determine(input);
  if (d.outcome.kind === "certified") return { category: "certified", reason: d.outcome.reason, determination: d };

  const why =
    a.operation !== "VLOS" ? `${a.operation} is outside the open category.`
    : a.mass === "over25" ? "Over 25 kg is outside the open category."
    : a.ground === "assembly" ? "Flight over an assembly of people is outside the open category."
    : "A 4–25 kg aircraft over a populated area is outside subcategory A3.";

  const best = counterfactuals(input)[0];
  const hint = best && best.result.outcome.kind === "sail"
    ? `${best.title.replace(/^Claim/, "Claiming").replace(/^Fit/, "Fitting")} would reach SAIL ${["I", "II", "III", "IV", "V", "VI"][best.result.outcome.sail - 1]} for an operation like this.`
    : undefined;
  return { category: "specific", reason: why, determination: d, hint };
}
