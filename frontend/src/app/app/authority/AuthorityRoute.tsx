"use client";

/**
 * The country pack, cut to one operation's SAIL and required OSOs.
 *
 * Every line carries its verification state in words. This project has transcribed no
 * authority publication yet, so every line currently reads UNVERIFIED and says where to
 * check it — and that is shown prominently rather than tucked into a footnote, because
 * a checklist that looks official and is not is worse than no checklist.
 *
 * Build spec HARD RULE 3. The same content is rendered into the dossier as Appendix C.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { EmptyState } from "@/components/app/EmptyState";
import { Disclaimer } from "@/components/Brand";
import { ButtonLink } from "@/components/ui/Button";
import { Select } from "@/components/ui/Field";
import { SailBadge } from "@/components/SailBadge";
import { sailLevel, type PackItem, type SubmissionChecklist } from "@/lib/api-client";
import { usePrefs } from "@/lib/prefs";
import { useOperations, useSubmissionChecklist } from "@/lib/hooks";
import { cn } from "@/lib/cn";

/** The order the file is actually assembled in, with the heading for each part. */
const GROUPS: { kind: PackItem["kind"]; heading: string; note: string }[] = [
  {
    kind: "process",
    heading: "Process",
    note: "In order. Checking the geographical zones before the volume is fixed saves redrawing it.",
  },
  {
    kind: "form",
    heading: "The authority's forms",
    note: "SORA Copilot does not reproduce an authority's form. The dossier is the technical annex that accompanies it.",
  },
  {
    kind: "attachment",
    heading: "Attachments",
    note: "What travels with the application at this SAIL.",
  },
  {
    kind: "note",
    heading: "Open questions",
    note: "Things this pack deliberately does not state, because nobody has supplied them.",
  },
  { kind: "contact", heading: "Where it goes", note: "" },
];

export function AuthorityRoute() {
  const params = useSearchParams();
  const { data: operations = [], isLoading: loadingOps } = useOperations();
  const [selected, setSelected] = useState<string | null>(params.get("op"));

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
          slot="empty-operations"
          title="No operations yet"
          body="The submission checklist is cut to a determination's SAIL and the OSOs it required, so there is one as soon as an operation has been run."
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
        <ButtonLink href="/app/settings/" variant="secondary">
          Change the authority
        </ButtonLink>
      </div>

      {selected && <Checklist key={selected} operationId={selected} />}
    </main>
  );
}

function Checklist({ operationId }: { operationId: string }) {
  const { data, isLoading, isError } = useSubmissionChecklist(operationId);

  if (isLoading) {
    return (
      <div className="bg-sheet p-4 md:p-6 flex flex-col gap-sheet" aria-busy>
        {[1, 0.7, 0.45, 0.25].map((o, i) => (
          <div key={i} className="h-14 bg-sheet-well" style={{ opacity: o }} />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-sheet p-4 md:p-6">
        <p className="m-0 t-body-sm text-ink-mid pretty">
          The checklist could not be read. Nothing you entered was lost.
        </p>
      </div>
    );
  }

  const checklist: SubmissionChecklist = data;
  const level = sailLevel(checklist.sail);

  return (
    <div className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(340px,1fr))] flex-1">
      <div className="bg-sheet p-4 md:p-6 flex flex-col gap-6 min-w-0">
        <header className="flex flex-col gap-3">
          <div className="flex items-start gap-4 flex-wrap">
            {level && <SailBadge level={level} size="sm" />}
            <div className="min-w-0">
              <h2 className="m-0 t-h2 text-ink-hi">{checklist.authority}</h2>
              <span className="block mt-1 t-data-sm text-ink-low">
                {checklist.country_name}
                {checklist.sail ? ` · SAIL ${checklist.sail}` : " · not yet determined"}
                {` · ${checklist.due.length} items due`}
              </span>
            </div>
          </div>
          <p className="m-0 max-w-[68ch] t-body-sm text-ink-mid pretty">{checklist.summary}</p>
          {checklist.authority_url && (
            <a
              className="self-start t-data-sm text-accent underline underline-offset-2"
              href={checklist.authority_url}
              target="_blank"
              rel="noreferrer noopener"
            >
              {checklist.authority_url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </a>
          )}
        </header>

        {checklist.warning && (
          <div
            role="status"
            className="p-4 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm flex flex-col gap-1.5"
          >
            <span className="t-micro-10 text-sail-3">Unverified pack</span>
            <p className="m-0 t-cap text-ink-mid pretty">{checklist.warning}</p>
          </div>
        )}

        {GROUPS.map((group) => {
          const rows = checklist.due.filter((i) => i.kind === group.kind);
          if (!rows.length) return null;
          return (
            <section key={group.kind} className="flex flex-col gap-3">
              <div>
                <h3 className="m-0 t-h3 text-ink-hi">{group.heading}</h3>
                {group.note && (
                  <p className="m-0 mt-1 t-cap text-ink-low max-w-[68ch] pretty">{group.note}</p>
                )}
              </div>
              <ol className="m-0 p-0 list-none flex flex-col gap-sheet bg-hairline border border-hairline">
                {rows.map((item, i) => (
                  <Item key={item.id} item={item} index={group.kind === "process" ? i + 1 : null} />
                ))}
              </ol>
            </section>
          );
        })}
      </div>

      <div className="bg-sheet p-4 md:p-6 flex flex-col gap-6 min-w-0">
        <section className="flex flex-col gap-3">
          <h3 className="m-0 t-h3 text-ink-hi">Already in SORA Copilot</h3>
          <dl className="m-0 grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 t-data-sm">
            <dt className="text-ink-mid">Determination</dt>
            <dd className="m-0 text-ink-hi tnum">
              {checklist.sail ? `SAIL ${checklist.sail}` : "not run"}
            </dd>
            <dt className="text-ink-mid">Dossier versions</dt>
            <dd className="m-0 text-ink-hi tnum">{checklist.dossier_versions}</dd>
            <dt className="text-ink-mid">Evidence files</dt>
            <dd className="m-0 text-ink-hi tnum">{checklist.evidence_attached}</dd>
          </dl>
          <div className="flex gap-2.5 flex-wrap">
            <ButtonLink href={`/app/dossiers/?op=${encodeURIComponent(operationId)}`}>
              {checklist.dossier_versions ? "Open the dossier" : "Build the dossier"}
            </ButtonLink>
            <ButtonLink
              href={`/app/operations/view/?id=${encodeURIComponent(operationId)}`}
              variant="secondary"
            >
              The determination
            </ButtonLink>
          </div>
        </section>

        {checklist.pending.length > 0 && (
          <section className="flex flex-col gap-3 pt-5 border-t border-hairline">
            <div>
              <h3 className="m-0 t-h3 text-ink-hi">Not due at this SAIL</h3>
              <p className="m-0 mt-1 t-cap text-ink-low pretty">
                Listed so that the cost of a less favourable determination is visible
                before it is incurred.
              </p>
            </div>
            <ul className="m-0 p-0 list-none flex flex-col gap-2">
              {checklist.pending.map((item) => (
                <li key={item.id} className="flex gap-2.5 t-body-sm text-ink-mid">
                  <span aria-hidden className="text-ink-low flex-none">
                    —
                  </span>
                  <span className="pretty">
                    {item.title}
                    {item.min_sail && (
                      <span className="text-ink-low"> · from SAIL {item.min_sail}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="pt-5 border-t border-hairline">
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}

function Item({ item, index }: { item: PackItem; index: number | null }) {
  const { slots } = usePrefs();
  return (
    <li className="bg-sheet-well p-4 flex gap-3.5">
      {index !== null && (
        <span aria-hidden className="t-data-sm text-ink-low tnum flex-none pt-[2px]">
          {String(index).padStart(2, "0")}
        </span>
      )}
      <div className="flex-1 min-w-0 flex flex-col gap-1.5">
        <div className="flex items-baseline gap-2.5 flex-wrap">
          <span className="t-data-13 text-ink-hi">{item.title}</span>
          {/* State as a word, never as colour alone. */}
          <span
            className={cn(
              "t-micro-10 flex-none",
              item.verified ? "text-ink-low" : "text-sail-3",
            )}
          >
            {item.verified ? "verified" : "unverified"}
          </span>
          {item.min_sail && (
            <span className="t-micro-10 text-ink-low">from SAIL {item.min_sail}</span>
          )}
        </div>
        {item.detail && <p className="m-0 t-body-sm text-ink-mid pretty">{item.detail}</p>}
        {item.osos.length > 0 && (
          <span className="t-data-sm text-ink-low">For {item.osos.join(", ")}</span>
        )}
        {!item.verified && item.source && (
          <span className="t-cap text-ink-low pretty">{item.source}</span>
        )}
        {item.url && (
          <a
            className="self-start t-data-sm text-accent underline underline-offset-2"
            href={item.url}
            target="_blank"
            rel="noreferrer noopener"
          >
            {item.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
          </a>
        )}
        {slots && <code className="self-start t-data-sm text-[11px] text-ink-low">{item.id}</code>}
      </div>
    </li>
  );
}
