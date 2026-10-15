import type { Metadata } from "next";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/Chrome";
import { Checker } from "./Checker";

export const metadata: Metadata = { title: "Free category checker" };

export default function CheckerPage() {
  return (
    <div className="flex flex-col gap-sheet">
      <MarketingHeader variant="stamp" />
      <section className="bg-sheet px-4 pt-10 pb-6 md:px-12 md:pt-12">
        <span className="t-micro text-ink-low">Free category checker</span>
        <h1 className="mt-3 mb-3 t-h1 text-ink-hi max-w-[24ch] pretty">Three questions. Category, and an estimated SAIL.</h1>
        <p className="m-0 max-w-[62ch] t-body leading-[1.6] text-ink-mid pretty">No account. Nothing is stored. The estimate is indicative — a full determination needs the flight geography and your claimed mitigations.</p>
      </section>
      <Checker />
      <MarketingFooter compact />
    </div>
  );
}
