import type { Metadata } from "next";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/Chrome";
import { Tiers } from "@/components/marketing/Tiers";

export const metadata: Metadata = { title: "Pricing" };

const INCLUDED = [
  ["Full derivation trace.", "Every determination is traceable to the clause that produced it, on every plan, including the free checker's estimate."],
  ["Rulebase stamping.", "Results are reproducible. The version and date travel with the determination and into the export."],
  ["EU data residency.", "Mission data, evidence and dossiers stay in Frankfurt or Dublin, your choice."],
  ["No lock-in.", "Dossiers export as DOCX. Cancel and keep everything you generated."],
];

export default function Pricing() {
  return (
    <div className="flex flex-col gap-sheet">
      <MarketingHeader variant="cta" />
      <section className="bg-sheet px-4 pt-12 pb-8 md:px-12 md:pt-16">
        <h1 className="m-0 mb-5 t-display text-ink-hi pretty">Pay for the assessment, not the appointment.</h1>
        <p className="m-0 max-w-[60ch] t-body-lg text-ink-mid pretty">The category checker is free and needs no account. Everything else is priced against what a consultant would charge for one dossier.</p>
      </section>
      <section className="bg-sheet px-4 pb-12 md:px-12">
        <Tiers tall />
      </section>
      <section className="bg-sheet p-6 md:p-12">
        <h2 className="m-0 mb-6 t-h2 text-ink-hi">What is included at every tier</h2>
        <div className="grid gap-6 grid-cols-[repeat(auto-fit,minmax(240px,1fr))]">
          {INCLUDED.map(([h, b]) => (
            <p key={h} className="m-0 t-body-sm leading-[1.55] text-ink-mid pretty"><strong className="text-ink-hi font-semibold">{h}</strong> {b}</p>
          ))}
        </div>
      </section>
      <MarketingFooter compact />
    </div>
  );
}
