"use client";

/**
 * Every data surface's loading, empty, error and offline state, on one page.
 *
 * Not decoration: these are the states a real operator hits on a free-tier deployment
 * with a sleeping backend, and having them in one place is how they stay consistent
 * rather than being invented separately on each screen.
 */

import { useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { ComputationProgress, useStagedRun } from "@/components/ComputationProgress";
import { EmptyState } from "@/components/app/EmptyState";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useHealth } from "@/lib/hooks";

export default function States() {
  const [run, setRun] = useState(0);
  const [fail, setFail] = useState(false);
  const staged = useStagedRun(run > 0, () => undefined, fail ? 3 : undefined);
  const { data: health, isError } = useHealth();

  return (
    <>
      <PageHeader title="System states" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <div className="bg-sheet px-4 md:px-6 py-5">
          <p className="m-0 max-w-[68ch] t-body-sm text-ink-mid pretty">
            The states every data surface can be in. They live here so that the empty
            dashboard, the sleeping backend and the failed run look the same wherever
            they appear.
          </p>
        </div>

        <Panel title="Computation in progress" note="No spinner: named stages with elapsed time, because a compliance officer wants to see which stage is slow.">
          <div className="flex gap-2.5 flex-wrap mb-4">
            <Button
              onClick={() => {
                setFail(false);
                setRun((r) => r + 1);
              }}
            >
              Run
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setFail(true);
                setRun((r) => r + 1);
              }}
            >
              Run and fail at the airspace stage
            </Button>
          </div>
          {run > 0 ? (
            <div key={run} className="p-4 bg-sheet-well rounded-sm max-w-[520px]">
              <ComputationProgress {...staged} />
            </div>
          ) : (
            <p className="m-0 t-body-sm text-ink-low">Not started.</p>
          )}
        </Panel>

        <Panel title="Empty — operations" note="Body copy says what the next concrete step produces, never 'get started'.">
          <EmptyState
            slot="empty-operations"
            title="No operations yet"
            body="Start with the aircraft and the area. The engine needs six confirmed facts to reach a SAIL; the wizard collects them in about four minutes."
            action={<ButtonLink href="/app/new/">New operation</ButtonLink>}
          />
        </Panel>

        <Panel title="Empty — dossiers">
          <EmptyState
            slot="empty-dossiers"
            title="No dossiers yet"
            body="A dossier is a rendering of a determination, so there is one to build as soon as an operation has been run."
            action={<ButtonLink href="/app/">Go to operations</ButtonLink>}
          />
        </Panel>

        <Panel title="Empty — fleet">
          <EmptyState
            slot="empty-fleet"
            title="No aircraft yet"
            body="Add the aircraft you fly. The engine needs its characteristic dimension, mass and maximum speed to choose the iGRC column."
            action={<ButtonLink href="/app/fleet/">Add aircraft</ButtonLink>}
          />
        </Panel>

        <Panel title="Error — the engine did not answer" note="The reference identifies the run and the rulebase, because 'it broke' is not actionable.">
          <div className="max-w-[560px] p-5 bg-sheet-raised rounded-sm border-t-[3px] border-sail-6 flex flex-col gap-3">
            <span className="t-h3 text-ink-hi">The run stopped at the airspace assessment</span>
            <p className="m-0 t-body-sm text-ink-mid pretty">
              No determination was written. Nothing you entered was lost.
            </p>
            <span className="self-start px-3.5 py-2.5 bg-sheet-well rounded-sm t-data-sm text-ink-mid tnum">
              ref ENG-5081 · rulebase {health?.rulebase_version ?? "—"}
            </span>
          </div>
        </Panel>

        <Panel
          title="Offline, or the service is waking"
          note="A free-tier backend sleeps after about 15 minutes. That is a wait, not a failure, and the client says so."
        >
          <div className="max-w-[560px] p-5 bg-sheet-well rounded-sm border-l-[3px] border-sail-3 flex flex-col gap-2">
            <span className="t-micro-10 text-sail-3">
              {isError ? "Not reachable" : "Warming"}
            </span>
            <p className="m-0 t-body-sm text-ink-mid pretty">
              {isError
                ? "The determination service did not answer. Your saved work is unaffected; it lives on the server, not in this tab."
                : "The determination service is waking. This takes up to half a minute on a free deployment, and the request completes on its own."}
            </p>
          </div>
        </Panel>

        <Panel title="Loading — a table" note="Static stepped opacity. No shimmer: a skeleton that moves implies progress nobody is making.">
          <div className="flex flex-col gap-sheet max-w-[640px]" aria-busy>
            {[1, 0.7, 0.45, 0.25].map((o, i) => (
              <div key={i} className="h-14 bg-sheet-well" style={{ opacity: o }} />
            ))}
          </div>
        </Panel>
      </main>
    </>
  );
}

function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-sheet p-4 md:p-6 flex flex-col gap-4">
      <div>
        <h3 className="m-0 t-h3 text-ink-hi">{title}</h3>
        {note && <p className="m-0 mt-1 t-cap text-ink-low max-w-[72ch] pretty">{note}</p>}
      </div>
      {children}
    </section>
  );
}
