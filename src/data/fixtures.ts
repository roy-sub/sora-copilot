// Demo workspace: Steiermark Inspect GmbH. Every determination shown in the app
// is computed from these inputs by the engine — no SAIL is typed in by hand.

import type { AircraftInput, OperationInput } from "../engine/types.ts";

export interface Aircraft extends AircraftInput {
  cruiseMs: number;
  fitted: string[];
}

export const FLEET: Aircraft[] = [
  { model: "Freefly Alta X", registration: "ALTA-X-01", maxDimensionM: 1.32, mtomKg: 15.9, cruiseMs: 18, maxSpeedMs: 22, fitted: ["Parachute", "FTS"] },
  { model: "DJI Matrice 350 RTK", registration: "M350-04", maxDimensionM: 0.89, mtomKg: 6.47, cruiseMs: 17, maxSpeedMs: 23, fitted: ["Parachute"] },
  { model: "Wingcopter 198", registration: "WC198-01", maxDimensionM: 1.98, mtomKg: 24.0, cruiseMs: 28, maxSpeedMs: 36, fitted: ["Parachute", "DAA", "FTS"] },
  { model: "DJI Mavic 3E", registration: "M3E-11", maxDimensionM: 0.38, mtomKg: 0.92, cruiseMs: 15, maxSpeedMs: 21, fitted: [] },
];

/** ½·m·v² at max speed, in kJ. Computed, never edited. */
export const kineticEnergyKj = (a: Aircraft) => (0.5 * a.mtomKg * a.maxSpeedMs ** 2) / 1000;

export const aircraftByReg = (reg: string) => FLEET.find((a) => a.registration === reg) ?? FLEET[0];

const ac = (reg: string): AircraftInput => {
  const { model, registration, maxDimensionM, maxSpeedMs, mtomKg } = aircraftByReg(reg);
  return { model, registration, maxDimensionM, maxSpeedMs, mtomKg };
};

export type OpStatus = "draft" | "determined" | "dossier ready" | "submitted" | "authorised";

export interface Operation {
  id: string;
  name: string;
  site: string;
  status: OpStatus;
  rulebase: string | null;
  lastRun: string | null;
  corridorKm?: number;
  input: OperationInput;
}

const NO_MIT = { m1a: "none", m1b: "none", m1c: "none", m2: "none", strategic: false } as const;

export const POWERLINE_INPUT: OperationInput = {
  aircraft: ac("ALTA-X-01"),
  operationType: "BVLOS",
  maxAltitudeM: 118,
  durationMin: 42,
  ground: { environment: "sparsely", peakDensity: 84 },
  airspace: {
    airspaceClass: "G", atypical: false, aerodromeEnvironment: true, aerodromeIcao: "LOWG", aerodromeDistanceKm: 7.4,
    modeSVeilOrTmz: false, urban: false, geoZones: ["AT-R-114"],
  },
  mitigations: { ...NO_MIT, m1a: "low", strategic: true },
};

export const OPERATIONS: Operation[] = [
  { id: "powerline-mur", name: "Powerline corridor — Mur valley", site: "Graz Süd, AT", status: "dossier ready", rulebase: "2026.2", lastRun: "2 h ago", corridorKm: 14.2, input: POWERLINE_INPUT },
  {
    id: "roof-reininghaus", name: "Roof survey — Reininghaus block 4", site: "Graz, AT", status: "determined", rulebase: "2026.2", lastRun: "Yesterday",
    input: {
      aircraft: ac("M350-04"), operationType: "VLOS", maxAltitudeM: 60, durationMin: 25,
      ground: { environment: "populated", peakDensity: 3200 },
      airspace: { airspaceClass: "G", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban: true, geoZones: [] },
      mitigations: { ...NO_MIT, m1a: "medium", strategic: true },
    },
  },
  {
    id: "quarry-peggau", name: "Quarry volumetrics — Peggau", site: "Peggau, AT", status: "authorised", rulebase: "2026.1", lastRun: "12 Sep",
    input: {
      aircraft: ac("M3E-11"), operationType: "EVLOS", maxAltitudeM: 90, durationMin: 35,
      ground: { environment: "controlled", peakDensity: 0 },
      airspace: { airspaceClass: "G", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban: false, geoZones: [] },
      mitigations: { ...NO_MIT },
    },
  },
  {
    id: "pipeline-leibnitz", name: "BVLOS pipeline run — Leibnitz", site: "Leibnitz, AT", status: "submitted", rulebase: "2026.1", lastRun: "04 Sep",
    input: {
      aircraft: ac("WC198-01"), operationType: "BVLOS", maxAltitudeM: 110, durationMin: 55,
      ground: { environment: "sparsely", peakDensity: 120 },
      airspace: { airspaceClass: "G", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban: false, geoZones: [] },
      mitigations: { ...NO_MIT, m2: "medium" },
    },
  },
  {
    id: "schlossberg-event", name: "Crowd overflight — Schlossberg event", site: "Graz, AT", status: "draft", rulebase: null, lastRun: null,
    input: {
      aircraft: ac("ALTA-X-01"), operationType: "VLOS", maxAltitudeM: 80, durationMin: 20,
      ground: { environment: "assembly", peakDensity: 60000 },
      airspace: { airspaceClass: "D", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban: true, geoZones: [] },
      mitigations: { ...NO_MIT },
    },
  },
  {
    id: "thermal-werk2", name: "Thermal inspection — Werk 2", site: "Kapfenberg, AT", status: "determined", rulebase: "2026.2", lastRun: "28 Aug",
    input: {
      aircraft: ac("M3E-11"), operationType: "VLOS", maxAltitudeM: 50, durationMin: 15,
      ground: { environment: "controlled", peakDensity: 0 },
      airspace: { airspaceClass: "G", atypical: false, aerodromeEnvironment: false, modeSVeilOrTmz: false, urban: false, geoZones: [] },
      mitigations: { ...NO_MIT, strategic: true },
    },
  },
];

export const opById = (id: string) => OPERATIONS.find((o) => o.id === id);

/** Evidence state per OSO for the demo operation. Anything absent is a gap. */
export const EVIDENCE: Record<string, Record<number, "evidenced" | "partial">> = {
  "powerline-mur": { 1: "evidenced", 2: "evidenced", 3: "evidenced", 6: "evidenced", 7: "evidenced", 8: "partial", 9: "evidenced", 16: "evidenced", 17: "evidenced", 18: "evidenced", 19: "partial", 20: "partial", 23: "evidenced" },
};

export const ORG = {
  name: "Steiermark Inspect GmbH",
  short: "Steiermark Inspect",
  registration: "AUT8j2kx91mfq",
  user: { name: "K. Leitner", initials: "KL" },
  members: [
    { name: "K. Leitner", initials: "KL", role: "OWNER" },
    { name: "M. Reiter", initials: "MR", role: "PILOT" },
    { name: "A. Stiegler", initials: "AS", role: "COMPLIANCE" },
  ],
};
