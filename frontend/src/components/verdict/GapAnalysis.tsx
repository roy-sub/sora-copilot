"use client";

/**
 * OSOs required against OSOs evidenced, grouped by robustness.
 *
 * Not-required OSOs are **listed**, not omitted: an absent row reads as an oversight, and
 * a compliance officer will take it as one. Evidence state uses a glyph plus the word,
 * never colour alone.
 */

import { EvidenceMark, type EvidenceState } from "@/components/Brand";
import type { OsoRequirement, Robustness } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const GROUPS: { level: Robustness; label: string }[] = [
  { level: "high", label: "High robustness" },
  { level: "medium", label: "Medium robustness" },
  { level: "low", label: "Low robustness" },
];

export const evidenceStateOf = (oso: OsoRequirement): EvidenceState => {
  if (oso.required_robustness === "none") return "na";
  if (oso.status === "verified" || oso.status === "documented") return "evidenced";
  if (oso.status === "claimed") return "partial";
  return "gap";
};

export function GapAnalysis({
  osos,
  onOpen,
}: {
  osos: OsoRequirement[];
  onOpen: (osoId: string) => void;
}) {
  const required = osos.filter((o) => o.required_robustness !== "none");
  const notRequired = osos.filter((o) => o.required_robustness === "none");
  const gaps = required.filter((o) => evidenceStateOf(o) === "gap").length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-4 flex-wrap">
        <div>
          <h3 className="m-0 t-h3 text-ink-hi">Gap analysis</h3>
          <p className="mt-1 mb-0 t-body-sm text-ink-mid pretty">
            {required.length} of {osos.length} operational safety objectives apply at this
            SAIL. {gaps === 0 ? "Every one has evidence." : `${gaps} have no evidence yet.`}
          </p>
        </div>
        <span className="t-data-sm text-ink-low tnum">
          {required.length - gaps} / {required.length} evidenced
        </span>
      </div>

      {GROUPS.map((group) => {
        const rows = required.filter((o) => o.required_robustness === group.level);
        if (!rows.length) return null;
        return (
          <div key={group.level} className="flex flex-col gap-2">
            <span className="t-micro text-ink-low">
              {group.label} · {rows.length}
            </span>
            <div className="grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(300px,1fr))]">
              {rows.map((oso) => (
                <OsoRow key={oso.oso_id} oso={oso} onOpen={() => onOpen(oso.oso_id)} />
              ))}
            </div>
          </div>
        );
      })}

      {notRequired.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="t-micro text-ink-low">Not required at this SAIL · {notRequired.length}</span>
          <div className="flex flex-wrap gap-2">
            {notRequired.map((oso) => (
              <span
                key={oso.oso_id}
                title={oso.title}
                className="inline-flex items-center gap-2 min-h-8 px-2.5 rounded-sm bg-sheet-well t-data-sm text-ink-low"
              >
                <span aria-hidden>⊘</span>
                {oso.oso_id}
              </span>
            ))}
          </div>
          <span className="t-cap text-ink-low pretty">
            Listed rather than hidden, so it is clear they were considered and found not
            to apply.
          </span>
        </div>
      )}
    </div>
  );
}

function OsoRow({ oso, onOpen }: { oso: OsoRequirement; onOpen: () => void }) {
  const state = evidenceStateOf(oso);
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        "bg-sheet-well hover:bg-sheet-raised tr-ui p-3.5 min-h-11 flex items-start gap-3 border-0 text-left",
        state === "gap" && "shadow-[inset_2px_0_0_var(--sail-6)]",
      )}
    >
      <span className="t-data-sm text-ink-hi tnum w-[58px] flex-none">{oso.oso_id}</span>
      <span className="flex-1 min-w-0">
        <span className="block t-body-sm leading-[1.4] text-ink-hi pretty">{oso.title}</span>
        <span className="block mt-1.5">
          <EvidenceMark state={state} />
        </span>
      </span>
    </button>
  );
}
