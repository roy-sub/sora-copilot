"use client";

/**
 * The dossier builder.
 *
 * The orchestrated moment: section rows tick complete in sequence as generation runs.
 * It is not a progress bar over a guess — the backend renders the document in one
 * request, and the rows resolve as the request completes, so nothing claims to know more
 * than it does.
 */

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Disclaimer, RulebaseStamp } from "@/components/Brand";
import { EmptyState } from "@/components/app/EmptyState";
import { MediaSlot } from "@/components/MediaSlot";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Segmented, Select } from "@/components/ui/Field";
import { useToast } from "@/components/Toast";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import { ApiError } from "@/lib/api";
import { api, type DossierFormat, type DossierSection, type DossierStatus } from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { useDossierStatus, useGenerateDossier, useOperations } from "@/lib/hooks";
import { downloadFile } from "@/lib/upload";

const GLYPH: Record<DossierSection["state"], string> = {
  complete: "▣",
  partial: "◧",
  not_started: "□",
};

const INK: Record<DossierSection["state"], string> = {
  complete: "text-accent",
  partial: "text-sail-3",
  not_started: "text-ink-low",
};

export function DossiersRoute() {
  const params = useSearchParams();
  const { data: operations = [], isLoading: loadingOps } = useOperations();
  const [selected, setSelected] = useState<string | null>(params.get("op"));

  // Default to the first operation that has been determined, since a dossier is a
  // rendering of a determination and the others have nothing to render.
  useEffect(() => {
    if (selected || !operations.length) return;
    const determined = operations.find((o) => o.sail);
    setSelected((determined ?? operations[0]).id);
  }, [operations, selected]);

  if (loadingOps) return <main className="flex-1 bg-sheet" aria-busy />;

  if (!operations.length) {
    return (
      <main className="flex-1 bg-sheet p-6">
        <EmptyState
          slot="empty-dossiers"
          title="No dossiers yet"
          body="A dossier is a rendering of a determination, so there is one to build as soon as an operation has been run."
          action={<ButtonLink href="/app/new/">New operation</ButtonLink>}
        />
      </main>
    );
  }

  return (
    <main className="flex-1 flex flex-col gap-sheet min-w-0">
      <div className="bg-sheet px-4 md:px-6 py-5 flex items-center gap-3 flex-wrap justify-between">
        <label className="flex items-center gap-2.5">
          <span className="t-micro text-ink-low">Operation</span>
          <Select
            value={selected ?? ""}
            onChange={(e) => setSelected(e.target.value)}
            className="min-w-[260px]"
          >
            {operations.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
                {o.sail ? ` · SAIL ${o.sail}` : " · not run"}
              </option>
            ))}
          </Select>
        </label>
        {selected && (
          <ButtonLink
            href={`/app/operations/view/?id=${encodeURIComponent(selected)}`}
            variant="secondary"
          >
            Open the determination
          </ButtonLink>
        )}
      </div>

      {selected && <Builder key={selected} operationId={selected} />}
    </main>
  );
}

function Builder({ operationId }: { operationId: string }) {
  const { push } = useToast();
  const { data: status, isLoading } = useDossierStatus(operationId);
  const generate = useGenerateDossier(operationId);
  const [ticked, setTicked] = useState<number>(-1);
  const [error, setError] = useState<string | null>(null);
  // A plan refusal is kept as the error object rather than its message, because the
  // upgrade panel renders the limit, the usage and the plan, not the prose.
  const [limit, setLimit] = useState<ApiError | null>(null);
  // DOCX to edit alongside the authority's own forms, PDF to file. The two are rendered
  // from one content path on the server, so the choice is about what you do with it.
  const [format, setFormat] = useState<DossierFormat>("docx");

  const run = () => {
    setError(null);
    setLimit(null);
    setTicked(0);
    generate.mutate({ format }, {
      onSuccess: (dossier) => {
        setTicked(Number.MAX_SAFE_INTEGER);
        push({
          tone: "ok",
          text: `Dossier v${dossier.version} generated`,
          action: {
            label: "Download",
            onClick: () =>
              downloadFile(
                api.dossierDownloadPath(operationId, dossier.id),
                `sora-dossier-v${dossier.version}.${dossier.format}`,
              ).catch(() => push({ tone: "fail", text: "Download failed" })),
          },
        });
      },
      onError: (e) => {
        setTicked(-1);
        if (isPlanLimit(e)) {
          setLimit(e);
          return;
        }
        setError(
          e instanceof ApiError ? (e.problem.detail ?? e.problem.title) : "Generation failed.",
        );
      },
    });
  };

  // The rows tick in sequence while the request is in flight, then all complete when it
  // returns. Each tick is 180ms, which is the design's sail-step cadence.
  useEffect(() => {
    if (!generate.isPending || !status) return;
    const timer = setInterval(
      () => setTicked((t) => Math.min(t + 1, status.sections.length - 1)),
      180,
    );
    return () => clearInterval(timer);
  }, [generate.isPending, status]);

  if (isLoading || !status) return <div className="bg-sheet flex-1" aria-busy />;

  return (
    <div className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(320px,1fr))] flex-1">
      <div className="bg-sheet p-4 md:p-6 flex flex-col gap-5 min-w-0">
        <div>
          <h3 className="m-0 t-h3 text-ink-hi">Sections</h3>
          <p className="m-0 mt-1 t-body-sm text-ink-mid pretty">
            Every section is rendered from the stored determination. Nothing in the
            document is recomputed when it is generated.
          </p>
        </div>

        <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
          {status.sections.map((section, i) => {
            const done = generate.isPending ? i <= ticked : section.state === "complete";
            return (
              <div
                key={section.key}
                className="bg-sheet-well px-4 py-3.5 flex items-center gap-3 min-h-[52px] tr-ui"
              >
                <span
                  aria-hidden
                  className={cn(
                    "tr-ui",
                    generate.isPending && done ? "text-accent" : INK[section.state],
                  )}
                >
                  {generate.isPending && done ? "▣" : GLYPH[section.state]}
                </span>
                <span className="flex-1 t-data text-ink-hi">{section.name}</span>
                <span
                  className={cn(
                    "t-data-sm",
                    section.state === "partial" ? "text-sail-3" : "text-ink-low",
                  )}
                >
                  {generate.isPending && done ? "written" : section.meta}
                </span>
              </div>
            );
          })}
        </div>

        {status.blocker && (
          <div role="status" className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
            <span className="t-micro-10 text-sail-3">Cannot generate yet</span>
            <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">{status.blocker}</p>
          </div>
        )}

        {limit && <PlanLimit error={limit} />}

        {error && (
          <div role="alert" className="p-3 bg-sheet-well border-l-[3px] border-sail-6 rounded-sm">
            <span className="t-micro-10 text-sail-6">Generation failed</span>
            <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">{error}</p>
          </div>
        )}

        <div className="flex gap-2.5 flex-wrap items-center">
          <Button disabled={!status.can_generate || generate.isPending} onClick={run}>
            {generate.isPending ? "Generating" : `Generate v${status.next_version}`}
          </Button>
          <Segmented
            label="Format"
            value={format}
            onChange={(v) => setFormat(v as DossierFormat)}
            options={[
              { value: "docx", label: "DOCX" },
              { value: "pdf", label: "PDF" },
            ]}
          />
          {status.versions[0] && (
            <Button
              variant="secondary"
              onClick={() =>
                downloadFile(
                  api.dossierDownloadPath(operationId, status.versions[0].id),
                  `sora-dossier-v${status.versions[0].version}.${status.versions[0].format}`,
                ).catch((e) =>
                  push({ tone: "fail", text: e instanceof Error ? e.message : "Download failed" }),
                )
              }
            >
              Download {status.versions[0].format.toUpperCase()}
            </Button>
          )}
        </div>
        <span className="t-cap text-ink-low pretty">
          DOCX to edit alongside the authority&apos;s own forms; PDF to file. Both are
          rendered from the same stored determination and say the same thing.
        </span>

        <VersionHistory status={status} operationId={operationId} />
      </div>

      <div className="bg-sheet p-4 md:p-6 flex flex-col gap-4 min-w-0">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="m-0 t-h3 text-ink-hi">Preview</h3>
          <span className="t-data-sm text-ink-low">
            {status.versions.length
              ? `v${status.versions[0].version} · ${status.sections.length} sections`
              : "not generated"}
          </span>
        </div>
        <MediaSlot id="dossier-preview" />
        <p className="m-0 t-cap text-ink-low pretty">
          The preview image is a placeholder until real media is added. The generated
          document itself is complete — download it to read the real pages.
        </p>
        <div className="pt-4 border-t border-hairline flex flex-col gap-3">
          <RulebaseStamp authoritative />
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

function VersionHistory({
  status,
  operationId,
}: {
  status: DossierStatus;
  operationId: string;
}) {
  const { push } = useToast();
  if (!status.versions.length) {
    return (
      <div className="pt-5 border-t border-hairline">
        <span className="t-micro text-ink-low">Version history</span>
        <p className="m-0 mt-2 t-cap text-ink-low pretty">
          No versions yet. Each generated dossier is kept whole, with the rulebase it was
          generated against — a later rulebase change never alters an existing version.
        </p>
      </div>
    );
  }
  return (
    <div className="pt-5 border-t border-hairline">
      <span className="t-micro text-ink-low">Version history</span>
      <div className="mt-3 flex flex-col gap-3">
        {status.versions.map((v) => (
          <div key={v.id} className="flex gap-3 items-baseline">
            <span className="t-data-13 text-ink-hi tnum min-w-[28px]">v{v.version}</span>
            <span className="flex-1 t-body-sm text-ink-mid pretty">
              {v.note ?? "Generated from the stored determination"}
            </span>
            <span className="t-data-sm text-ink-low tnum">
              {v.format.toUpperCase()} · {new Date(v.generated_at).toLocaleDateString("en-GB")}
            </span>
            <button
              type="button"
              onClick={() =>
                downloadFile(
                  api.dossierDownloadPath(operationId, v.id),
                  `sora-dossier-v${v.version}.${v.format}`,
                ).catch((e) =>
                  push({ tone: "fail", text: e instanceof Error ? e.message : "Download failed" }),
                )
              }
              className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
            >
              Get
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
