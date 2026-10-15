"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { EmptyState } from "@/components/app/EmptyState";
import { StatusPill } from "@/components/Brand";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { ButtonLink } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";
import { sailLevel, type OperationStatus } from "@/lib/api-client";
import { useOperations } from "@/lib/hooks";
import { cn } from "@/lib/cn";

const FILTERS: ("all" | OperationStatus)[] = [
  "all",
  "draft",
  "determined",
  "dossier_ready",
  "submitted",
  "authorised",
];

const LABEL: Record<string, string> = {
  all: "all",
  draft: "draft",
  determined: "determined",
  dossier_ready: "dossier ready",
  submitted: "submitted",
  authorised: "authorised",
};

const COLS =
  "md:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)_92px_minmax(0,1fr)_110px_110px] md:gap-4";

export default function Operations() {
  const { data: operations = [], isLoading, error } = useOperations();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [q, setQ] = useState("");

  const counts = useMemo(
    () =>
      Object.fromEntries(
        FILTERS.map((f) => [
          f,
          f === "all" ? operations.length : operations.filter((o) => o.status === f).length,
        ]),
      ),
    [operations],
  );

  const rows = operations.filter(
    (o) =>
      (filter === "all" || o.status === filter) &&
      (!q || `${o.name} ${o.site ?? ""}`.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <>
      <PageHeader title="Operations" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <div className="bg-sheet px-4 md:px-6 py-5 flex items-center gap-3 flex-wrap justify-between">
          <div
            role="group"
            aria-label="Filter by status"
            className="flex gap-sheet bg-hairline border border-hairline rounded-sm overflow-x-auto no-scrollbar max-w-full"
          >
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
                className={cn(
                  "min-h-11 px-3.5 t-micro tracking-[.08em] whitespace-nowrap border-0 tr-ui",
                  filter === f
                    ? "bg-sheet-raised text-ink-hi"
                    : "bg-sheet text-ink-mid hover:text-ink-hi",
                )}
              >
                {LABEL[f]} {counts[f]}
              </button>
            ))}
          </div>
          <div className="flex gap-2.5 items-center flex-wrap">
            <Input
              type="search"
              aria-label="Filter by name or site"
              placeholder="Filter by name or site"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-full md:w-auto md:min-w-[220px] text-[13px]"
            />
            <ButtonLink href="/app/new/">New operation</ButtonLink>
          </div>
        </div>

        <div className="bg-sheet flex-1">
          <div
            className={cn(
              "hidden md:grid px-6 py-3 border-b border-hairline bg-sheet-well",
              COLS,
            )}
          >
            {["Operation", "Site", "SAIL", "Status", "Rulebase", "Last run"].map((h) => (
              <span key={h} className="t-micro text-ink-low">
                {h}
              </span>
            ))}
          </div>

          {error ? (
            <div className="p-6 flex flex-col gap-3 items-start max-w-[52ch]">
              <span className="t-micro text-sail-6">Could not load your operations</span>
              <p className="m-0 t-body-sm text-ink-mid pretty">
                {error instanceof Error ? error.message : "The service did not answer."}
              </p>
            </div>
          ) : isLoading ? (
            <div className="p-6 flex flex-col gap-sheet" aria-busy>
              {[1, 0.7, 0.45, 0.25].map((o, i) => (
                <div key={i} className="h-14 bg-sheet-well" style={{ opacity: o }} />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6">
              {operations.length === 0 ? (
                <EmptyState
                  slot="empty-operations"
                  title="No operations yet"
                  body="Start with the aircraft and the area. The engine needs six confirmed facts to reach a SAIL; the wizard collects them in about four minutes."
                  action={<ButtonLink href="/app/new/">New operation</ButtonLink>}
                />
              ) : (
                <p className="m-0 t-body-sm text-ink-mid">
                  No operations match this filter.{" "}
                  <button
                    type="button"
                    className="underline bg-transparent border-0 p-0 text-ink-hi"
                    onClick={() => {
                      setFilter("all");
                      setQ("");
                    }}
                  >
                    Clear it
                  </button>
                  .
                </p>
              )}
            </div>
          ) : (
            rows.map((o) => {
              const level = sailLevel(o.sail);
              const href =
                o.status === "draft"
                  ? `/app/new/?id=${encodeURIComponent(o.id)}`
                  : `/app/operations/view/?id=${encodeURIComponent(o.id)}`;
              return (
                <Link
                  key={o.id}
                  href={href}
                  className={cn(
                    "no-underline grid grid-cols-[auto_minmax(0,1fr)] gap-x-3.5 gap-y-2.5 items-center p-4 md:px-6 md:py-3.5 border-b border-hairline min-h-11 hover:bg-sheet-raised tr-ui",
                    COLS,
                  )}
                >
                  <span className="col-span-full md:col-span-1 text-[15px] md:text-[14px] font-semibold md:font-medium leading-[1.35] text-ink-hi md:truncate">
                    {o.name}
                    {o.unconfirmed_facts > 0 && (
                      <span className="ml-2 t-micro-10 text-sail-3">
                        {o.unconfirmed_facts} unconfirmed
                      </span>
                    )}
                  </span>
                  <span className="col-span-full md:col-span-1 t-body-sm leading-[1.4] text-ink-mid md:truncate">
                    {o.site ?? "—"}
                  </span>
                  {level ? (
                    <SailBadge level={level} size="sm" />
                  ) : (
                    <SailPlaceholder
                      size="sm"
                      label={o.sail === "certified_category" ? "Certified category" : "Not run"}
                    />
                  )}
                  <StatusPill status={o.status} />
                  <span className="t-data-sm text-ink-mid tnum">{o.rulebase_version ?? "—"}</span>
                  <span className="t-data-sm text-ink-low tnum">
                    {o.determined_at ? new Date(o.determined_at).toLocaleDateString("en-GB") : "—"}
                  </span>
                </Link>
              );
            })
          )}
        </div>
      </main>
    </>
  );
}
