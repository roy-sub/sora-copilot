"use client";

/**
 * The boundary between the language model and the engine, made visible.
 *
 * Three states, each with a 3px left band AND the state word, because the band colour
 * must never be the only signal:
 *
 * - unconfirmed — sail-3 band, the only state with Confirm and Reject
 * - confirmed — accent band, keeps an Edit affordance
 * - rejected — hairline band, struck through; rejecting offers the step that owns the fact
 *
 * Nothing silently returns to unconfirmed. A chip's state is a decision the operator
 * made, and the dossier records who made it.
 */

import type { ProposedFact } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import type { StepKey } from "@/components/wizard/WizardStepper";

const STATE_WORD: Record<ProposedFact["status"], string> = {
  pending: "Unconfirmed",
  confirmed: "Confirmed",
  rejected: "Rejected",
};

const BAND: Record<ProposedFact["status"], string> = {
  pending: "border-sail-3",
  confirmed: "border-accent",
  rejected: "border-hairline-strong",
};

const TONE: Record<ProposedFact["status"], string> = {
  pending: "text-sail-3",
  confirmed: "text-accent",
  rejected: "text-ink-low",
};

/** A value in the operator's words rather than the wire's. */
export function factValue(fact: ProposedFact, aircraftName?: string): string {
  const v = fact.value;
  if (fact.field === "drone_id") return aircraftName ?? String(v);
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (fact.field === "volume.max_altitude_agl_m") return `${v} m AGL`;
  if (fact.field === "population_density_per_km2") return `${Number(v).toLocaleString("en-GB")} ppl/km²`;
  if (fact.field === "airspace_class") return `Class ${String(v).toUpperCase()}`;
  if (fact.field === "operation_type") return String(v).toUpperCase();
  return String(v).replace(/_/g, " ");
}

export function FactChip({
  fact,
  aircraftName,
  busy,
  onConfirm,
  onReject,
  onEdit,
}: {
  fact: ProposedFact;
  aircraftName?: string;
  busy?: boolean;
  onConfirm: () => void;
  onReject: () => void;
  onEdit: (step: StepKey) => void;
}) {
  const unconfirmed = fact.status === "pending";
  const rejected = fact.status === "rejected";

  return (
    <div
      className={cn(
        "flex flex-col gap-2.5 p-3 rounded-sm bg-sheet-well border-l-[3px]",
        BAND[fact.status],
        busy && "opacity-60 pointer-events-none",
      )}
    >
      <div className="flex items-start justify-between gap-2.5">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="t-micro-10 text-ink-low">{fact.label}</span>
          <p
            className={cn(
              "m-0 t-data-13 leading-[1.4] pretty",
              rejected ? "text-ink-low line-through" : "text-ink-hi",
            )}
          >
            {factValue(fact, aircraftName)}
          </p>
        </div>
        <span className={cn("t-micro-10 flex-none", TONE[fact.status])}>
          {STATE_WORD[fact.status]}
        </span>
      </div>

      {fact.source_span && (
        <p className="m-0 t-cap leading-[1.45] text-ink-low pretty">
          <span aria-hidden>“</span>
          {fact.source_span}
          <span aria-hidden>”</span>
        </p>
      )}

      {unconfirmed && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onConfirm}
            className="flex-1 min-h-11 bg-accent text-accent-ink border-0 rounded-sm t-micro-10 press tr-ui"
          >
            Confirm
          </button>
          <button
            type="button"
            onClick={onReject}
            className="flex-1 min-h-11 bg-transparent text-ink-mid border border-hairline-strong rounded-sm t-micro-10 hover:text-ink-hi tr-ui"
          >
            Reject
          </button>
        </div>
      )}

      {fact.status === "confirmed" && (
        <button
          type="button"
          onClick={() => onEdit(fact.owning_step as StepKey)}
          className="self-start min-h-11 px-0 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-ink-hi tr-ui underline"
        >
          Edit at the {fact.owning_step} step
        </button>
      )}

      {rejected && (
        <button
          type="button"
          onClick={() => onEdit(fact.owning_step as StepKey)}
          className="self-start min-h-11 px-0 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-ink-hi tr-ui underline"
        >
          Set it yourself at the {fact.owning_step} step
        </button>
      )}
    </div>
  );
}
