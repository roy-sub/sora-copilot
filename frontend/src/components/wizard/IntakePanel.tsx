"use client";

/**
 * The conversational intake panel.
 *
 * Design brief §12: this is the visible boundary between the LLM and the engine, and
 * that boundary is the brand. So the panel is built to make the boundary legible rather
 * than to feel like a chatbot:
 *
 * - the heading of the list is "Extracted facts — not yet in the engine"
 * - every chip shows its state as a word, not only as a colour
 * - the panel says which extractor read the text, because an operator should know
 *   whether a language model was involved
 * - nothing here can show a SAIL, because extraction has no field to put one in
 */

import { useState } from "react";
import { FactChip } from "@/components/wizard/FactChip";
import type { StepKey } from "@/components/wizard/WizardStepper";
import type { Drone, Extractor, ProposedFact } from "@/lib/api-client";
import type { ApiError } from "@/lib/api";
import { PlanLimit } from "@/components/PlanLimit";
import { cn } from "@/lib/cn";

const SEED =
  "Alta X along the 110 kV line south of Gratkorn, about 14 km, below 120 metres, farmland and a few scattered houses.";

export function IntakePanel({
  facts,
  fleet,
  extractor,
  busy,
  error,
  limit,
  onSend,
  onConfirm,
  onReject,
  onEdit,
  onHide,
  className,
}: {
  facts: ProposedFact[];
  fleet: Drone[];
  extractor: Extractor | null;
  busy: boolean;
  error: string | null;
  /** A plan refusal, shown as an upgrade panel rather than as an error. */
  limit: ApiError | null;
  onSend: (text: string) => void;
  onConfirm: (factId: string) => void;
  onReject: (factId: string) => void;
  onEdit: (step: StepKey) => void;
  onHide?: () => void;
  className?: string;
}) {
  const [text, setText] = useState("");
  const pending = facts.filter((f) => f.status === "pending");
  const decided = facts.filter((f) => f.status !== "pending");
  const nameFor = (id: string) => fleet.find((d) => d.id === id)?.name;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    onSend(value);
    setText("");
  };

  return (
    <aside className={cn("bg-sheet p-5 flex flex-col gap-4 min-w-0", className)}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="m-0 t-h4 text-ink-hi">Describe the mission</h3>
        {onHide && (
          <button
            type="button"
            onClick={onHide}
            className="min-h-11 px-3 bg-transparent border border-hairline rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
          >
            Hide
          </button>
        )}
      </div>

      <p className="m-0 t-body-sm text-ink-mid pretty">
        Write it the way you would tell a colleague. What comes back is a list of
        candidate facts for you to confirm — never a conclusion.
      </p>

      {facts.length === 0 && (
        <button
          type="button"
          onClick={() => setText(SEED)}
          className="text-left p-3 bg-sheet-well rounded-sm border-0 hover:bg-sheet-raised tr-ui"
        >
          <span className="t-micro-10 text-ink-low">Try this</span>
          <p className="m-0 mt-1.5 t-body-sm text-ink-mid pretty">“{SEED}”</p>
        </button>
      )}

      <div className="flex flex-col gap-1.5">
        <span className="t-micro text-ink-low">Extracted facts — not yet in the engine</span>
        <p className="m-0 t-cap text-ink-low pretty">
          Each one needs your confirmation. Rejecting a fact returns you to the step that
          owns it, where you set it yourself.
        </p>
      </div>

      {limit && <PlanLimit error={limit} compact />}

      {error && (
        <div role="alert" className="p-3 bg-sheet-well border-l-[3px] border-sail-6 rounded-sm">
          <span className="t-micro-10 text-sail-6">Extraction failed</span>
          <p className="m-0 mt-1 t-cap text-ink-mid pretty">{error}</p>
        </div>
      )}

      {facts.length === 0 && !error && !limit && (
        <p className="m-0 t-cap text-ink-low pretty">
          Nothing extracted yet. You can also fill the steps in directly — the panel is a
          shortcut, not a requirement.
        </p>
      )}

      <div className="flex flex-col gap-2.5">
        {[...pending, ...decided].map((fact) => (
          <FactChip
            key={fact.id}
            fact={fact}
            aircraftName={fact.field === "drone_id" ? nameFor(String(fact.value)) : undefined}
            busy={busy}
            onConfirm={() => onConfirm(fact.id)}
            onReject={() => onReject(fact.id)}
            onEdit={onEdit}
          />
        ))}
      </div>

      {extractor && (
        <p className="m-0 t-cap text-ink-low pretty">
          {extractor === "llm"
            ? "Read by a language model, which proposes facts and never computes a risk value."
            : "Read by the deterministic extractor: no language-model key is configured, so keywords and patterns were used."}
        </p>
      )}

      <form onSubmit={submit} className="mt-auto flex gap-2">
        <label className="sr-only" htmlFor="intake-text">
          Describe the mission
        </label>
        <input
          id="intake-text"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add detail"
          disabled={busy}
          className="flex-1 min-w-0 min-h-11 px-3 bg-field border border-field-border rounded-sm text-[13px] text-ink-hi placeholder:text-ink-low disabled:opacity-50"
        />
        <button
          type="submit"
          aria-label="Extract facts"
          disabled={busy || !text.trim()}
          className="size-11 flex-none grid place-items-center bg-sheet-alt text-ink-hi border-0 rounded-sm disabled:opacity-35 press tr-ui"
        >
          {busy ? <span className="t-micro-10">…</span> : <span aria-hidden>→</span>}
        </button>
      </form>
    </aside>
  );
}
