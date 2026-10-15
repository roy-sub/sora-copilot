"use client";

import { useEffect, useRef, useState } from "react";
import { CitationChip, EvidenceMark, RobustnessPill, type EvidenceState } from "@/components/Brand";
import { Button } from "@/components/ui/Button";
import { DialogClose, Drawer } from "@/components/ui/Dialog";
import { useToast } from "@/components/Toast";
import { ASSURANCE, OSO_TEXT } from "@/data/oso";
import { CITE } from "@/engine/rulebase";
import { roman } from "@/engine/engine";
import type { Sail } from "@/engine/types";
import type { EvidenceFile } from "@/lib/workspace";
import { cn } from "@/lib/cn";
import type { OsoRow } from "./GapAnalysis";

const ACCEPT = [".pdf", ".docx", ".xlsx"];
const MAX = 40 * 1024 * 1024;

function EvidenceUploader({ files, onAdd, onRemove }: { files: EvidenceFile[]; onAdd: (f: EvidenceFile[]) => void; onRemove: (name: string) => void }) {
  const [over, setOver] = useState(false);
  const [rejected, setRejected] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const { push } = useToast();

  const take = (list: FileList | null) => {
    if (!list) return;
    const ok: EvidenceFile[] = [];
    for (const f of Array.from(list)) {
      const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
      if (!ACCEPT.includes(ext)) { setRejected(`${f.name}: format not accepted. Use PDF, DOCX or XLSX.`); continue; }
      if (f.size > MAX) { setRejected(`${f.name}: over 40 MB.`); push({ tone: "fail", text: "Upload rejected — file over 40 MB", action: { label: "Dismiss" } }); continue; }
      ok.push({ name: f.name, bytes: f.size });
    }
    if (ok.length) { setRejected(null); onAdd(ok); }
  };

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files); }}
        className={cn("p-5 border border-dashed rounded-sm flex flex-col items-center gap-2.5 text-center tr-ui", over ? "border-accent" : "border-hairline-strong")}
      >
        <span className={cn("t-data-13", over ? "text-accent" : "text-ink-mid")}>{over ? "Release to attach" : "Drop evidence here, or"}</span>
        <Button onClick={() => input.current?.click()}>Choose files</Button>
        <input ref={input} type="file" multiple accept={ACCEPT.join(",")} className="sr-only" tabIndex={-1} onChange={(e) => { take(e.target.files); e.target.value = ""; }} />
        <span className="text-[11px] leading-[1.4] text-ink-low">PDF, DOCX or XLSX · 40 MB maximum · this build keeps file names on this device only</span>
      </div>
      {rejected && <div role="alert" className="p-3 bg-sheet-well border-l-[3px] border-sail-6 t-cap text-ink-mid">{rejected}</div>}
      {files.map((f) => (
        <div key={f.name} className="flex items-center gap-2.5 px-3.5 py-2 bg-sheet t-data-sm text-ink-hi min-h-11">
          <span aria-hidden>▣</span><span className="flex-1 truncate">{f.name}</span>
          <span className="text-ink-low">{(f.bytes / 1024 / 1024).toFixed(1)} MB</span>
          <button type="button" aria-label={`Remove ${f.name}`} onClick={() => onRemove(f.name)} className="size-9 bg-transparent border-0 text-ink-low hover:text-ink-hi">✕</button>
        </div>
      ))}
    </div>
  );
}

export function OsoDrawer({ oso, sail, files, onClose, onSave }: {
  oso: OsoRow | null; sail: Sail; files: EvidenceFile[];
  onClose: () => void; onSave: (s: EvidenceState, files: EvidenceFile[]) => void;
}) {
  const text = oso ? OSO_TEXT[oso.num] : null;
  const [checked, setChecked] = useState<boolean[]>([]);
  const [list, setList] = useState<EvidenceFile[]>([]);

  useEffect(() => {
    if (!oso || !text) return;
    const n = text.evidence.length;
    setChecked(text.evidence.map((_, i) => oso.state === "evidenced" || (oso.state === "partial" && i < Math.ceil(n / 2))));
    setList(files);
    // Reset only when a different OSO opens; parent re-renders must not wipe edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oso?.num]);

  if (!oso || !text) return <Drawer open={false} onOpenChange={() => {}} label="OSO">{null}</Drawer>;

  const n = checked.filter(Boolean).length;
  const next: EvidenceState = n === 0 && !list.length ? "gap" : n === checked.length ? "evidenced" : "partial";
  const level = oso.level === "nr" ? "low" : oso.level;

  return (
    <Drawer open={!!oso} onOpenChange={(o) => !o && onClose()} label={`${oso.id} detail`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <span className="t-micro text-ink-low">{oso.id} · required at SAIL {roman(sail)}</span>
          <h2 className="mt-2 mb-0 t-h2 text-ink-hi pretty">{oso.name}</h2>
        </div>
        <DialogClose aria-label="Close" className="size-11 flex-none bg-transparent border border-hairline rounded-sm text-ink-mid hover:text-ink-hi hover:border-hairline-strong text-base">✕</DialogClose>
      </div>
      <div className="flex gap-2.5 flex-wrap items-center">
        <RobustnessPill level={`${level} robustness`} />
        <EvidenceMark state={oso.state} />
      </div>
      <div className="p-4 bg-sheet-well rounded-sm flex flex-col gap-2">
        <span className="t-micro text-ink-low">What it requires</span>
        <p className="m-0 t-body-sm leading-[1.55] text-ink-mid pretty">{text.requires} {ASSURANCE[level]}</p>
        <span className="self-start"><CitationChip reference={`${CITE.oso} · ${oso.id}`} size="md" /></span>
      </div>
      <fieldset className="m-0 p-0 border-0 flex flex-col gap-2.5">
        <legend className="t-micro text-ink-low mb-2.5">Evidence that satisfies it</legend>
        <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
          {text.evidence.map((e, i) => (
            <label key={e} className="bg-sheet px-3.5 py-3 flex items-center gap-2.5 t-body-sm leading-[1.4] text-ink-mid min-h-11 cursor-pointer">
              <input type="checkbox" className="size-[18px] flex-none" checked={!!checked[i]} onChange={() => setChecked((c) => c.map((x, j) => (j === i ? !x : x)))} />
              <span className={checked[i] ? "text-ink-hi" : ""}>{e}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <EvidenceUploader files={list} onAdd={(f) => setList((l) => [...l, ...f.filter((x) => !l.some((y) => y.name === x.name))])} onRemove={(name) => setList((l) => l.filter((x) => x.name !== name))} />
      <div className="mt-auto flex gap-2.5 pt-2">
        <Button variant="secondary" className="flex-1" onClick={() => onSave("na", list)}>Mark not applicable</Button>
        <Button className="flex-1" onClick={() => onSave(next, list)}>Save · {next === "gap" ? "gap" : next}</Button>
      </div>
    </Drawer>
  );
}
