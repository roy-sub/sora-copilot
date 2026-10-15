"use client";

import { EvidenceMark, EVIDENCE_TONE, RobustnessPill, type EvidenceState } from "@/components/Brand";
import { roman } from "@/engine/engine";
import type { OsoRequirement, Sail } from "@/engine/types";

export type OsoRow = OsoRequirement & { state: EvidenceState };

const GROUPS = ["high", "medium", "low"] as const;

export function GapAnalysis({ rows, sail, onOpen }: { rows: OsoRow[]; sail: Sail; onOpen: (num: number) => void }) {
  const req = rows.filter((r) => r.level !== "nr");
  const count = (s: EvidenceState) => req.filter((r) => r.state === s).length;
  const nr = rows.filter((r) => r.level === "nr");
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 flex-wrap mb-4">
        <div>
          <h3 className="m-0 t-h3 text-ink-hi">Gap analysis</h3>
          <p className="mt-1 mb-0 t-body-sm text-ink-mid">
            {req.length} OSOs required at SAIL {roman(sail)}. {count("evidenced")} evidenced, {count("partial")} partial, {count("gap")} gaps{count("na") ? `, ${count("na")} not applicable` : ""}.
          </p>
        </div>
        <div className="flex gap-4 flex-wrap">
          {(["evidenced", "partial", "gap"] as const).map((s) => <EvidenceMark key={s} state={s} />)}
        </div>
      </div>
      <div className="flex flex-col gap-6">
        {GROUPS.map((g) => {
          const list = req.filter((r) => r.level === g);
          if (!list.length) return null;
          return (
            <section key={g} aria-label={`${g} robustness`}>
              <div className="flex items-center gap-3 mb-2"><RobustnessPill level={g} /><span className="t-data-sm text-ink-low">{list.length} OSO{list.length > 1 ? "s" : ""}</span></div>
              <div className="grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(min(360px,100%),1fr))]">
                {list.map((o) => (
                  <button key={o.num} type="button" onClick={() => onOpen(o.num)}
                    className="bg-sheet-well hover:bg-sheet-raised border-0 text-left px-4 py-3.5 flex items-center gap-3.5 min-h-14 tr-ui">
                    <span className="text-[12px] font-semibold leading-none text-ink-mid min-w-[58px] tnum">{o.id}</span>
                    <span className="flex-1 t-body-sm leading-[1.4] text-ink-hi pretty">{o.name}</span>
                    <span className={`inline-flex items-center gap-1.5 min-w-[84px] t-data-sm leading-none ${EVIDENCE_TONE[o.state].ink}`}>
                      <span aria-hidden>{EVIDENCE_TONE[o.state].glyph}</span>{EVIDENCE_TONE[o.state].label}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          );
        })}
        {nr.length > 0 && (
          <p className="m-0 t-cap text-ink-low pretty">Not required at SAIL {roman(sail)}: {nr.map((o) => o.id).join(", ")}.</p>
        )}
      </div>
    </div>
  );
}
