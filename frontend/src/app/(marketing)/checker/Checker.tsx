"use client";

import { useMemo, useState } from "react";
import { PreliminaryNotice, PreliminaryTag } from "@/components/Preliminary";
import { Disclaimer, STAMP } from "@/components/Brand";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { ButtonLink } from "@/components/ui/Button";
import { RadioRow, Segmented } from "@/components/ui/Field";
import { checkCategory, MASS_BANDS, type CheckerAnswers, type MassBand } from "@/engine/checker";
import { roman } from "@/engine/engine";
import type { GroundEnvironment, OperationType } from "@/engine/types";

const GROUND: { id: GroundEnvironment; label: string }[] = [
  { id: "controlled", label: "Controlled ground area" },
  { id: "sparsely", label: "Sparsely populated" },
  { id: "populated", label: "Populated area" },
  { id: "assembly", label: "Assembly of people" },
];

const OPS: { value: OperationType; label: string }[] = [
  { value: "VLOS", label: "VLOS" }, { value: "EVLOS", label: "EVLOS" }, { value: "BVLOS", label: "BVLOS" },
];

export function Checker() {
  const [a, setA] = useState<CheckerAnswers>({ mass: "4to25", ground: "sparsely", operation: "BVLOS" });
  const r = useMemo(() => checkCategory(a), [a]);
  const key = `${a.mass}-${a.ground}-${a.operation}`;

  const d = r.category === "open" ? null : r.determination;
  const sail = d && d.outcome.kind === "sail" ? d.outcome.sail : null;
  const title = r.category === "open" ? `Open category · ${r.subcategory}` : r.category === "specific" ? "Specific category" : "Certified category";
  const lead =
    r.category === "open" ? `${r.reason} No operational authorisation is needed; the subcategory rules apply.`
    : r.category === "specific" ? `${r.reason} This operation needs an operational authorisation. Estimated SAIL ${sail ? roman(sail) : "—"} before mitigations are claimed.`
    : `${r.reason} The operation falls outside SORA and needs certification of the aircraft and operator.`;

  const mail = `mailto:?subject=${encodeURIComponent("SORA Copilot estimate")}&body=${encodeURIComponent(`${title}\n${lead}\n${STAMP}`)}`;

  return (
    <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(340px,100%),1fr))]">
      <div className="bg-sheet px-4 py-8 md:px-12 md:pt-8 md:pb-12 flex flex-col gap-8">
        <fieldset className="m-0 p-0 border-0 flex flex-col gap-3">
          <legend className="t-micro text-ink-low mb-3">01 — Aircraft mass and size</legend>
          <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
            {MASS_BANDS.map((m) => (
              <RadioRow key={m.id} name="q1" title={m.label} checked={a.mass === m.id} onChange={() => setA({ ...a, mass: m.id as MassBand })} className="min-h-12 py-3.5" />
            ))}
          </div>
        </fieldset>
        <fieldset className="m-0 p-0 border-0 flex flex-col gap-3">
          <legend className="t-micro text-ink-low mb-3">02 — What is underneath</legend>
          <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
            {GROUND.map((g) => (
              <RadioRow key={g.id} name="q2" title={g.label} checked={a.ground === g.id} onChange={() => setA({ ...a, ground: g.id })} className="min-h-12 py-3.5" />
            ))}
          </div>
        </fieldset>
        <div className="flex flex-col gap-3">
          <span className="t-micro text-ink-low">03 — How you will fly it</span>
          <Segmented label="How you will fly it" size="lg" options={OPS} value={a.operation} onChange={(v) => setA({ ...a, operation: v })} className="rounded-none" />
        </div>
      </div>

      <div className="bg-sheet-raised px-4 py-8 md:p-12 flex flex-col gap-6" aria-live="polite">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <span className="t-micro text-ink-low">Result</span>
          <PreliminaryTag />
        </div>
        <div key={key} className="flex items-center gap-6 flex-wrap animate-[node-settle_240ms_var(--ease-ui)_both]">
          {sail ? <SailBadge level={sail} size="lg" /> : <SailPlaceholder size="lg" label={r.category === "open" ? "NO SAIL" : "OUT OF SORA"} />}
          <div className="flex flex-col gap-2 min-w-[200px] flex-1">
            <span className="t-h2 text-ink-hi">{title}</span>
            <p className="m-0 t-body-sm text-ink-mid pretty">{lead}</p>
          </div>
        </div>
        {d && (
          <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
            {[
              ["Estimated iGRC", d.igrc ?? "—"],
              ["Estimated ARC", d.initialArc],
              ["OSOs at this SAIL", d.osos.filter((o) => o.level !== "nr").length || "—"],
            ].map(([k, v]) => (
              <div key={k} className="bg-sheet-well px-4 py-3 flex justify-between gap-3 t-data-13 text-ink-hi min-h-11 items-center">
                <span className="text-ink-mid">{k}</span><span>{v}</span>
              </div>
            ))}
          </div>
        )}
        {r.category === "specific" && r.hint && <p className="m-0 t-body-sm leading-[1.55] text-ink-mid pretty">Mitigations can move this. {r.hint}</p>}
        <p className="m-0 t-cap text-ink-low pretty">Assumes a typical aircraft for the mass band, class G airspace below 120 m AGL, no aerodrome environment. {STAMP}.</p>
        <div className="flex gap-2.5 flex-wrap">
          <ButtonLink href="/app/new" shape="pill" size="lg">Run the full assessment</ButtonLink>
          <a href={mail} className="no-underline inline-flex items-center justify-center min-h-12 px-6 border border-hairline-strong rounded-pill t-micro text-ink-hi hover:bg-sheet hover:text-ink-hi tr-ui">Email me this estimate</a>
        </div>
        <PreliminaryNotice />
        <Disclaimer className="pt-5 border-t border-hairline" />
      </div>
    </section>
  );
}
