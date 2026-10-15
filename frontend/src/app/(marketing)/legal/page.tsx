import type { Metadata } from "next";
import Link from "next/link";
import { DISCLAIMER } from "@/components/Brand";
import { MarketingFooter, MarketingHeader } from "@/components/marketing/Chrome";

export const metadata: Metadata = { title: "Legal" };

const CHANGELOG = [
  ["2026.2 · 01 Oct", "Rulebase moved to JARUS SORA 2.5. Austrian annex: AT-R-114 boundary updated. Adjacent-area assessment now flags populated cells within 500 m of the ground risk buffer."],
  ["2026.1 · 14 Jun", "M2 robustness criteria aligned to the revised AMC. Three OSOs reworded; none changed robustness level."],
  ["2025.4 · 02 Dec", "Containment requirements separated from the OSO set and surfaced as their own determination output."],
];

const SECTIONS = [["disclaimer", "Disclaimer"], ["terms", "Terms of service"], ["privacy", "Privacy"], ["changelog", "Rulebase changelog"]];

export default function Legal() {
  return (
    <div className="flex flex-col gap-sheet">
      <MarketingHeader variant="plain" />
      <section className="bg-sheet p-6 md:p-12 grid gap-12 md:grid-cols-[260px_minmax(0,1fr)]">
        <nav aria-label="Legal" className="flex flex-col gap-sheet self-start md:sticky md:top-6">
          {SECTIONS.map(([id, label], i) => (
            <Link key={id} href={`#${id}`} className={i === 0 ? "no-underline p-3 bg-sheet-raised text-ink-hi t-micro min-h-11 flex items-center shadow-[inset_2px_0_0_var(--accent)]" : "no-underline p-3 text-ink-mid hover:text-ink-hi t-micro min-h-11 flex items-center"}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="min-w-0 flex flex-col gap-12 max-w-[72ch]">
          <div id="disclaimer">
            <h1 className="m-0 mb-4 t-h1 text-ink-hi">Disclaimer</h1>
            <div className="p-5 bg-accent text-accent-ink rounded-sm"><p className="m-0 text-[18px] font-semibold leading-[1.5] pretty">{DISCLAIMER}</p></div>
            <p className="mt-4 mb-0 t-body leading-[1.6] text-ink-mid pretty">The determinations this service produces are decision support. They are computed from the facts you confirm, against a stated version of the rulebase, and they are shown with the reasoning that produced them so that you can check it. They are not an authorisation, a declaration, or a legal opinion, and they do not transfer any part of the operator&apos;s responsibility under Regulation (EU) 2019/947.</p>
            <p className="mt-4 mb-0 t-body leading-[1.6] text-ink-mid pretty">You remain the accountable party for the accuracy of the facts you enter, for the evidence you attach to each OSO, and for the operation itself.</p>
          </div>
          <div id="terms">
            <h2 className="m-0 mb-4 t-h2 text-ink-hi">Terms of service</h2>
            <p className="m-0 t-body leading-[1.6] text-ink-mid pretty">The service is provided to operators and their consultants for preparing SORA assessments. Accounts are per organisation; seats are per named person. Determinations, traces and generated dossiers belong to the organisation that produced them and can be exported at any time. Fees are billed monthly in advance or per dossier; cancellation takes effect at the end of the billing period.</p>
          </div>
          <div id="privacy">
            <h2 className="m-0 mb-4 t-h2 text-ink-hi">Privacy</h2>
            <p className="m-0 t-body leading-[1.6] text-ink-mid pretty">Mission data, evidence files and dossiers are stored in the EU region your organisation selects — Frankfurt or Dublin — and are not used to train models. Prose you enter in the intake panel is processed only to extract facts for your confirmation. The free category checker stores nothing.</p>
          </div>
          <div id="changelog">
            <h2 className="m-0 mb-4 t-h2 text-ink-hi">Rulebase changelog</h2>
            <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
              {CHANGELOG.map(([v, b]) => (
                <div key={v} className="bg-sheet-well p-4 flex gap-4 flex-wrap">
                  <span className="text-[13px] font-semibold leading-[1.4] text-ink-hi min-w-[120px] tnum">{v}</span>
                  <span className="flex-1 min-w-[220px] t-body-sm text-ink-mid pretty">{b}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <MarketingFooter compact />
    </div>
  );
}
