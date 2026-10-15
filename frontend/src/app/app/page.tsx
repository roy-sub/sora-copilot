"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { EmptyState } from "@/components/app/EmptyState";
import { DemoNotice } from "@/components/Preliminary";
import { StatusPill } from "@/components/Brand";
import { SailBadge, SailPlaceholder } from "@/components/SailBadge";
import { ButtonLink } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";
import type { OpStatus } from "@/data/fixtures";
import { determinationOf, sailOf } from "@/lib/determine";
import { cn } from "@/lib/cn";
import { useWorkspace } from "@/lib/workspace";
import { usePrefs } from "@/lib/prefs";
import { opHref } from "@/components/verdict/Verdict";

const FILTERS: ("all" | OpStatus)[] = ["all", "draft", "determined", "dossier ready", "submitted", "authorised"];
const COLS = "md:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)_92px_minmax(0,1fr)_110px_110px] md:gap-4";

export default function Operations() {
  const { operations } = useWorkspace();
  const { setDemo } = usePrefs();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [q, setQ] = useState("");

  const counts = useMemo(() => Object.fromEntries(FILTERS.map((f) => [f, f === "all" ? operations.length : operations.filter((o) => o.status === f).length])), [operations]);
  const rows = operations.filter((o) =>
    (filter === "all" || o.status === filter) &&
    (!q || `${o.name} ${o.site} ${o.input.aircraft.model} ${o.input.aircraft.registration}`.toLowerCase().includes(q.toLowerCase())),
  );

  return (
    <>
      <PageHeader title="Operations" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <DemoNotice />
        <div className="bg-sheet px-4 md:px-6 py-5 flex items-center gap-3 flex-wrap justify-between">
          <div role="group" aria-label="Filter by status" className="flex gap-sheet bg-hairline border border-hairline rounded-sm overflow-x-auto no-scrollbar max-w-full">
            {FILTERS.map((f) => (
              <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}
                className={cn("min-h-11 px-3.5 t-micro tracking-[.08em] whitespace-nowrap border-0 tr-ui", filter === f ? "bg-sheet-raised text-ink-hi" : "bg-sheet text-ink-mid hover:text-ink-hi")}>
                {f} {counts[f]}
              </button>
            ))}
          </div>
          <Input type="search" aria-label="Filter by site or aircraft" placeholder="Filter by site or aircraft" value={q} onChange={(e) => setQ(e.target.value)} className="w-full md:w-auto md:min-w-[220px] text-[13px]" />
        </div>

        <div className="bg-sheet flex-1">
          <div className={cn("hidden md:grid px-6 py-3 border-b border-hairline bg-sheet-well", COLS)}>
            {["Operation", "Site", "SAIL", "Status", "Rulebase", "Last run"].map((h) => <span key={h} className="t-micro text-ink-low">{h}</span>)}
          </div>
          {rows.length === 0 ? (
            <div className="p-6">
              {operations.length === 0 ? (
                <EmptyState
                  slot="empty-operations"
                  title="No operations yet"
                  body="Start with the aircraft and the area. The engine needs eleven facts to reach a SAIL; the wizard collects them in about four minutes."
                  action={<ButtonLink href="/app/new/">New operation</ButtonLink>}
                  secondaryAction={
                    <button
                      type="button"
                      onClick={() => setDemo(true)}
                      className="inline-flex items-center min-h-11 px-4 bg-transparent border border-hairline-strong rounded-sm t-micro-10 text-ink-mid hover:text-ink-hi tr-ui"
                    >
                      Load the demo workspace
                    </button>
                  }
                />
              ) : (
                <p className="m-0 t-body-sm text-ink-mid">No operations match this filter. <button type="button" className="underline bg-transparent border-0 p-0 text-ink-hi" onClick={() => { setFilter("all"); setQ(""); }}>Clear it</button>.</p>
              )}
            </div>
          ) : rows.map((o) => {
            const d = determinationOf(o);
            const sail = sailOf(d);
            return (
              <Link key={o.id} href={opHref(o.id)}
                className={cn("no-underline grid grid-cols-[auto_minmax(0,1fr)] gap-x-3.5 gap-y-2.5 items-center p-4 md:px-6 md:py-3.5 border-b border-hairline min-h-11 hover:bg-sheet-raised tr-ui", COLS)}>
                <span className="col-span-full md:col-span-1 text-[15px] md:text-[14px] font-semibold md:font-medium leading-[1.35] text-ink-hi md:truncate">{o.name}</span>
                <span className="col-span-full md:col-span-1 t-body-sm leading-[1.4] text-ink-mid md:truncate">{o.site}</span>
                {sail ? <SailBadge level={sail} size="sm" /> : <SailPlaceholder size="sm" label={d ? "Certified category" : "Not run"} />}
                <StatusPill status={o.status} />
                <span className="col-span-full md:hidden t-data-sm text-ink-low">{o.rulebase ? `Rulebase ${o.rulebase} · ${o.lastRun}` : "Not yet run"}</span>
                <span className="hidden md:block t-data-sm text-ink-mid">{o.rulebase ?? "—"}</span>
                <span className="hidden md:block t-data-sm text-ink-low">{o.lastRun ?? "—"}</span>
              </Link>
            );
          })}
        </div>
      </main>
    </>
  );
}
