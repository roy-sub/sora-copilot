"use client";

import { useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { EmptyState } from "@/components/app/EmptyState";
import { Button } from "@/components/ui/Button";
import { FieldLabel, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Dialog";
import { useToast } from "@/components/Toast";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import type { ApiError } from "@/lib/api";
import type { DroneIn, FittedMitigation } from "@/lib/api-client";
import { useCreateDrone, useDeleteDrone, useDrones } from "@/lib/hooks";
import { cn } from "@/lib/cn";

const COLS =
  "grid-cols-[minmax(0,1.6fr)_110px_110px_100px_100px_100px_110px_minmax(0,1.4fr)_90px] gap-3";

const FITTED: { value: FittedMitigation; label: string }[] = [
  { value: "parachute", label: "Parachute" },
  { value: "tether", label: "Tether" },
  { value: "fts", label: "FTS" },
  { value: "daa", label: "DAA" },
  { value: "low_speed", label: "Low speed" },
];

export default function Fleet() {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limit, setLimit] = useState<ApiError | null>(null);
  const [fitted, setFitted] = useState<FittedMitigation[]>([]);
  const { push } = useToast();

  const { data: fleet = [], isLoading } = useDrones();
  const createDrone = useCreateDrone();
  const deleteDrone = useDeleteDrone();

  const save = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    const f = new FormData(e.currentTarget);
    const num = (k: string) => Number(f.get(k));
    const body: DroneIn = {
      name: String(f.get("name") ?? "").trim(),
      registration: String(f.get("registration") ?? "").trim().toUpperCase() || null,
      max_dimension_m: num("max_dimension_m"),
      mtom_kg: num("mtom_kg"),
      cruise_speed_ms: num("cruise_speed_ms") || num("max_speed_ms"),
      max_speed_ms: num("max_speed_ms"),
      fitted_mitigations: fitted,
    };
    setLimit(null);
    createDrone.mutate(body, {
      onSuccess: (drone) => {
        setOpen(false);
        setFitted([]);
        push({ tone: "ok", text: `${drone.name} added to the fleet` });
      },
      onError: (err) => {
        // The free plan caps the fleet. The upgrade panel replaces the error line,
        // because "could not save" is not what happened.
        if (isPlanLimit(err)) {
          setLimit(err);
          return;
        }
        setError(err instanceof Error ? err.message : "Could not save the aircraft");
      },
    });
  };

  return (
    <>
      <PageHeader title="Drone fleet" />
      <main className="flex-1 flex flex-col gap-sheet min-w-0">
        <div className="bg-sheet px-4 md:px-6 py-5 flex items-center justify-between gap-3 flex-wrap">
          <p className="m-0 max-w-[62ch] t-body-sm text-ink-mid pretty">
            The characteristic dimension and maximum speed choose the iGRC column, so they
            move every determination this aircraft flies. Kinetic energy is computed from
            mass and speed and is not editable.
          </p>
          <Button onClick={() => setOpen(true)}>Add aircraft</Button>
        </div>

        {isLoading ? (
          <div className="bg-sheet flex-1 p-6">
            <div className="flex flex-col gap-sheet" aria-busy>
              {[1, 0.7, 0.45].map((o, i) => (
                <div key={i} className="h-11 bg-sheet-well" style={{ opacity: o }} />
              ))}
            </div>
          </div>
        ) : fleet.length === 0 ? (
          <div className="bg-sheet flex-1 p-6">
            <EmptyState
              slot="empty-fleet"
              title="No aircraft yet"
              body="Add the aircraft you fly. The engine needs its characteristic dimension, mass and maximum speed to choose the iGRC column."
              action={<Button onClick={() => setOpen(true)}>Add aircraft</Button>}
            />
          </div>
        ) : (
          <div className="bg-sheet flex-1 overflow-x-auto">
            <table className="min-w-[1040px] w-full border-collapse">
              <thead>
                <tr className={cn("grid px-6 py-3 bg-sheet-well border-b border-hairline", COLS)}>
                  {[
                    "Aircraft",
                    "Reg",
                    "Max dim",
                    "MTOM",
                    "Cruise",
                    "V max",
                    "Kinetic E",
                    "Fitted mitigations",
                    "",
                  ].map((h, i) => (
                    <th
                      key={h || i}
                      scope="col"
                      className="t-micro text-ink-low text-left font-semibold"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {fleet.map((d) => (
                  <tr
                    key={d.id}
                    className={cn(
                      "grid px-6 py-4 items-center border-b border-hairline min-h-11 hover:bg-sheet-raised tr-ui",
                      COLS,
                    )}
                  >
                    <td className="t-data text-ink-hi">{d.name}</td>
                    <td className="t-data-sm text-ink-mid">{d.registration ?? "—"}</td>
                    <td className="t-data-sm text-ink-hi tnum">{d.max_dimension_m} m</td>
                    <td className="t-data-sm text-ink-hi tnum">{d.mtom_kg} kg</td>
                    <td className="t-data-sm text-ink-mid tnum">{d.cruise_speed_ms} m/s</td>
                    <td className="t-data-sm text-ink-hi tnum">{d.max_speed_ms} m/s</td>
                    <td className="t-data-sm text-ink-hi tnum">
                      {(d.kinetic_energy_j / 1000).toFixed(1)} kJ
                    </td>
                    <td className="t-cap text-ink-mid">
                      {d.fitted_mitigations.length ? d.fitted_mitigations.join(", ") : "none"}
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={() => {
                          if (!confirm(`Remove ${d.name} from the fleet?`)) return;
                          deleteDrone.mutate(d.id, {
                            onSuccess: () => push({ tone: "ok", text: `${d.name} removed` }),
                            onError: (err) =>
                              push({
                                tone: "fail",
                                text: err instanceof Error ? err.message : "Could not remove it",
                              }),
                          });
                        }}
                        className="min-h-11 px-2 bg-transparent border-0 t-micro-10 text-ink-low hover:text-sail-6 tr-ui"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <Modal open={open} onOpenChange={setOpen} title="Add aircraft">
        <form onSubmit={save} className="flex flex-col gap-4">
          <FieldLabel label="Model">
            <Input name="name" required placeholder="Freefly Alta X" />
          </FieldLabel>
          <FieldLabel label="Registration">
            <Input name="registration" placeholder="ALTA-X-01" />
          </FieldLabel>
          <div className="grid grid-cols-2 gap-4">
            <FieldLabel label="Max dimension (m)">
              <Input name="max_dimension_m" type="number" step="0.01" min="0.01" required className="tnum" />
            </FieldLabel>
            <FieldLabel label="MTOM (kg)">
              <Input name="mtom_kg" type="number" step="0.01" min="0.01" required className="tnum" />
            </FieldLabel>
            <FieldLabel label="Cruise speed (m/s)">
              <Input name="cruise_speed_ms" type="number" step="0.1" min="0" className="tnum" />
            </FieldLabel>
            <FieldLabel label="Max speed (m/s)">
              <Input name="max_speed_ms" type="number" step="0.1" min="0.1" required className="tnum" />
            </FieldLabel>
          </div>
          <div className="flex flex-col gap-2">
            <span className="t-micro text-ink-low">Fitted mitigations</span>
            <div className="flex flex-wrap gap-2">
              {FITTED.map((f) => {
                const on = fitted.includes(f.value);
                return (
                  <button
                    key={f.value}
                    type="button"
                    aria-pressed={on}
                    onClick={() =>
                      setFitted((prev) =>
                        on ? prev.filter((x) => x !== f.value) : [...prev, f.value],
                      )
                    }
                    className={cn(
                      "min-h-11 px-3.5 rounded-pill t-micro-10 tr-ui border",
                      on
                        ? "bg-accent text-accent-ink border-accent"
                        : "bg-transparent text-ink-mid border-hairline-strong hover:text-ink-hi",
                    )}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>
            <span className="t-cap text-ink-low pretty">
              What is fitted here decides which M2 claims the wizard will offer. An
              impact-reduction claim without a parachute is refused by the engine.
            </span>
          </div>
          {limit && <PlanLimit error={limit} compact />}
          {error && (
            <p className="m-0 t-cap text-ink-mid">
              <span className="text-sail-6" aria-hidden>
                □{" "}
              </span>
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={createDrone.isPending}>
            {createDrone.isPending ? "Saving" : "Add to fleet"}
          </Button>
        </form>
      </Modal>
    </>
  );
}
