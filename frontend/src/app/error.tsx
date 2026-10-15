"use client";

import { useEffect, useState } from "react";
import { RulebaseStamp } from "@/components/Brand";
import { Button } from "@/components/ui/Button";

/**
 * 500. Copy from the design prototype verbatim.
 *
 * The reference identifies the exact run and rulebase, because "it broke" is not
 * actionable and a compliance officer will ask which run. It states plainly that no
 * determination was written: a half-written determination would be worse than none.
 */
export default function ErrorScreen({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Nothing is reported anywhere yet; the console is the only record in this build.
    console.error(error);
  }, [error]);

  const ref = `ref ${error.digest ? error.digest.slice(0, 8).toUpperCase() : "ENG-LOCAL"}`;
  const when = new Date().toISOString().replace("T", " ").slice(0, 16) + " UTC";
  const reference = `${ref} · ${when}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${reference} · ${error.message}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <main className="min-h-dvh bg-sheet-raised px-6 py-12 md:p-12 flex flex-col justify-center gap-5 border-t-[3px] border-sail-6">
      <span className="t-figure text-ink-hi tnum" aria-hidden>
        500
      </span>
      <h1 className="m-0 t-h2 text-ink-hi max-w-[22ch] pretty">The engine did not answer</h1>
      <p className="m-0 max-w-[44ch] t-body text-ink-mid pretty">
        No determination was written. Nothing you entered was lost. If this repeats, send
        the reference below — it identifies the exact run and rulebase.
      </p>
      <div className="self-start px-3.5 py-3 bg-sheet-well rounded-sm flex flex-col gap-1.5">
        <span className="t-data-sm text-ink-mid tnum">{reference}</span>
        <RulebaseStamp />
      </div>
      <div className="flex gap-2.5 flex-wrap">
        <Button onClick={reset}>Retry</Button>
        <Button variant="secondary" onClick={copy}>
          {copied ? "Reference copied" : "Copy reference"}
        </Button>
      </div>
    </main>
  );
}
