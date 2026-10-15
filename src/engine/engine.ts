// The determination engine. Pure, synchronous, deterministic: the same input and
// rulebase always produce the same determination and the same trace.

import {
  CITE, GRC_MITIGATIONS, IGRC_COLUMNS, IGRC_ROWS, OSO_TABLE, ROMAN, RULEBASE, SAIL_TABLE, SMALL_UA,
} from "./rulebase.ts";
import type {
  Arc, Determination, MitigationInput, OperationInput, OsoRequirement, Outcome, Sail, TraceNode,
} from "./types.ts";

export const roman = (s: number) => ROMAN[s - 1];
const fmt = (n: number) => n.toLocaleString("en-GB");

// ------------------------------------------------------------------ step 2 · iGRC

export function igrcColumn(dimM: number, speedMs: number): number {
  const i = IGRC_COLUMNS.findIndex((c) => dimM <= c.dim && speedMs <= c.speed);
  return i === -1 ? IGRC_COLUMNS.length : i; // beyond the last column = outside SORA
}

export function igrcRow(env: OperationInput["ground"]["environment"], density: number): number {
  if (env === "controlled") return 0;
  const d = env === "assembly" ? Math.max(density, 50001) : density;
  return IGRC_ROWS.findIndex((r, i) => i > 0 && d < r.maxDensity);
}

export function intrinsicGrc(input: OperationInput) {
  const { aircraft: ac, ground } = input;
  const col = igrcColumn(ac.maxDimensionM, ac.maxSpeedMs);
  const row = igrcRow(ground.environment, ground.peakDensity);
  if (ac.mtomKg <= SMALL_UA.mtomKg && ac.maxSpeedMs <= SMALL_UA.speedMs) {
    return { value: 1 as number | null, col: 0, row, rule: "MTOM ≤ 250 g and speed ≤ 25 m/s: iGRC 1 regardless of population." };
  }
  if (col >= IGRC_COLUMNS.length) {
    return { value: null, col, row, rule: "Dimension or speed beyond the last iGRC column: outside SORA scope." };
  }
  const value = IGRC_ROWS[row].values[col];
  const rule = value === null
    ? `${IGRC_COLUMNS[col].label} over ${IGRC_ROWS[row].label}: not part of SORA.`
    : `Column ${IGRC_COLUMNS[col].label} over ${IGRC_ROWS[row].label.toLowerCase()}.`;
  return { value, col, row, rule };
}

// ------------------------------------------------------------------ step 3 · GRC

export function mitigationDeltas(m: MitigationInput) {
  const out: { key: keyof typeof GRC_MITIGATIONS; label: string; level: string; delta: number }[] = [];
  const add = (key: keyof typeof GRC_MITIGATIONS, label: string, level: string) => {
    if (level === "none") return;
    const d = (GRC_MITIGATIONS[key] as Record<string, number | null>)[level];
    if (d == null) throw new Error(`${label} cannot be claimed at ${level} robustness`);
    out.push({ key, label, level, delta: d });
  };
  add("m1a", "M1(A) sheltering", m.m1a);
  add("m1b", "M1(B) operational restrictions", m.m1b);
  add("m1c", "M1(C) ground observation", m.m1c);
  add("m2", "M2 impact dynamics", m.m2);
  return out;
}

// ------------------------------------------------------------------ step 4 · ARC

export function initialArc(input: OperationInput): { arc: Arc; rule: string } {
  const a = input.airspace;
  const above150 = input.maxAltitudeM > 150;
  const controlled = ["A", "B", "C", "D", "E"].includes(a.airspaceClass);
  if (a.atypical) return { arc: "a", rule: "Atypical or segregated airspace." };
  if (above150) {
    if (a.modeSVeilOrTmz || controlled) return { arc: "d", rule: "Above 150 m AGL in controlled airspace, Mode-S veil or TMZ." };
    return { arc: "c", rule: `Above 150 m AGL, uncontrolled, ${a.urban ? "urban" : "rural"}.` };
  }
  if (a.aerodromeEnvironment) {
    const bcd = ["B", "C", "D"].includes(a.airspaceClass);
    const where = a.aerodromeIcao ? ` of ${a.aerodromeIcao}` : "";
    return bcd
      ? { arc: "d", rule: `Below 150 m AGL in the aerodrome environment${where}, class ${a.airspaceClass}.` }
      : { arc: "c", rule: `Below 150 m AGL in the aerodrome environment${where}, class ${a.airspaceClass}.` };
  }
  if (a.modeSVeilOrTmz) return { arc: "c", rule: "Below 150 m AGL inside a Mode-S veil or TMZ." };
  if (controlled) return { arc: "c", rule: `Below 150 m AGL in controlled airspace, class ${a.airspaceClass}.` };
  if (a.urban) return { arc: "c", rule: "Below 150 m AGL, uncontrolled, over an urban area." };
  return { arc: "b", rule: "Below 150 m AGL, uncontrolled, over a rural area." };
}

export function residualArc(initial: Arc, strategic: boolean): Arc {
  if (!strategic) return initial;
  return ({ a: "a", b: "a", c: "b", d: "c" } as const)[initial];
}

// ------------------------------------------------------------------ step 7 · SAIL

export function sailFor(grc: number, arc: Arc): Sail {
  const row = Math.min(7, Math.max(2, grc));
  return SAIL_TABLE[row][arc];
}

export function osoSet(sail: Sail): OsoRequirement[] {
  return OSO_TABLE.map((o) => ({
    id: `OSO #${String(o.num).padStart(2, "0")}`,
    num: o.num,
    name: o.name,
    level: o.levels[sail - 1],
  }));
}

// ------------------------------------------------------------------ the run

export function determine(input: OperationInput): Determination {
  const { aircraft: ac, ground, airspace: as, mitigations: m } = input;
  const trace: TraceNode[] = [];
  const envLabel = { controlled: "controlled ground area", sparsely: "sparsely populated", populated: "populated", assembly: "assembly of people" }[ground.environment];

  trace.push(
    { id: "f-dim", kind: "fact", term: "Aircraft", value: `${ac.maxDimensionM} m · ${ac.maxSpeedMs} m/s`, rule: `Characteristic dimension ${ac.maxDimensionM} m, V max ${ac.maxSpeedMs} m/s`, inputs: [] },
    { id: "f-ground", kind: "fact", term: "Ground environment", value: envLabel, rule: ground.environment === "controlled" ? "Ground environment: controlled ground area" : `Ground environment: ${envLabel}, peak ${fmt(ground.peakDensity)} ppl/km²`, inputs: [] },
    { id: "f-alt", kind: "fact", term: "Altitude", value: `${input.maxAltitudeM} m AGL`, rule: `Max altitude ${input.maxAltitudeM} m AGL`, inputs: [] },
    { id: "f-airspace", kind: "fact", term: "Airspace", value: `Class ${as.airspaceClass}`, rule: `Airspace class ${as.airspaceClass}, ${["A", "B", "C", "D", "E"].includes(as.airspaceClass) ? "controlled" : "uncontrolled"}${as.urban ? ", urban" : ", rural"}`, inputs: [] },
    { id: "f-aerodrome", kind: "fact", term: "Aerodrome", value: as.aerodromeDistanceKm != null ? `${as.aerodromeDistanceKm} km` : "none", rule: as.aerodromeDistanceKm != null ? `Aerodrome proximity ${as.aerodromeDistanceKm} km${as.aerodromeIcao ? ` (${as.aerodromeIcao})` : ""}${as.aerodromeEnvironment ? ", inside its environment" : ""}` : "No aerodrome environment", inputs: [] },
  );

  // iGRC
  const ig = intrinsicGrc(input);
  trace.push({
    id: "n-igrc", kind: "derived", term: "iGRC", value: ig.value == null ? "—" : String(ig.value),
    rule: ig.rule, citation: CITE.igrc, inputs: ["f-dim", "f-ground"],
    detail: [
      `Column: ${IGRC_COLUMNS[Math.min(ig.col, IGRC_COLUMNS.length - 1)].label}${ig.col >= IGRC_COLUMNS.length ? " exceeded" : ""}`,
      `Row: ${IGRC_ROWS[ig.row].label}`,
      `MTOM ${ac.mtomKg} kg`,
    ],
  });

  // GRC
  let grc: number | null = null;
  let deltas: ReturnType<typeof mitigationDeltas> = [];
  if (ig.value != null) {
    deltas = mitigationDeltas(m);
    const raw = ig.value + deltas.reduce((s, d) => s + d.delta, 0);
    const floor = IGRC_ROWS[0].values[Math.min(ig.col, IGRC_COLUMNS.length - 1)] as number;
    grc = Math.max(raw, floor);
    const parts = deltas.length ? deltas.map((d) => `${d.label} ${d.level} (${d.delta})`).join(". ") + "." : "No ground mitigations claimed.";
    trace.push({
      id: "n-grc", kind: "derived", term: "GRC", value: String(grc),
      rule: raw < floor ? `${parts} Floored at ${floor}, the controlled-area value for this column.` : parts,
      citation: CITE.grcTable,
      inputs: ["n-igrc"],
      detail: [`iGRC ${ig.value}`, ...deltas.map((d) => `${d.label} at ${d.level}: ${d.delta}`), `Floor ${floor} (${CITE.grcFloor})`],
    });
  } else {
    trace.push({ id: "n-grc", kind: "derived", term: "GRC", value: "—", rule: "Not computed: iGRC is outside SORA scope.", inputs: ["n-igrc"] });
  }

  // ARC
  const ia = initialArc(input);
  const ra = residualArc(ia.arc, m.strategic);
  trace.push(
    { id: "n-arc", kind: "derived", term: "ARC", value: ia.arc, rule: ia.rule, citation: CITE.arc, inputs: ["f-alt", "f-airspace", "f-aerodrome"], detail: [`Altitude ${input.maxAltitudeM} m AGL (150 m threshold)`, `Class ${as.airspaceClass}`, as.geoZones.length ? `Geo-zones: ${as.geoZones.join(", ")}` : "No geo-zones intersected"] },
    { id: "n-rarc", kind: "derived", term: "Residual ARC", value: ra, rule: m.strategic ? `Strategic mitigation by operational restriction: ARC ${ia.arc} → ${ra}.` : "No strategic mitigation claimed.", citation: CITE.residualArc, inputs: ["n-arc"], detail: [`Initial ARC ${ia.arc}`, m.strategic ? "Operational restriction claimed" : "Not claimed"] },
  );

  // SAIL
  let outcome: Outcome;
  if (grc == null) outcome = { kind: "certified", reason: "The intrinsic ground risk is outside SORA scope." };
  else if (grc > 7) outcome = { kind: "certified", reason: `Final GRC ${grc} exceeds 7.` };
  else outcome = { kind: "sail", sail: sailFor(grc, ra) };

  trace.push({
    id: "root-sail", kind: "root", term: "SAIL",
    value: outcome.kind === "sail" ? roman(outcome.sail) : "—",
    rule: outcome.kind === "sail" ? `GRC ${grc} × residual ARC ${ra}` : `Certified category. ${outcome.reason}`,
    citation: CITE.sail, inputs: ["n-grc", "n-rarc"],
  });

  return {
    rulebase: { ...RULEBASE },
    igrc: ig.value, grc, initialArc: ia.arc, residualArc: ra, outcome,
    osos: outcome.kind === "sail" ? osoSet(outcome.sail) : [],
    containment: {
      status: "assessment-required",
      note: `Containment robustness depends on the adjacent area and is assessed at ${CITE.containment}.`,
    },
    trace,
  };
}

// ------------------------------------------------------------------ counterfactuals

export interface Counterfactual {
  id: string;
  title: string;
  effect: string;
  cost: string;
  input: OperationInput;
  result: Determination;
}

const sailOf = (d: Determination) => (d.outcome.kind === "sail" ? d.outcome.sail : 7);

function effectText(a: Determination, b: Determination): string {
  const out: string[] = [];
  if (a.grc !== b.grc) out.push(`GRC ${a.grc ?? "—"} → ${b.grc ?? "—"}`);
  if (a.initialArc !== b.initialArc) out.push(`ARC ${a.initialArc} → ${b.initialArc}`);
  if (a.residualArc !== b.residualArc) out.push(`Residual ARC ${a.residualArc} → ${b.residualArc}`);
  return out.join(" · ") || "No change to the chain";
}

/** Single-change alternatives that lower SAIL, best first. */
export function counterfactuals(input: OperationInput, fitted: string[] = []): Counterfactual[] {
  const base = determine(input);
  const m = input.mitigations;
  const reg = input.aircraft.registration;
  const cands: Omit<Counterfactual, "result" | "effect">[] = [];
  const withM = (patch: Partial<MitigationInput>) => ({ ...input, mitigations: { ...m, ...patch } });

  if (m.m2 !== "high") {
    const lvl = m.m2 === "none" ? "medium" : "high";
    const has = fitted.some((f) => /parachute/i.test(f));
    cands.push({
      id: `m2-${lvl}`,
      title: has ? `Claim the parachute fitted on ${reg} as M2 at ${lvl} robustness` : `Fit a parachute and claim M2 at ${lvl} robustness`,
      cost: has ? "Evidence: deployment test report, maintenance log." : "Requires a parachute system with test evidence for this airframe.",
      input: withM({ m2: lvl }),
    });
  }
  if (m.m1a !== "medium") {
    cands.push({ id: "m1a-medium", title: "Claim M1(A) sheltering at medium robustness", cost: "Requires a sheltering analysis of the ground risk buffer and a signed procedure.", input: withM({ m1a: "medium" }) });
  }
  if (m.m1b !== "high") {
    const lvl = m.m1b === "none" ? "medium" : "high";
    cands.push({ id: `m1b-${lvl}`, title: `Claim M1(B) operational restrictions at ${lvl} robustness`, cost: "Requires evidence that people at risk are reduced, e.g. a timed closure procedure.", input: withM({ m1b: lvl }) });
  }
  if (!m.strategic) {
    cands.push({ id: "strategic", title: "Claim strategic mitigation by operational restriction", cost: "Daylight only, corridor confined, NOTAM filed. Evidence: restriction procedure.", input: withM({ strategic: true }) });
  }
  if (input.maxAltitudeM > 150) {
    cands.push({ id: "alt-120", title: "Lower maximum altitude to 120 m AGL", cost: "No equipment change. Check corridor coverage at the lower height.", input: { ...input, maxAltitudeM: 120 } });
  }
  if (input.airspace.aerodromeEnvironment) {
    cands.push({
      id: "aerodrome",
      title: `Route the flight geography outside the aerodrome environment${input.airspace.aerodromeIcao ? ` of ${input.airspace.aerodromeIcao}` : ""}`,
      cost: "Shortens or re-routes the corridor. Re-run the map step to confirm.",
      input: { ...input, airspace: { ...input.airspace, aerodromeEnvironment: false } },
    });
  }

  return cands
    .map((c) => {
      const result = determine(c.input);
      return { ...c, result, effect: effectText(base, result) };
    })
    .filter((c) => sailOf(c.result) < sailOf(base))
    .sort((a, b) => sailOf(a.result) - sailOf(b.result));
}
