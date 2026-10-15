"use client";

import { usePrefs } from "@/lib/prefs";

/**
 * The honesty labels for everything the clingo engine has not computed yet.
 *
 * Through phases 1–6 the checker and the verdict screen compute the chain in TypeScript,
 * in the browser. That is useful for building the UI and useless as compliance evidence,
 * so it is labelled wherever it appears. Both labels and the TypeScript engine are
 * removed together when the backend takes over: the verdict at Phase 3, the checker at
 * Phase 7.
 */

export const PRELIMINARY_TITLE = "Preliminary estimate";
export const PRELIMINARY_BODY =
  "Computed in your browser from a seed rulebase, not by the rules engine. It is not a determination, it carries no trace you can submit, and no table behind it has been verified against the official SORA 2.5 text.";

/** A sail-3 banded block. `inline` drops the heading for tight columns. */
export function PreliminaryNotice({ inline = false }: { inline?: boolean }) {
  return (
    <div
      role="note"
      className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm flex flex-col gap-1.5"
    >
      {!inline && <span className="t-micro-10 text-sail-3">{PRELIMINARY_TITLE}</span>}
      <p className="m-0 t-cap text-ink-mid pretty">{PRELIMINARY_BODY}</p>
    </div>
  );
}

/** A one-line marker to sit beside a figure the engine did not produce. */
export function PreliminaryTag() {
  return (
    <span className="t-micro-10 text-sail-3" title={PRELIMINARY_BODY}>
      Preliminary · not a determination
    </span>
  );
}

/**
 * Says plainly that what is on screen is the fixture demo workspace.
 *
 * Renders nothing when the demo is off, so a real account never sees it.
 */
export function DemoNotice() {
  const { demo, setDemo } = usePrefs();
  if (!demo) return null;
  return (
    <div
      role="note"
      className="bg-sheet px-4 md:px-6 py-3 flex items-center gap-3 flex-wrap border-l-[3px] border-sail-3"
    >
      <span className="t-micro-10 text-sail-3 flex-none">Demo workspace</span>
      <span className="flex-1 t-cap text-ink-mid pretty">
        Six example operations for a fictional operator in Graz. Every figure is computed
        in your browser from a seed rulebase, not by the rules engine.
      </span>
      <button
        type="button"
        onClick={() => setDemo(false)}
        className="min-h-11 px-3 bg-transparent border border-hairline-strong rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
      >
        Hide the demo
      </button>
    </div>
  );
}
