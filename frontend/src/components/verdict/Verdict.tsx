"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { Disclaimer, RulebaseStamp, STAMP, type EvidenceState } from "@/components/Brand";
import { ComputationProgress, useStagedRun } from "@/components/ComputationProgress";
import { DemoNotice, PreliminaryNotice, PreliminaryTag } from "@/components/Preliminary";
import { SailBadge, SailPlaceholder, SailScale, useSteppedLevel } from "@/components/SailBadge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useToast } from "@/components/Toast";
import { aircraftByReg, opById, type Operation } from "@/data/fixtures";
import { counterfactuals, determine } from "@/engine/engine";
import type { Determination, OperationInput } from "@/engine/types";
import { cn } from "@/lib/cn";
import { evidenceOf, useWorkspace, type EvidenceFile } from "@/lib/workspace";
import { chainLinks, RiskChainReadout } from "./Chain";
import { DerivationTree } from "./DerivationTree";
import { GapAnalysis, type OsoRow } from "./GapAnalysis";
import { OsoDrawer } from "./OsoDrawer";

const EMPTY: EvidenceFile[] = [];
const ENV = { controlled: "controlled ground area", sparsely: "sparsely populated", populated: "populated", assembly: "assembly of people" };

function notes(i: OperationInput) {
  const m = i.mitigations;
  const mit = [m.m1a !== "none" && `M1(A) ${m.m1a}`, m.m1b !== "none" && `M1(B) ${m.m1b}`, m.m1c !== "none" && `M1(C) ${m.m1c}`, m.m2 !== "none" && `M2 ${m.m2}`].filter(Boolean).join(" · ");
  return {
    igrc: `${i.aircraft.maxDimensionM} m · ${ENV[i.ground.environment]}`,
    grc: mit || "No ground mitigations",
    arc: `Class ${i.airspace.airspaceClass} · ${i.maxAltitudeM} m AGL`,
    rarc: m.strategic ? "Operational restriction" : "Not claimed",
  };
}

export const opHref = (id: string) => (opById(id) ? `/app/operations/${id}/` : `/app/operations/view/?id=${encodeURIComponent(id)}`);

function download(name: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export function Verdict({ id }: { id: string }) {
  const ws = useWorkspace();
  const op = ws.op(id);
  const [ran, setRan] = useState(false);
  if (!ws.ready) return <><PageHeader title="Determination" /><main className="flex-1 bg-sheet" /></>;
  if (!op) return <NotFoundPanel />;
  if (op.status === "draft" && !ran) return <DraftRun op={op} onDone={() => setRan(true)} />;
  return <VerdictView op={op} />;
}

function NotFoundPanel() {
  return (
    <>
      <PageHeader title="Determination" />
      <main className="flex-1 bg-sheet p-6 flex flex-col gap-4 items-start">
        <h2 className="m-0 t-h2 text-ink-hi">This operation is not on this device</h2>
        <p className="m-0 t-body-sm text-ink-mid max-w-[52ch]">Operations created in this build are stored in this browser only. Open it from the device you used, or start a new one.</p>
        <ButtonLink href="/app/">Go to operations</ButtonLink>
      </main>
    </>
  );
}

function DraftRun({ op, onDone }: { op: Operation; onDone: () => void }) {
  const [go, setGo] = useState(false);
  const run = useStagedRun(go, onDone);
  return (
    <>
      <PageHeader title="Determination" />
      <main className="flex-1 grid gap-sheet grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))] content-start">
        <div className="bg-sheet p-6 flex flex-col gap-4 items-start">
          <span className="t-micro text-ink-low">Draft · not yet run</span>
          <h2 className="m-0 t-h2 text-ink-hi pretty">{op.name}</h2>
          <p className="m-0 t-body-sm text-ink-mid max-w-[52ch] pretty">No determination has been recorded for this operation. Running it computes the chain against {STAMP} from the facts already confirmed.</p>
          <div className="flex gap-2.5 flex-wrap">
            <Button onClick={() => setGo(true)} disabled={go}>{go ? "Running" : "Run determination"}</Button>
            <ButtonLink href="/app/new/" variant="secondary">Edit in the wizard</ButtonLink>
          </div>
        </div>
        <div className="bg-sheet-well p-6 flex flex-col gap-4">
          <span className="t-micro text-ink-low">Computation</span>
          {go ? <ComputationProgress {...run} /> : <p className="m-0 t-body-sm text-ink-low">Waiting for you to start the run.</p>}
        </div>
      </main>
    </>
  );
}

function VerdictView({ op }: { op: Operation }) {
  const ws = useWorkspace();
  const { push } = useToast();
  const recorded = opById(op.id)?.input ?? ws.created.find((c) => c.id === op.id)?.input ?? op.input;
  const d = useMemo(() => determine(op.input), [op.input]);
  const fitted = ws.fleet.find((a) => a.registration === op.input.aircraft.registration)?.fitted ?? aircraftByReg(op.input.aircraft.registration).fitted;

  // Counterfactuals are offered against the recorded inputs, so an applied one stays visible with UNDO.
  const baseD = useMemo(() => determine(recorded), [recorded]);
  const cfs = useMemo(() => counterfactuals(recorded, fitted).slice(0, 3), [recorded, fitted]);
  const appliedId = cfs.find((c) => JSON.stringify(c.input) === JSON.stringify(op.input))?.id ?? null;
  const modified = op.input !== recorded;

  const [runKey, setRunKey] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [openOso, setOpenOso] = useState<number | null>(null);

  const sail = d.outcome.kind === "sail" ? d.outcome.sail : null;
  const shown = useSteppedLevel(sail ?? 1, 180, 1);

  const changed = useMemo(() => {
    const prev = new Map(baseD.trace.map((n) => [n.id, n.value]));
    return new Set(modified ? d.trace.filter((n) => prev.get(n.id) !== n.value).map((n) => n.id) : []);
  }, [baseD, d, modified]);

  const rows: OsoRow[] = d.osos.map((o) => ({ ...o, state: evidenceOf(ws, op.id, o.num) }));
  const current = rows.find((r) => r.num === openOso) ?? null;

  const apply = (id: string, input: OperationInput | null) => {
    setBusy(id);
    setTimeout(() => {
      ws.setInput(op.id, input);
      setBusy(null);
      setRunKey((k) => k + 1);
    }, 420);
  };

  const exportTrace = () => {
    download(`${op.id}-trace.json`, JSON.stringify({ operation: op.name, input: op.input, determination: d }, null, 2), "application/json");
    push({ tone: "ok", text: "Trace exported with rulebase stamp" });
  };

  const corridor = op.corridorKm ? ` · ${op.corridorKm} km corridor` : "";
  const category = d.outcome.kind === "sail" ? "Specific category" : "Certified category";

  return (
    <>
      <PageHeader title="Determination" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <DemoNotice />
        <div className="bg-sheet p-4 md:p-6 flex gap-8 items-start flex-wrap">
          <div className="flex gap-5 items-start">
            {sail ? <SailBadge level={shown} size="lg" /> : <SailPlaceholder size="lg" label="CERTIFIED" />}
            <div className="flex flex-col gap-2 max-w-[30ch]">
              <span className="t-micro text-ink-low">Determination</span>
              <h2 className="m-0 t-h2 text-ink-hi pretty">{op.name}</h2>
              <p className="m-0 t-body-sm text-ink-mid">{category} · {op.input.operationType} · {op.input.aircraft.registration}{corridor}</p>
              <RulebaseStamp />
            </div>
          </div>
          <div className="flex-1 min-w-[min(300px,100%)] flex flex-col gap-2.5">
            <div className="flex items-baseline justify-between gap-4 flex-wrap">
              <span className="t-micro text-ink-low">Risk chain</span>
              <PreliminaryTag />
            </div>
            <RiskChainReadout key={runKey} links={chainLinks(d, notes(op.input))} countUp={runKey === 0} recomputing={!!busy} />
            <SailScale />
            {d.outcome.kind === "certified" && <p className="m-0 t-body-sm text-ink-mid">{d.outcome.reason} SORA does not apply; the operation needs the certified category.</p>}
          </div>
        </div>

        {modified && (
          <div role="status" className="bg-sheet px-4 md:px-6 py-3 flex items-center gap-3 flex-wrap border-l-[3px] border-accent">
            <span className="flex-1 t-body-sm text-ink-mid">Re-run with a change to the recorded inputs. Changed nodes carry an accent band.</span>
            <Button variant="ghost" onClick={() => apply("revert", null)}>Revert to recorded inputs</Button>
          </div>
        )}

        <div className="flex flex-wrap gap-sheet items-stretch">
          <div className="bg-sheet p-4 md:p-6 flex-[1_1_560px] min-w-0">
            <DerivationTree d={d} changed={changed} runKey={runKey} onReplay={() => setRunKey((k) => k + 1)} />
          </div>
          <div className="bg-sheet p-4 md:p-6 flex flex-col gap-6 flex-[0_1_420px] min-w-[min(320px,100%)]">
            <div>
              <h3 className="m-0 t-h3 text-ink-hi">Counterfactual advisor</h3>
              <p className="mt-1 mb-4 t-body-sm text-ink-mid pretty">What would change the determination, and what it costs you.</p>
              {cfs.length === 0 ? (
                <p className="m-0 p-4 bg-sheet-well t-body-sm text-ink-mid">No single change to the claimed mitigations or airspace lowers this SAIL.</p>
              ) : (
                <div className="flex flex-col gap-sheet bg-hairline">
                  {cfs.map((c) => {
                    const on = appliedId === c.id;
                    const r = c.result.outcome.kind === "sail" ? c.result.outcome.sail : null;
                    return (
                      <div key={c.id} className={cn("bg-sheet-well p-4 flex flex-col gap-3", busy && "pointer-events-none")}>
                        <div className="flex items-start justify-between gap-3">
                          <span className="t-data text-ink-hi pretty">{c.title}</span>
                          {r && <SailBadge level={r} size="sm" />}
                        </div>
                        <span className="t-data-sm leading-none tracking-[.06em] text-ink-hi"><span aria-hidden className="text-accent">→ </span>{c.effect}</span>
                        <span className="t-cap text-ink-low pretty">{c.cost}</span>
                        <Button variant={on ? "primary" : "secondary"} className="tracking-[.08em] px-3.5" onClick={() => apply(c.id, on ? null : c.input)}>
                          {busy === c.id ? "Re-running" : on ? "Applied · undo" : "Apply and re-run"}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="flex flex-col gap-3 pt-5 border-t border-hairline">
              <PreliminaryNotice />
              <RulebaseStamp authoritative />
              <Disclaimer />
              <div className="flex gap-2.5 flex-wrap">
                <ButtonLink href={`/app/dossiers/?op=${encodeURIComponent(op.id)}`} className="flex-1 min-w-[140px]">Build dossier</ButtonLink>
                <Button variant="secondary" className="flex-1 min-w-[120px]" onClick={exportTrace}>Export trace</Button>
              </div>
            </div>
          </div>
        </div>

        {sail && (
          <div className="bg-sheet p-4 md:p-6">
            <GapAnalysis rows={rows} sail={sail} onOpen={setOpenOso} />
          </div>
        )}
        {d.outcome.kind === "sail" && (
          <div className="bg-sheet px-4 md:px-6 py-4 flex gap-3 items-start">
            <span className="t-micro text-sail-3 flex-none pt-0.5">Containment</span>
            <p className="m-0 t-cap text-ink-mid">{d.containment.note} <Link href="/legal#changelog">See the changelog</Link>.</p>
          </div>
        )}
      </main>
      {sail && (
        <OsoDrawer
          oso={current}
          sail={sail}
          files={(current && ws.files[op.id]?.[current.num]) || EMPTY}
          onClose={() => setOpenOso(null)}
          onSave={(s: EvidenceState, files) => {
            ws.setEvidence(op.id, current!.num, s, files);
            setOpenOso(null);
            push({ tone: s === "gap" ? "warn" : "ok", text: s === "gap" ? `${current!.id} still has no evidence` : `${current!.id} saved as ${s === "na" ? "not applicable" : s}` });
          }}
        />
      )}
    </>
  );
}

export type { Determination };
