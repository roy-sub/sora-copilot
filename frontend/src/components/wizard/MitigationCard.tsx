"use client";

/**
 * One mitigation, its claimable levels, and what claiming it would cost.
 *
 * A level the table does not offer is **disabled, not hidden** — the design's rule, and
 * the right one: hiding it leaves the operator wondering whether they missed something,
 * while disabling it shows the path exists and this is not it.
 *
 * The deltas shown here come from the rulebase, and the engine refuses a claim the table
 * does not support rather than quietly ignoring it, so a disabled button and a refused
 * determination say the same thing.
 */

import type { Robustness } from "@/lib/api-client";
import { cn } from "@/lib/cn";

export type MitigationKind =
  | "m1_strategic"
  | "m1_ers"
  | "m2_impact"
  | "strategic_air"
  | "tactical_air";

export interface MitigationSpec {
  kind: MitigationKind;
  name: string;
  delta: string;
  /** Levels the transcribed table offers. Everything else renders disabled. */
  claimable: Robustness[];
  evidence: string;
  /** Shown when the aircraft does not carry what the mitigation needs. */
  requires?: { fitted: string; label: string };
}

export const MITIGATIONS: MitigationSpec[] = [
  {
    kind: "m1_strategic",
    name: "M1 — Sheltering",
    delta: "GRC −1 at low, −2 at medium",
    claimable: ["low", "medium"],
    evidence: "Sheltering analysis of the ground risk buffer; a signed procedure at medium.",
  },
  {
    kind: "m1_ers",
    name: "M1 — Ground observation",
    delta: "GRC −1 at low",
    claimable: ["low"],
    evidence: "A ground observation procedure naming who watches and from where.",
  },
  {
    kind: "m2_impact",
    name: "M2 — Impact reduction",
    delta: "GRC −1 at medium, −2 at high",
    claimable: ["medium", "high"],
    evidence: "Deployment test report and maintenance log; qualified to a standard at high.",
    requires: { fitted: "parachute", label: "a parachute or equivalent fitted to the aircraft" },
  },
  {
    kind: "strategic_air",
    name: "Strategic — air risk",
    delta: "Lowers the ARC by one class",
    claimable: ["low"],
    evidence: "Operational restriction procedure and a filed NOTAM.",
  },
];

const ALL_LEVELS: Robustness[] = ["low", "medium", "high"];

export function MitigationCard({
  spec,
  value,
  fitted,
  onChange,
}: {
  spec: MitigationSpec;
  value: Robustness;
  fitted: string[];
  onChange: (level: Robustness) => void;
}) {
  const needsEquipment = spec.requires
    ? !fitted.some((f) => f.toLowerCase().includes(spec.requires!.fitted))
    : false;

  return (
    <div className="bg-sheet-well p-4 flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="t-data text-[14px] font-semibold leading-[1.3] text-ink-hi">
          {spec.name}
        </span>
        <span className="t-micro-10 text-ink-low">{spec.delta}</span>
      </div>

      <div
        role="radiogroup"
        aria-label={spec.name}
        className="flex gap-sheet bg-hairline border border-hairline rounded-sm overflow-hidden"
      >
        <button
          type="button"
          role="radio"
          aria-checked={value === "none"}
          onClick={() => onChange("none")}
          className={cn(
            "flex-1 min-h-11 t-micro-10 border-0 tr-ui",
            value === "none" ? "bg-accent text-accent-ink" : "bg-sheet-well text-ink-mid hover:text-ink-hi",
          )}
        >
          Not claimed
        </button>
        {ALL_LEVELS.map((level) => {
          const offered = spec.claimable.includes(level);
          const blocked = !offered || (needsEquipment && level !== "none");
          const on = value === level;
          return (
            <button
              key={level}
              type="button"
              role="radio"
              aria-checked={on}
              disabled={blocked}
              title={
                !offered
                  ? "The SORA table does not offer this mitigation at this robustness."
                  : needsEquipment
                    ? `Requires ${spec.requires?.label}.`
                    : undefined
              }
              onClick={() => onChange(level)}
              className={cn(
                "flex-1 min-h-11 t-micro-10 border-0 tr-ui disabled:opacity-35 disabled:cursor-not-allowed",
                on ? "bg-accent text-accent-ink" : "bg-sheet-well text-ink-mid hover:text-ink-hi",
              )}
            >
              {level}
            </button>
          );
        })}
      </div>

      <span className="t-cap text-ink-mid pretty">Evidence: {spec.evidence}</span>

      {needsEquipment && (
        <span className="t-cap text-sail-3 pretty">
          Not claimable on this aircraft: it needs {spec.requires?.label}. Add it to the
          aircraft record in the fleet and it becomes available.
        </span>
      )}

      {spec.claimable.length < 3 && !needsEquipment && (
        <span className="t-cap text-ink-low pretty">
          The levels shown greyed out are not offered for this mitigation by the SORA
          table, so the engine would refuse them.
        </span>
      )}
    </div>
  );
}
