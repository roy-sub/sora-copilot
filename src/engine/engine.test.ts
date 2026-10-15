import { test } from "node:test";
import assert from "node:assert/strict";
import { counterfactuals, determine, igrcColumn, initialArc, sailFor } from "./engine.ts";
import { checkCategory } from "./checker.ts";
import { OPERATIONS, POWERLINE_INPUT } from "../data/fixtures.ts";

test("iGRC column requires both dimension and speed to fit", () => {
  assert.equal(igrcColumn(0.9, 23), 0);
  assert.equal(igrcColumn(0.9, 30), 1); // speed pushes it out of the 1 m column
  assert.equal(igrcColumn(1.98, 36), 2);
  assert.equal(igrcColumn(50, 10), 5); // beyond the table
});

test("powerline corridor resolves to SAIL III via GRC 4 × residual ARC b", () => {
  const d = determine(POWERLINE_INPUT);
  assert.equal(d.igrc, 5);
  assert.equal(d.grc, 4);
  assert.equal(d.initialArc, "c");
  assert.equal(d.residualArc, "b");
  assert.deepEqual(d.outcome, { kind: "sail", sail: 3 });
  assert.equal(d.osos.length, 17);
  assert.ok(d.trace.every((n) => n.kind === "fact" || n.citation), "every derived node cites its rule");
});

test("fixture operations reproduce their recorded SAILs", () => {
  const want: Record<string, number | "certified"> = {
    "powerline-mur": 3, "roof-reininghaus": 2, "quarry-peggau": 2, "pipeline-leibnitz": 4, "thermal-werk2": 1, "schlossberg-event": "certified",
  };
  for (const op of OPERATIONS) {
    const d = determine(op.input);
    const got = d.outcome.kind === "sail" ? d.outcome.sail : "certified";
    assert.equal(got, want[op.id], op.id);
  }
});

test("final GRC is floored at the controlled-area value of its column", () => {
  const d = determine({ ...POWERLINE_INPUT, ground: { environment: "controlled", peakDensity: 0 }, mitigations: { ...POWERLINE_INPUT.mitigations, m1a: "medium", m2: "high" } });
  assert.equal(d.igrc, 1);
  assert.equal(d.grc, 1);
});

test("mitigations cannot be claimed at levels the table does not offer", () => {
  assert.throws(() => determine({ ...POWERLINE_INPUT, mitigations: { ...POWERLINE_INPUT.mitigations, m2: "low" as never } }));
});

test("ARC tree", () => {
  const base = { ...POWERLINE_INPUT, airspace: { ...POWERLINE_INPUT.airspace, aerodromeEnvironment: false } };
  assert.equal(initialArc(base).arc, "b");
  assert.equal(initialArc({ ...base, airspace: { ...base.airspace, urban: true } }).arc, "c");
  assert.equal(initialArc({ ...base, maxAltitudeM: 200, airspace: { ...base.airspace, airspaceClass: "C" } }).arc, "d");
  assert.equal(initialArc({ ...base, airspace: { ...base.airspace, airspaceClass: "D", aerodromeEnvironment: true } }).arc, "d");
  assert.equal(initialArc({ ...base, airspace: { ...base.airspace, atypical: true } }).arc, "a");
});

test("SAIL table edges", () => {
  assert.equal(sailFor(1, "a"), 1);
  assert.equal(sailFor(4, "d"), 6);
  assert.equal(sailFor(7, "a"), 6);
});

test("counterfactuals only offer changes that lower SAIL", () => {
  const cfs = counterfactuals(POWERLINE_INPUT, ["Parachute", "FTS"]);
  assert.ok(cfs.length >= 2);
  for (const c of cfs) assert.ok(c.result.outcome.kind === "sail" && c.result.outcome.sail < 3, c.id);
  assert.ok(cfs.some((c) => c.id === "m2-medium" && /parachute fitted/.test(c.title)));
});

test("category checker", () => {
  assert.equal(checkCategory({ mass: "sub250", ground: "populated", operation: "VLOS" }).category, "open");
  assert.equal(checkCategory({ mass: "4to25", ground: "populated", operation: "VLOS" }).category, "specific");
  const r = checkCategory({ mass: "4to25", ground: "sparsely", operation: "BVLOS" });
  assert.equal(r.category, "specific");
  if (r.category === "specific") {
    assert.equal(r.determination.igrc, 5);
    assert.deepEqual(r.determination.outcome, { kind: "sail", sail: 4 });
    assert.ok(r.hint);
  }
});
