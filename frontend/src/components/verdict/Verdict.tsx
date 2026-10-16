"use client";

/**
 * The verdict screen. The product's centrepiece.
 *
 * Everything on it comes from one stored determination: the SAIL badge, the chain, the
 * derivation tree, the gap analysis and the counterfactual advisor all read the same
 * record, so nothing on the screen can disagree with anything else on it.
 *
 * Applying a counterfactual writes to the **draft** and does not re-run. The operator
 * sees the change land, then runs the determination themselves — a suggestion that
 * silently became a determination would blur the line the whole product defends.
 */

import Link from "next/link";
import { useMemo, useState } from "react";
import { Disclaimer, RulebaseStamp } from "@/components/Brand";
import { ComputationProgress, useStagedRun } from "@/components/ComputationProgress";
import { SailBadge, SailPlaceholder, SailScale, useSteppedLevel } from "@/components/SailBadge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useToast } from "@/components/Toast";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import { RiskChainReadout } from "@/components/verdict/Chain";
import { GapAnalysis } from "@/components/verdict/GapAnalysis";
import { OsoDrawer } from "@/components/verdict/OsoDrawer";
import { TraceTree, traceMarkdown } from "@/components/verdict/TraceTree";
import { ApiError } from "@/lib/api";
import { sailLevel, type Counterfactual, type Determination } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import {
  useApplyCounterfactual,
  useCounterfactuals,
  useDetermination,
  useOperation,
  useOsos,
  useRunDetermination,
} from "@/lib/hooks";
import { downloadJson, downloadText } from "@/lib/upload";

export function Verdict({ operationId }: { operationId: string }) {
  const { push } = useToast();
  const { data: operation, isLoading: loadingOp } = useOperation(operationId);
  const {
    data: determination,
    isLoading: loadingDetermination,
    error: determinationError,
  } = useDetermination(operationId);

  if (loadingOp || loadingDetermination) {
    return <main className="flex-1 bg-sheet" aria-busy />;
  }
  if (!operation) {
    return <NotFoundPanel />;
  }
  if (!determination) {
    const notRun = determinationError instanceof ApiError && determinationError.code === "no_determination";
    return notRun ? (
      <DraftRun operationId={operationId} name={operation.name} />
    ) : (
      <ErrorPanel message={determinationError instanceof Error ? determinationError.message : "The determination could not be loaded."} />
    );
  }
  return <VerdictView operationId={operationId} name={operation.name} determination={determination} />;
}

function NotFoundPanel() {
  return (
    <main className="flex-1 bg-sheet p-6 flex flex-col gap-4 items-start">
      <h2 className="m-0 t-h2 text-ink-hi">That operation is not available</h2>
      <p className="m-0 t-body-sm text-ink-mid max-w-[52ch] pretty">
        It may have been deleted, or it belongs to another organisation.
      </p>
      <ButtonLink href="/app/">Go to operations</ButtonLink>
    </main>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <main className="flex-1 bg-sheet p-6 flex flex-col gap-4 items-start">
      <span className="t-micro text-sail-6">The determination could not be loaded</span>
      <p className="m-0 t-body-sm text-ink-mid max-w-[52ch] pretty">{message}</p>
      <ButtonLink href="/app/">Go to operations</ButtonLink>
    </main>
  );
}

function DraftRun({ operationId, name }: { operationId: string; name: string }) {
  const { push } = useToast();
  const [go, setGo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useRunDetermination(operationId);
  const staged = useStagedRun(go, () => undefined);

  return (
    <main className="flex-1 grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))] content-start">
      <div className="bg-sheet p-6 flex flex-col gap-4 items-start">
        <span className="t-micro text-ink-low">Not yet run</span>
        <h2 className="m-0 t-h2 text-ink-hi pretty">{name}</h2>
        <p className="m-0 t-body-sm text-ink-mid max-w-[52ch] pretty">
          No determination has been recorded for this operation. Running it computes the
          chain from the facts you have confirmed, and stores the result with the rulebase
          version pinned.
        </p>
        <div className="flex gap-2.5 flex-wrap">
          <Button
            disabled={go}
            onClick={() => {
              setError(null);
              setGo(true);
              run.mutate(false, {
                onError: (e) => {
                  setGo(false);
                  setError(
                    e instanceof ApiError
                      ? (e.problem.unconfirmed_fields?.length
                          ? `Confirm or reject these first: ${e.problem.unconfirmed_fields.join(", ")}.`
                          : (e.problem.detail ?? e.problem.title))
                      : e instanceof Error
                        ? e.message
                        : "The determination did not run.",
                  );
                },
                onSuccess: () => push({ tone: "ok", text: "Determination computed" }),
              });
            }}
          >
            {go ? "Running" : "Run determination"}
          </Button>
          <ButtonLink href={`/app/new/?id=${encodeURIComponent(operationId)}`} variant="secondary">
            Open the wizard
          </ButtonLink>
        </div>
        {error && (
          <div role="alert" className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
            <span className="t-micro-10 text-sail-3">Not run</span>
            <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">{error}</p>
          </div>
        )}
      </div>
      <div className="bg-sheet-well p-6 flex flex-col gap-4">
        <span className="t-micro text-ink-low">Computation</span>
        {go ? (
          <ComputationProgress {...staged} />
        ) : (
          <p className="m-0 t-body-sm text-ink-low">Waiting for you to start the run.</p>
        )}
      </div>
    </main>
  );
}

function VerdictView({
  operationId,
  name,
  determination,
}: {
  operationId: string;
  name: string;
  determination: Determination;
}) {
  const { push } = useToast();
  const [runKey, setRunKey] = useState(0);
  const [openOso, setOpenOso] = useState<string | null>(null);

  const { data: osos = [] } = useOsos(operationId);
  const {
    data: counterfactuals,
    isLoading: loadingCfs,
    error: cfError,
  } = useCounterfactuals(operationId);
  const apply = useApplyCounterfactual(operationId);
  const rerun = useRunDetermination(operationId);

  const level = sailLevel(determination.sail);
  const certified = determination.sail === "certified_category";
  const shown = useSteppedLevel(level ?? 1, 180, 1);

  // Nothing has been re-run in this view yet, so no node is marked changed. The accent
  // band appears after an apply-and-rerun, keyed on what actually moved.
  const [changed, setChanged] = useState<Set<string>>(new Set());

  const current = osos.find((o) => o.oso_id === openOso) ?? null;
  const category = certified ? "Certified category" : "Specific category";

  const exportTrace = () => {
    downloadJson(`${operationId}-trace.json`, determination);
    push({ tone: "ok", text: "Trace exported with the rulebase stamp" });
  };

  const copyTrace = () => {
    downloadText(`${operationId}-trace.md`, traceMarkdown(determination));
    push({ tone: "ok", text: "Trace saved as markdown" });
  };

  const applyAndRerun = (suggestion: Counterfactual) => {
    const before = determination;
    apply.mutate(suggestion.id, {
      onSuccess: () => {
        rerun.mutate(false, {
          onSuccess: (after) => {
            const previous = new Map(before.trace.map((n) => [n.id, n.conclusion]));
            setChanged(
              new Set(
                after.trace.filter((n) => previous.get(n.id) !== n.conclusion).map((n) => n.id),
              ),
            );
            setRunKey((k) => k + 1);
            push({
              tone: "ok",
              text: `Re-run: SAIL ${before.sail} → ${after.sail}`,
            });
          },
          onError: (e) =>
            push({
              tone: "warn",
              text:
                e instanceof ApiError
                  ? (e.problem.detail ?? e.problem.title)
                  : "Applied to the draft, but the re-run did not complete.",
            }),
        });
      },
      onError: (e) =>
        push({ tone: "fail", text: e instanceof Error ? e.message : "Could not apply that change" }),
    });
  };

  return (
    <>
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        {!determination.is_verified && <UnverifiedBanner warnings={determination.warnings} />}

        <div className="bg-sheet p-4 md:p-6 flex gap-8 items-start flex-wrap">
          <div className="flex gap-5 items-start">
            {level ? (
              <SailBadge level={shown} size="lg" />
            ) : (
              <SailPlaceholder size="lg" label="CERTIFIED" />
            )}
            <div className="flex flex-col gap-2 max-w-[30ch]">
              <span className="t-micro text-ink-low">Determination</span>
              <h2 className="m-0 t-h2 text-ink-hi pretty">{name}</h2>
              <p className="m-0 t-body-sm text-ink-mid">
                {category} · computed{" "}
                {new Date(determination.computed_at).toLocaleString("en-GB", {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
              <RulebaseStamp />
            </div>
          </div>
          <div className="flex-1 min-w-[min(300px,100%)] flex flex-col gap-2.5">
            <span className="t-micro text-ink-low">Risk chain</span>
            <RiskChainReadout
              key={`${determination.id}-${runKey}`}
              determination={determination}
              countUp={runKey === 0}
              recomputing={rerun.isPending || apply.isPending}
            />
            <SailScale />
            {certified && (
              <p className="m-0 t-body-sm text-ink-mid pretty">
                The intrinsic ground risk for this operation is outside SORA, so the
                specific category does not apply and it needs the certified category.
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-sheet items-stretch">
          <div className="bg-sheet p-4 md:p-6 flex-[1_1_560px] min-w-0">
            <TraceTree
              determination={determination}
              changed={changed}
              runKey={runKey}
              onReplay={() => setRunKey((k) => k + 1)}
            />
          </div>

          <div className="bg-sheet p-4 md:p-6 flex flex-col gap-6 flex-[0_1_420px] min-w-[min(320px,100%)]">
            <div>
              <h3 className="m-0 t-h3 text-ink-hi">Counterfactual advisor</h3>
              <p className="mt-1 mb-4 t-body-sm text-ink-mid pretty">
                What would change the determination, and what it costs you. Every
                suggestion was re-run by the engine before it was offered.
              </p>

              {loadingCfs && <p className="m-0 t-body-sm text-ink-low">Searching…</p>}

              {/* The advisor is a paid feature. The refusal replaces the list rather
                  than sitting above it, because an empty list next to an upgrade panel
                  reads as a failure. */}
              {isPlanLimit(cfError) && <PlanLimit error={cfError} compact />}

              {!loadingCfs && !cfError && counterfactuals && counterfactuals.suggestions.length === 0 && (
                <p className="m-0 p-4 bg-sheet-well t-body-sm text-ink-mid pretty">
                  No change within the advisor&apos;s reach lowers this SAIL. It searches
                  single changes first, then pairs; something larger — a different
                  aircraft, a different site — may still help.
                </p>
              )}

              {!cfError && counterfactuals && counterfactuals.suggestions.length > 0 && (
                <div className="flex flex-col gap-sheet bg-hairline">
                  {counterfactuals.suggestions.map((s) => (
                    <CounterfactualCard
                      key={s.id}
                      suggestion={s}
                      busy={apply.isPending || rerun.isPending}
                      onApply={() => applyAndRerun(s)}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 pt-5 border-t border-hairline">
              <RulebaseStamp authoritative />
              <Disclaimer />
              <div className="flex gap-2.5 flex-wrap">
                <ButtonLink
                  href={`/app/dossiers/?op=${encodeURIComponent(operationId)}`}
                  className="flex-1 min-w-[140px]"
                >
                  Build dossier
                </ButtonLink>
                <Button variant="secondary" className="flex-1 min-w-[120px]" onClick={exportTrace}>
                  Export trace
                </Button>
                <Button variant="ghost" onClick={copyTrace}>
                  Save as markdown
                </Button>
              </div>
            </div>
          </div>
        </div>

        {!certified && osos.length > 0 && (
          <div className="bg-sheet p-4 md:p-6">
            <GapAnalysis osos={osos} onOpen={setOpenOso} />
          </div>
        )}

        {!certified && (
          <div className="bg-sheet px-4 md:px-6 py-4 flex gap-3 items-start">
            <span
              className={cn(
                "t-micro flex-none pt-0.5",
                determination.containment.level ? "text-ink-low" : "text-sail-3",
              )}
            >
              Containment
            </span>
            <p className="m-0 t-cap text-ink-mid pretty">
              {determination.containment.level ? (
                <>
                  <span className="t-data-sm text-ink-hi">
                    {determination.containment.level} robustness
                  </span>{" "}
                  — from Step #8&apos;s tables, by the aircraft&apos;s characteristic
                  dimension, the adjacent ground area and this SAIL.
                </>
              ) : (
                // Two different answers wear this shape: the tables said "out of scope",
                // or an input Step #8 needs is missing. The note says which.
                determination.containment.note ||
                "Containment has not been established for this operation."
              )}{" "}
              <Link href="/legal#changelog">See the rulebase changelog</Link>.
            </p>
          </div>
        )}
      </main>

      <OsoDrawer operationId={operationId} oso={current} onClose={() => setOpenOso(null)} />
    </>
  );
}

/**
 * Says how many tables are open, not that everything is.
 *
 * Part of the rulebase is now checked against the published SORA 2.5 text and part is
 * not, so a blanket "none of this has been verified" would be false — and false in the
 * direction that teaches an operator to ignore the banner. Each warning names one table
 * and its own open question, so the count is the headline and the notes are the detail.
 */
function UnverifiedBanner({ warnings }: { warnings: string[] }) {
  const [open, setOpen] = useState(false);
  const n = warnings.length;
  return (
    <div role="status" className="bg-sheet px-4 md:px-6 py-3 border-l-[3px] border-sail-3">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="t-micro-10 text-sail-3 flex-none">Unverified rulebase</span>
        <span className="flex-1 t-cap text-ink-mid pretty">
          {n === 1 ? "One of the regulatory tables" : `${n} of the regulatory tables`} behind
          this determination {n === 1 ? "is" : "are"} still transcribed from a seed rather
          than checked against the published JARUS SORA 2.5 text. It must not be submitted
          to an authority.
        </span>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="min-h-11 px-3 bg-transparent border border-hairline-strong rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
        >
          {open ? "Hide" : n === 1 ? "Which one" : "Which ones"}
        </button>
      </div>
      {open && (
        <ul className="m-0 mt-3 p-0 pl-4 list-disc flex flex-col gap-1.5">
          {warnings.map((w) => (
            <li key={w} className="t-cap text-ink-mid pretty">
              {w}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CounterfactualCard({
  suggestion,
  busy,
  onApply,
}: {
  suggestion: Counterfactual;
  busy: boolean;
  onApply: () => void;
}) {
  const level = sailLevel(suggestion.resulting_sail);
  const osoDelta = suggestion.oso_delta ?? [];
  return (
    <div className={cn("bg-sheet-well p-4 flex flex-col gap-3", busy && "pointer-events-none opacity-70")}>
      <div className="flex items-start justify-between gap-3">
        <span className="t-data text-ink-hi pretty">{suggestion.title}</span>
        {level && <SailBadge level={level} size="sm" />}
      </div>

      <span className="t-data-sm leading-none tracking-[.06em] text-ink-hi">
        <span aria-hidden className="text-accent">
          →{" "}
        </span>
        {suggestion.chain_effect}
      </span>

      {suggestion.changes.length > 1 && (
        <span className="t-cap text-ink-low pretty">
          {suggestion.changes.length} changes together — neither reaches this SAIL alone.
        </span>
      )}

      <span className="t-cap text-ink-low pretty">Evidence: {suggestion.evidence_required}</span>

      {osoDelta.length > 0 && (
        <span className="t-cap text-ink-low pretty">
          OSOs affected: {osoDelta.slice(0, 3).join("; ")}
          {osoDelta.length > 3 ? ` and ${osoDelta.length - 3} more` : ""}
        </span>
      )}

      <Button variant="secondary" className="tracking-[.08em] px-3.5" onClick={onApply}>
        {busy ? "Re-running" : "Apply and re-run"}
      </Button>
    </div>
  );
}
