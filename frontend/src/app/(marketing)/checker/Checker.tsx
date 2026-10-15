"use client";

/**
 * The free category checker.
 *
 * Three questions, answered by the **same clingo engine** the product runs — not a
 * client-side approximation of it. That is the point: the first thing a sceptical
 * compliance officer tries should be the real thing, and the assumptions it made are
 * listed rather than hidden.
 */

import { useEffect, useState } from "react";
import { Disclaimer, RulebaseStamp } from "@/components/Brand";
import { MediaSlot } from "@/components/MediaSlot";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { ButtonLink } from "@/components/ui/Button";
import { Segmented } from "@/components/ui/Field";
import { sailLevel, type CategoryCheck, type CategoryCheckIn } from "@/lib/api-client";
import { useCategoryCheck } from "@/lib/hooks";
import { ApiError } from "@/lib/api";

type MassBand = CategoryCheckIn["mass_band"];
type Ground = CategoryCheckIn["ground_environment"];
type Op = CategoryCheckIn["operation_type"];

const MASS: { value: MassBand; label: string }[] = [
  { value: "sub250", label: "Under 250 g" },
  { value: "c_marked", label: "250 g – 4 kg" },
  { value: "4to25", label: "4 – 25 kg" },
  { value: "over25", label: "Over 25 kg" },
];

const GROUND: { value: Ground; label: string }[] = [
  { value: "controlled_ground_area", label: "Controlled" },
  { value: "sparsely_populated", label: "Sparse" },
  { value: "populated", label: "Populated" },
  { value: "assembly_of_people", label: "Assembly" },
];

const OPS: { value: Op; label: string }[] = [
  { value: "vlos", label: "VLOS" },
  { value: "evlos", label: "EVLOS" },
  { value: "bvlos", label: "BVLOS" },
];

export function Checker() {
  const [answers, setAnswers] = useState<CategoryCheckIn>({
    mass_band: "4to25",
    ground_environment: "sparsely_populated",
    operation_type: "bvlos",
  });
  const check = useCategoryCheck();
  const [result, setResult] = useState<CategoryCheck | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Re-run whenever an answer changes: three questions, so the result should feel like
  // an instrument reading rather than a form submission.
  useEffect(() => {
    let cancelled = false;
    setError(null);
    check.mutate(answers, {
      onSuccess: (r) => !cancelled && setResult(r),
      onError: (e) => {
        if (cancelled) return;
        setError(
          e instanceof ApiError
            ? (e.problem.detail ?? e.problem.title)
            : "The checker could not reach the engine. It runs on the server, so this needs a connection.",
        );
      },
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers.mass_band, answers.ground_environment, answers.operation_type]);

  const level = result ? sailLevel(result.sail) : null;
  const title = result ? titleFor(result) : "Working…";
  const mail = result
    ? `mailto:?subject=${encodeURIComponent("SORA category estimate")}&body=${encodeURIComponent(
        [
          title,
          "",
          result.reason,
          "",
          "Assumptions:",
          ...result.assumptions.map((a) => `- ${a}`),
          "",
          `Rulebase ${result.rulebase_version}.`,
          result.disclaimer,
        ].join("\n"),
      )}`
    : "#";

  return (
    <section className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(340px,100%),1fr))]">
      <div className="bg-sheet px-4 py-8 md:p-12 flex flex-col gap-8">
        <div className="flex flex-col gap-2.5">
          <span className="t-micro text-ink-low">01 — How heavy is it</span>
          <Segmented
            label="Mass band"
            size="lg"
            className="rounded-none"
            value={answers.mass_band}
            onChange={(v) => setAnswers((a) => ({ ...a, mass_band: v }))}
            options={MASS}
          />
        </div>
        <div className="flex flex-col gap-2.5">
          <span className="t-micro text-ink-low">02 — What is underneath</span>
          <Segmented
            label="Ground environment"
            size="lg"
            className="rounded-none"
            value={answers.ground_environment}
            onChange={(v) => setAnswers((a) => ({ ...a, ground_environment: v }))}
            options={GROUND}
          />
        </div>
        <div className="flex flex-col gap-2.5">
          <span className="t-micro text-ink-low">03 — How you will fly it</span>
          <Segmented
            label="Operation type"
            size="lg"
            className="rounded-none"
            value={answers.operation_type}
            onChange={(v) => setAnswers((a) => ({ ...a, operation_type: v }))}
            options={OPS}
          />
        </div>
      </div>

      <div className="bg-sheet-raised px-4 py-8 md:p-12 flex flex-col gap-6" aria-live="polite">
        <div className="flex items-baseline justify-between gap-4 flex-wrap">
          <span className="t-micro text-ink-low">Result</span>
          {result && !result.is_verified && (
            <span className="t-micro-10 text-sail-3">Unverified rulebase</span>
          )}
        </div>

        {error && (
          <div role="alert" className="p-4 bg-sheet-well border-l-[3px] border-sail-6 rounded-sm">
            <span className="t-micro-10 text-sail-6">The engine did not answer</span>
            <p className="m-0 mt-1.5 t-body-sm text-ink-mid pretty">{error}</p>
          </div>
        )}

        {result && !error && (
          <>
            <div
              key={`${result.category}-${result.sail}`}
              className="flex items-center gap-6 flex-wrap animate-[node-settle_240ms_var(--ease-ui)_both]"
            >
              {level ? (
                <SailBadge level={level} size="lg" />
              ) : (
                <SailPlaceholder
                  size="lg"
                  label={result.category === "open" ? "NO SAIL" : "OUT OF SORA"}
                />
              )}
              <div className="flex flex-col gap-2 min-w-[200px] flex-1">
                <span className="t-h2 text-ink-hi">{title}</span>
                <p className="m-0 t-body-sm text-ink-mid pretty">{result.reason}</p>
              </div>
            </div>

            {result.category !== "open" && (
              <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
                {[
                  ["Intrinsic ground risk (iGRC)", result.igrc ?? "—"],
                  ["Initial air risk (ARC)", result.initial_arc?.toUpperCase() ?? "—"],
                  ["OSOs at this SAIL", result.osos_required ?? "—"],
                ].map(([k, v]) => (
                  <div
                    key={String(k)}
                    className="bg-sheet-well px-4 py-3 flex justify-between gap-3 t-data-13 text-ink-hi min-h-11 items-center"
                  >
                    <span className="text-ink-mid">{k}</span>
                    <span className="tnum">{v}</span>
                  </div>
                ))}
              </div>
            )}

            {result.hint && (
              <p className="m-0 t-body-sm leading-[1.55] text-ink-mid pretty">
                Mitigations can move this. {result.hint}
              </p>
            )}

            <div className="flex flex-col gap-2">
              <span className="t-micro text-ink-low">What this assumed</span>
              <ul className="m-0 p-0 pl-4 list-disc flex flex-col gap-1">
                {result.assumptions.map((a) => (
                  <li key={a} className="t-cap text-ink-mid pretty">
                    {a}
                  </li>
                ))}
              </ul>
              <p className="m-0 t-cap text-ink-low pretty">
                A real assessment uses your aircraft, your airspace and your geography.
                Three questions cannot replace it, and this does not pretend to.
              </p>
            </div>

            {!result.is_verified && (
              <div className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
                <span className="t-micro-10 text-sail-3">Unverified rulebase</span>
                <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">
                  The regulatory tables behind this estimate have not yet been checked
                  against the published JARUS SORA 2.5 text.
                </p>
              </div>
            )}

            <RulebaseStamp />

            <div className="flex gap-2.5 flex-wrap">
              <ButtonLink href="/signin/" shape="pill" size="lg">
                Run the full assessment
              </ButtonLink>
              <a
                href={mail}
                className="no-underline inline-flex items-center justify-center min-h-12 px-6 border border-hairline-strong rounded-pill t-micro text-ink-hi hover:bg-sheet tr-ui"
              >
                Email me this estimate
              </a>
            </div>
          </>
        )}

        {!result && !error && (
          <div className="flex flex-col gap-3" aria-busy>
            <div className="h-[132px] w-[132px] bg-sheet-well" />
            <div className="h-6 w-2/3 bg-sheet-well" style={{ opacity: 0.7 }} />
            <div className="h-4 w-1/2 bg-sheet-well" style={{ opacity: 0.45 }} />
          </div>
        )}

        <Disclaimer className="pt-5 border-t border-hairline" />
      </div>

      <div className="sr-only">
        <MediaSlot id="og-default" />
      </div>
    </section>
  );
}

function titleFor(result: CategoryCheck): string {
  if (result.category === "open") return `Open category · ${result.subcategory}`;
  if (result.category === "certified") return "Certified category";
  return result.sail === "certified_category"
    ? "Certified category"
    : `Specific category · SAIL ${result.sail}`;
}
