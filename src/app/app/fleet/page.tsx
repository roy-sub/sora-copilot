"use client";

import { useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { Button } from "@/components/ui/Button";
import { FieldLabel, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Dialog";
import { useToast } from "@/components/Toast";
import { kineticEnergyKj, type Aircraft } from "@/data/fixtures";
import { useWorkspace } from "@/lib/workspace";

const COLS = "grid-cols-[minmax(0,1.6fr)_110px_110px_100px_100px_100px_110px_minmax(0,1.4fr)] gap-3";

export default function Fleet() {
  const [open, setOpen] = useState(false);
  const { push } = useToast();
  const { fleet, aircraft, set } = useWorkspace();
  const save = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const n = (k: string) => Number(f.get(k));
    const model = String(f.get("model")).trim();
    const a: Aircraft = {
      model, registration: String(f.get("reg")).trim().toUpperCase() || `AC-${fleet.length + 1}`,
      maxDimensionM: n("dim"), mtomKg: n("mtom"), cruiseMs: n("cruise") || n("vmax"), maxSpeedMs: n("vmax"), fitted: [],
    };
    set("aircraft", [...aircraft, a]);
    setOpen(false);
    push({ tone: "ok", text: `${model} added to the fleet on this device` });
  };
  return (
    <>
      <PageHeader title="Drone fleet" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <div className="bg-sheet px-4 md:px-6 py-5 flex items-center justify-between gap-3 flex-wrap">
          <p className="m-0 max-w-[62ch] t-body-sm text-ink-mid pretty">Kinetic energy is computed from MTOM and maximum speed; it is not editable. Fitted mitigations here become the M1 and M2 candidates offered in intake.</p>
          <Button onClick={() => setOpen(true)}>Add aircraft</Button>
        </div>
        <div className="bg-sheet flex-1 overflow-x-auto">
          <table className="min-w-[960px] w-full border-collapse">
            <thead>
              <tr className={`grid ${COLS} px-6 py-3 bg-sheet-well border-b border-hairline`}>
                {["Aircraft", "Reg", "Max dim", "MTOM", "Cruise", "V max", "Kinetic E", "Fitted mitigations"].map((h) => <th key={h} scope="col" className="t-micro text-ink-low text-left font-semibold">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {fleet.map((f) => (
                <tr key={f.registration} className={`grid ${COLS} px-6 py-4 items-center border-b border-hairline min-h-11 hover:bg-sheet-raised tr-ui`}>
                  <td className="t-data text-ink-hi">{f.model}</td>
                  <td className="t-data-sm text-ink-mid">{f.registration}</td>
                  <td className="t-data-13 text-ink-hi">{f.maxDimensionM.toFixed(2)} m</td>
                  <td className="t-data-13 text-ink-hi">{f.mtomKg.toFixed(f.mtomKg < 10 ? 2 : 1)} kg</td>
                  <td className="t-data-13 text-ink-mid">{f.cruiseMs} m/s</td>
                  <td className="t-data-13 text-ink-mid">{f.maxSpeedMs} m/s</td>
                  <td className="t-data-13 text-ink-hi">{kineticEnergyKj(f).toFixed(2)} kJ</td>
                  <td className="t-cap leading-[1.4] text-ink-mid">{f.fitted.join(" · ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
      <Modal open={open} onOpenChange={setOpen} title="Add aircraft" description="Dimension and speed set the iGRC column. Kinetic energy is derived.">
        <form className="flex flex-col gap-4" onSubmit={save}>
          <div className="grid grid-cols-2 gap-4">
            <FieldLabel label="Model"><Input name="model" required placeholder="e.g. DJI Matrice 30T" /></FieldLabel>
            <FieldLabel label="Registration"><Input name="reg" placeholder="e.g. M30T-02" /></FieldLabel>
            <FieldLabel label="Max dimension (m)"><Input name="dim" required type="number" step="0.01" min="0.01" className="tnum" /></FieldLabel>
            <FieldLabel label="MTOM (kg)"><Input name="mtom" required type="number" step="0.01" min="0.01" className="tnum" /></FieldLabel>
            <FieldLabel label="Cruise (m/s)"><Input name="cruise" type="number" min="0" className="tnum" /></FieldLabel>
            <FieldLabel label="V max (m/s)"><Input name="vmax" required type="number" min="1" className="tnum" /></FieldLabel>
          </div>
          <div className="flex gap-2.5 justify-end">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit">Save aircraft</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
