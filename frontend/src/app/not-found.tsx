import Link from "next/link";
import { MarketingFooter } from "@/components/marketing/Chrome";
import { ButtonLink } from "@/components/ui/Button";

export const metadata = { title: "404 · That page is not on the chart" };

/**
 * 404. Copy from the design prototype verbatim.
 *
 * Three routes in the app rail — /app/new, /app/dossiers, /app/settings — are not built
 * yet, so this is what an operator currently reaches from them. It says what is and is
 * not affected, because the first question a compliance officer has is whether their
 * determinations are still there.
 */
export default function NotFound() {
  return (
    <div className="min-h-dvh flex flex-col gap-sheet bg-ground">
      <main className="flex-1 bg-sheet px-6 py-12 md:p-12 flex flex-col justify-center gap-5">
        <span className="t-figure text-ink-hi tnum" aria-hidden>
          404
        </span>
        <h1 className="m-0 t-h2 text-ink-hi max-w-[20ch] pretty">That page is not on the chart</h1>
        <p className="m-0 max-w-[44ch] t-body text-ink-mid pretty">
          The link may be from an older rulebase, or the operation it pointed at was
          deleted. Your determinations are unaffected.
        </p>
        <div className="flex gap-2.5 flex-wrap">
          <ButtonLink href="/app/">Go to operations</ButtonLink>
          <ButtonLink href="/" variant="secondary">
            Back to the start
          </ButtonLink>
        </div>
        <p className="m-0 t-cap text-ink-low">
          Building the intake wizard, the dossier builder and settings is still in
          progress. <Link href="/checker/">The category checker</Link> works today and
          needs no account.
        </p>
      </main>
      <MarketingFooter />
    </div>
  );
}
