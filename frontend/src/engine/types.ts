// Engine input/output types. The vocabulary is the operator's: iGRC, GRC, ARC,
// residual ARC, SAIL, OSO. Nothing here is a "score".

export type Sail = 1 | 2 | 3 | 4 | 5 | 6;
export type Arc = "a" | "b" | "c" | "d";
export type Robustness = "low" | "medium" | "high";
export type OsoLevel = Robustness | "nr"; // nr = not required at this SAIL

export type OperationType = "VLOS" | "EVLOS" | "BVLOS";
export type AirspaceClass = "A" | "B" | "C" | "D" | "E" | "F" | "G";
export type GroundEnvironment = "controlled" | "sparsely" | "populated" | "assembly";

export interface AircraftInput {
  model: string;
  registration: string;
  maxDimensionM: number;
  maxSpeedMs: number;
  mtomKg: number;
}

export interface MitigationInput {
  /** M1(A) strategic mitigation — sheltering. Low or medium only. */
  m1a: "none" | "low" | "medium";
  /** M1(B) operational restrictions. Medium or high only. */
  m1b: "none" | "medium" | "high";
  /** M1(C) ground observation. Low only. */
  m1c: "none" | "low";
  /** M2 effects of UA impact dynamics reduced (e.g. parachute). Medium or high only. */
  m2: "none" | "medium" | "high";
  /** Strategic air-risk mitigation by operational restriction or common structure. */
  strategic: boolean;
}

export interface AirspaceInput {
  airspaceClass: AirspaceClass;
  /** Atypical or segregated airspace (e.g. a reserved area). */
  atypical: boolean;
  /** Inside an aerodrome environment, as the national annex defines it. */
  aerodromeEnvironment: boolean;
  aerodromeIcao?: string;
  aerodromeDistanceKm?: number;
  modeSVeilOrTmz: boolean;
  /** Over an urban area (vs. rural) — the ARC tree splits on this. */
  urban: boolean;
  geoZones: string[];
}

export interface OperationInput {
  aircraft: AircraftInput;
  operationType: OperationType;
  maxAltitudeM: number;
  durationMin: number;
  ground: {
    environment: GroundEnvironment;
    /** Peak population density across the ground risk buffer, ppl/km². */
    peakDensity: number;
  };
  airspace: AirspaceInput;
  mitigations: MitigationInput;
}

export interface TraceNode {
  id: string;
  kind: "fact" | "derived" | "root";
  term: string;
  value: string;
  /** One sentence naming the rule that fired. */
  rule: string;
  citation?: string;
  /** Ids of the nodes this one was derived from. */
  inputs: string[];
  /** Lookup detail shown when the node is expanded. */
  detail?: string[];
}

export interface OsoRequirement {
  id: string; // "OSO #05"
  num: number;
  name: string;
  level: OsoLevel;
}

export type Outcome =
  | { kind: "sail"; sail: Sail }
  | { kind: "certified"; reason: string };

export interface Determination {
  rulebase: { version: string; date: string };
  igrc: number | null; // null = outside SORA scope at the iGRC step
  grc: number | null;
  initialArc: Arc;
  residualArc: Arc;
  outcome: Outcome;
  osos: OsoRequirement[];
  containment: { status: "assessment-required"; note: string };
  trace: TraceNode[];
}
