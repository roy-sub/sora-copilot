import Link from "next/link";
import { MediaSlot } from "@/components/MediaSlot";
import type { MediaId } from "@/lib/media-manifest";
import { STAMP } from "@/components/Brand";
import { ButtonLink } from "@/components/ui/Button";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/Chrome";
import { Faq } from "@/components/marketing/Faq";
import { Tiers } from "@/components/marketing/Tiers";

// SORA 2.5 defines 17 operational safety objectives (#01–09, 13, 16–20, 23, 24).
// The engine derives the count from its own table; this is the landing page's copy,
// kept in step with backend/app/engine/rulebase/sora_2_5/tables/oso.csv.
const N_OSO = 17;

const CHAIN = [
  ["Step 01", "iGRC", "Characteristic dimension, speed and the population under the flight geography. Class 1–10."],
  ["Step 02 · M1 / M2", "GRC", "Ground mitigations applied at their evidenced robustness. Final ground risk class."],
  ["Step 03", "ARC", "Airspace class, altitude band, aerodrome proximity and traffic. a, b, c or d."],
  ["Step 04", "Residual ARC", "Strategic mitigation by operational restriction or common structure."],
] as const;

// What each portrait depicts lives in lib/media-manifest.ts, so it is stated once.
const PERSONAS = [
  ["persona-1", "Inspection company, Graz.", "Takes the roof survey it used to decline, because the assessment now costs an afternoon."],
  ["persona-2", "Solo BVLOS operator.", "Wants one answer before quoting: can this fly, and if not, what would it take."],
  ["persona-3", "Compliance officer.", "Reads the trace before the verdict. Signs nothing that cannot be defended clause by clause."],
] as const satisfies readonly (readonly [MediaId, string, string])[];

function Feature({ n, title, body, children }: { n: string; title: string; body: string; children?: React.ReactNode }) {
  return (
    <div className="bg-sheet p-6 md:p-12 flex flex-col justify-center gap-4 min-w-0">
      <span className="t-micro text-ink-low">{n}</span>
      <h3 className="m-0 t-h2 text-ink-hi pretty">{title}</h3>
      <p className="m-0 max-w-[44ch] t-body text-ink-mid pretty">{body}</p>
      {children}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="flex flex-col gap-sheet bg-ground">
      <MarketingHeader />

      <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))]">
        <div className="bg-sheet px-4 py-8 md:px-12 md:py-16 flex flex-col justify-between gap-10 min-w-0">
          <div>
            <h1 className="m-0 mb-5 t-display text-ink-hi pretty">From mission to dossier in minutes.</h1>
            <p className="m-0 max-w-[52ch] t-body-lg text-ink-mid pretty">
              Describe the operation. The rules engine computes iGRC, GRC, ARC and SAIL, then emits an authority-ready dossier. Every line cites its rule.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <ButtonLink href="/checker" shape="pill" size="lg" className="text-[13px] px-8">Run the category checker</ButtonLink>
            <ButtonLink href="/app/?example=1" variant="secondary" shape="pill" size="lg" className="text-[13px] px-8">See a worked example</ButtonLink>
            <span className="t-data-sm text-ink-low">{STAMP}</span>
          </div>
        </div>
        <div className="bg-sheet-raised p-6 md:p-12 flex flex-col justify-between gap-8 min-w-0">
          <div>
            <div className="text-[44px] md:text-[56px] font-bold leading-none tracking-[-.03em] text-ink-hi tnum">€1,000–5,000</div>
            <div className="mt-2 t-micro text-ink-low">Consultant fee per assessment</div>
          </div>
          <div>
            <div className="text-[44px] md:text-[56px] font-bold leading-none tracking-[-.03em] text-ink-hi tnum">{N_OSO}</div>
            <div className="mt-2 t-micro text-ink-low">OSOs checked on every run</div>
          </div>
          <p className="m-0 t-body-sm text-ink-mid max-w-[34ch] pretty">Operators decline work they could legally take because the paperwork costs more than the job.</p>
        </div>
      </section>

      <section className="bg-sheet p-sheet">
        <MediaSlot id="hero-loop" lazy={false} />
      </section>

      <section id="how" className="bg-sheet px-4 py-12 md:px-12 md:py-16">
        <div className="flex items-baseline justify-between gap-6 flex-wrap mb-10">
          <h2 className="m-0 t-h1 text-ink-hi max-w-[22ch] pretty">The chain the authority will read, computed in front of you</h2>
          <p className="m-0 max-w-[40ch] t-body text-ink-mid pretty">Five determinations, each one derived from the one before it, each one traceable to the clause that produced it.</p>
        </div>
        <ol className="m-0 p-0 list-none grid gap-sheet bg-hairline grid-cols-[repeat(auto-fit,minmax(170px,1fr))]">
          {CHAIN.map(([k, t, b], i) => (
            <li key={t} className="bg-sheet-well p-6 flex flex-col gap-2.5 min-h-[168px]" style={{ animation: `chain-link var(--t-panel) var(--ease-ui) ${i * 90}ms both` }}>
              <span className="t-micro text-ink-low">{k}</span>
              <span className="t-h2 text-ink-hi">{t}</span>
              <span className="t-body-sm text-ink-mid pretty">{b}</span>
            </li>
          ))}
          <li className="bg-accent p-6 flex flex-col gap-2.5 min-h-[168px]" style={{ animation: "chain-link var(--t-panel) var(--ease-ui) 360ms both" }}>
            <span className="t-micro text-accent-ink opacity-70">Step 05 · GRC × ARC</span>
            <span className="t-h2 text-accent-ink">SAIL I–VI</span>
            <span className="t-body-sm text-accent-ink pretty">Sets the {N_OSO} OSOs at Low, Medium or High robustness, then containment.</span>
          </li>
        </ol>
      </section>

      <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(340px,100%),1fr))]">
        <Feature n="01 — Trace" title="Every line cites its rule" body="The derivation tree holds the whole determination. Each node names the rule that fired and the clause it comes from; the raw facts you confirmed sit at the leaves. A case officer can follow it without asking you a question." />
        <div className="bg-sheet p-4 md:p-6 min-w-0">
          <MediaSlot id="feature-trace" />
        </div>
      </section>

      <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(340px,100%),1fr))]">
        <div className="bg-sheet p-4 md:p-6 min-w-0">
          <MediaSlot id="feature-map" />
        </div>
        <Feature n="02 — Geography" title="Draw the flight geography. The volumes follow." body="Contingency volume and ground risk buffer are derived from your aircraft's speed, altitude and response times, not typed in. Population density and ED-269 geo-zones sit underneath, so the adjacent area is visible before it becomes a finding." />
      </section>

      <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(300px,100%),1fr))]">
        <div className="bg-sheet p-4 md:p-6 min-w-0">
          <MediaSlot id="feature-dossier" />
        </div>
        <Feature n="03 — Dossier" title="The output looks like it came from an aviation professional" body="ConOps, the SORA assessment tables, the OSO matrix with evidence references, and an ERP skeleton. Versioned, rulebase-stamped, exported as DOCX.">
          <div className="mt-2 flex flex-col gap-sheet bg-hairline border-t border-hairline">
            {[["ConOps", "8 sections"], ["SORA assessment tables", "6 tables"], ["OSO matrix", `${N_OSO} rows`]].map(([a, b]) => (
              <div key={a} className="bg-sheet py-3 flex justify-between t-data-13 text-ink-mid"><span>{a}</span><span className="text-ink-low">{b}</span></div>
            ))}
          </div>
        </Feature>
        <div className="bg-sheet p-4 md:p-6 flex flex-col gap-4 min-w-0">
          <MediaSlot id="feature-counterfactual" />
          <div>
            <span className="t-micro text-ink-low">04 — Counterfactuals</span>
            <p className="mt-2 mb-0 t-body-sm text-ink-mid pretty">When the answer is no, the advisor says what would make it yes — and applies it.</p>
          </div>
        </div>
      </section>

      <section className="bg-sheet p-6 md:p-12">
        <div className="t-micro text-ink-low mb-6">Who runs it</div>
        <div className="grid gap-6 grid-cols-[repeat(auto-fit,minmax(240px,1fr))]">
          {PERSONAS.map(([slot, who, body]) => (
            <div key={slot} className="flex flex-col gap-3">
              <MediaSlot id={slot} />
              <p className="m-0 t-body-sm text-ink-mid pretty"><strong className="text-ink-hi font-semibold">{who}</strong> {body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-sheet p-6 md:p-12">
        <div className="flex items-baseline justify-between gap-6 flex-wrap mb-8">
          <h2 className="m-0 t-h1 text-ink-hi">Pricing</h2>
          <Link href="/pricing" className="inline-flex items-center min-h-11 px-1 t-micro text-ink-mid">See full comparison</Link>
        </div>
        <Tiers />
      </section>

      <section className="bg-sheet p-6 md:p-12">
        <h2 className="m-0 mb-8 t-h1 text-ink-hi">Questions worth asking</h2>
        <Faq />
      </section>

      <section className="bg-sheet px-6 py-10 md:px-12 flex flex-wrap items-center gap-8 justify-between">
        <div className="max-w-[34ch]">
          <div className="t-micro text-ink-low mb-2">Referenced frameworks</div>
          <p className="m-0 t-body-sm text-ink-mid pretty">Marks shown for reference only. No endorsement by EASA, Austro Control or the LBA is implied or claimed.</p>
        </div>
        <div className="flex-1 min-w-[min(280px,100%)] max-w-[520px]">
          <MediaSlot id="proof-logos" />
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
