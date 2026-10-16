"use client";

/**
 * The intake wizard. Seven steps, resumable, nothing reaching the engine until the
 * operator presses Run on the review step.
 *
 * The draft lives on the server (`PATCH /operations/{id}/draft`), not in localStorage, so
 * it resumes on another device and so the review step shows the same facts the engine
 * will read. Every step saves on change; "Autosaved · resumable" is a statement about
 * the server, not a hope about the browser.
 */

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Disclaimer, RulebaseStamp } from "@/components/Brand";
import { ComputationProgress, useStagedRun } from "@/components/ComputationProgress";
import { Button, ButtonLink } from "@/components/ui/Button";
import { FieldLabel, Input, RadioRow, Segmented, Select } from "@/components/ui/Field";
import { useToast } from "@/components/Toast";
import {
  AdjacentWarning,
  AreaReadout,
  DensityLegend,
  DerivationNotes,
  LayerControl,
} from "@/components/map/MapPanels";
import {
  DEFAULT_LAYERS,
  MapVolumeEditor,
  type LayerKey,
  type Layers,
} from "@/components/map/MapVolumeEditor";
import { IntakePanel } from "@/components/wizard/IntakePanel";
import { MITIGATIONS, MitigationCard } from "@/components/wizard/MitigationCard";
import { STEPS, WizardStepper, stepIndex, type StepKey } from "@/components/wizard/WizardStepper";
import { ApiError } from "@/lib/api";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import { WorkedExampleButton } from "@/components/app/WorkedExampleButton";
import {
  type AirspaceClass,
  type Draft,
  type Drone,
  type Extractor,
  type GeoDerive,
  type GeoJSONPolygon,
  type GroundEnvironment,
  type OperationType,
  type Robustness,
} from "@/lib/api-client";
import { cn } from "@/lib/cn";
import { env } from "@/lib/env";
import {
  useConfirmFact,
  useCreateOperation,
  useDeriveGeo,
  useDrones,
  useFacts,
  useIntakeChat,
  useOperation,
  usePatchDraft,
  useRejectFact,
  useRunDetermination,
  useSampleDensity,
} from "@/lib/hooks";

const GROUND_OPTIONS: { value: GroundEnvironment; title: string; body: string }[] = [
  {
    value: "controlled_ground_area",
    title: "Controlled ground area",
    body: "Access restricted to people under the operator's control for the duration.",
  },
  {
    value: "sparsely_populated",
    title: "Sparsely populated",
    body: "Farmland, open country, scattered dwellings.",
  },
  {
    value: "populated",
    title: "Populated",
    body: "Residential, commercial or industrial area within the ground risk buffer.",
  },
  {
    value: "assembly_of_people",
    title: "Assembly of people",
    body: "A gathering where people cannot move away. Pins the intrinsic ground risk to the top band.",
  },
];

const AIRSPACE_CLASSES: AirspaceClass[] = ["a", "b", "c", "d", "e", "f", "g"];

type Mission = Record<string, unknown>;

const get = (mission: Mission, path: string): unknown =>
  path.split(".").reduce<unknown>((cur, part) => {
    if (cur && typeof cur === "object" && part in (cur as Record<string, unknown>)) {
      return (cur as Record<string, unknown>)[part];
    }
    return undefined;
  }, mission);

export function Wizard({ operationId }: { operationId: string | null }) {
  const router = useRouter();
  const { push } = useToast();
  const reduce = useReducedMotion();

  const [step, setStep] = useState<StepKey>("aircraft");
  const [furthest, setFurthest] = useState<StepKey>("aircraft");
  const [direction, setDirection] = useState(1);
  const [panelOpen, setPanelOpen] = useState(true);
  const [layers, setLayers] = useState<Layers>(DEFAULT_LAYERS);
  const [derived, setDerived] = useState<GeoDerive | null>(null);
  const [extractor, setExtractor] = useState<Extractor | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  // A plan refusal is held as the error object, not its message: the upgrade panel is
  // rendered from the limit and the usage.
  const [runLimit, setRunLimit] = useState<ApiError | null>(null);
  const [extractLimit, setExtractLimit] = useState<ApiError | null>(null);
  const [startLimit, setStartLimit] = useState<ApiError | null>(null);
  const [extrudeKey, setExtrudeKey] = useState(0);
  const [localGeometry, setLocalGeometry] = useState<GeoJSONPolygon | null>(null);

  const { data: fleet = [] } = useDrones();
  const { data: operation } = useOperation(operationId);
  const { data: facts = [] } = useFacts(operationId);
  const createOperation = useCreateOperation();
  const patchDraft = usePatchDraft(operationId ?? "");
  const deriveGeo = useDeriveGeo(operationId ?? "");
  const sampleDensity = useSampleDensity(operationId ?? "");
  const chat = useIntakeChat(operationId ?? "");
  const confirmFact = useConfirmFact(operationId ?? "");
  const rejectFact = useRejectFact(operationId ?? "");
  const runDetermination = useRunDetermination(operationId ?? "");
  const staged = useStagedRun(running, () => undefined);

  const mission: Mission = useMemo(
    () => (operation?.mission ?? {}) as Mission,
    [operation?.mission],
  );
  const pending = facts.filter((f) => f.status === "pending");

  const geometry = localGeometry ?? ((get(mission, "volume.flight_geography") as GeoJSONPolygon) ?? null);
  const selectedDrone = fleet.find((d) => d.id === get(mission, "drone_id"));

  const advance = (next: StepKey) => {
    setDirection(stepIndex(next) >= stepIndex(step) ? 1 : -1);
    setStep(next);
    if (stepIndex(next) > stepIndex(furthest)) setFurthest(next);
  };

  // Keep the furthest-reached marker honest when a draft is resumed.
  useEffect(() => {
    if (stepIndex(step) > stepIndex(furthest)) setFurthest(step);
  }, [step, furthest]);

  const save = (patch: Record<string, unknown>) => {
    if (!operationId) return;
    patchDraft.mutate(patch as never, {
      onError: (e) => push({ tone: "fail", text: e instanceof Error ? e.message : "Could not save" }),
    });
  };

  // ---------------------------------------------------------------- no operation yet

  if (!operationId) {
    return (
      <StartPanel
        busy={createOperation.isPending}
        limit={startLimit}
        onStart={(name, site) => {
          setStartLimit(null);
          createOperation.mutate(
            { name, site },
            {
              onSuccess: (op) => router.replace(`/app/new/?id=${encodeURIComponent(op.id)}`),
              onError: (e) => {
                // The free plan caps operations. Shown here rather than as a toast,
                // because a toast that disappears is no use when the answer is "buy".
                if (isPlanLimit(e)) {
                  setStartLimit(e);
                  return;
                }
                push({ tone: "fail", text: e instanceof Error ? e.message : "Could not start" });
              },
            },
          );
        }}
      />
    );
  }

  // ---------------------------------------------------------------- the run

  const canRun = Boolean(operation) && pending.length === 0;
  const missingList = (operation ? missingFields(mission) : []) as string[];

  const run = () => {
    setRunError(null);
    setRunLimit(null);
    setRunning(true);
    runDetermination.mutate(false, {
      onSuccess: () => {
        push({ tone: "ok", text: "Determination computed" });
        router.push(`/app/operations/view/?id=${encodeURIComponent(operationId)}`);
      },
      onError: (e) => {
        setRunning(false);
        if (isPlanLimit(e)) {
          setRunLimit(e);
          return;
        }
        if (e instanceof ApiError) {
          const problem = e.problem;
          setRunError(
            problem.unconfirmed_fields?.length
              ? `Confirm or reject these first: ${problem.unconfirmed_fields.join(", ")}.`
              : (problem.detail ?? problem.title),
          );
        } else {
          setRunError(e instanceof Error ? e.message : "The determination did not run.");
        }
      },
    });
  };

  const title = STEPS[stepIndex(step)].title;
  const slide = reduce ? {} : { x: direction * 12, opacity: 0 };

  return (
    <main className="flex-1 flex flex-col min-w-0">
      <WizardStepper current={step} furthest={furthest} onGo={advance} />

      <div className="flex-1 flex gap-sheet flex-wrap min-w-0">
        <div className="flex-1 min-w-[min(340px,100%)] bg-sheet p-4 md:p-6 flex flex-col gap-5">
          <div className="flex items-baseline justify-between gap-4 flex-wrap">
            <h2 className="m-0 t-h2 text-ink-hi pretty">{title}</h2>
            <span className="t-data-sm text-ink-low">
              {patchDraft.isPending ? "Saving…" : "Autosaved · resumable"}
            </span>
          </div>

          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={step}
              initial={slide}
              animate={{ x: 0, opacity: 1 }}
              exit={reduce ? {} : { x: -direction * 12, opacity: 0 }}
              transition={reduce ? { duration: 0 } : { duration: 0.24, ease: [0.22, 0.61, 0.36, 1] }}
              className="flex-1 min-w-0"
            >
              {step === "aircraft" && (
                <AircraftStep
                  fleet={fleet}
                  value={String(get(mission, "drone_id") ?? "")}
                  onChange={(id) => save({ drone_id: id })}
                />
              )}

              {step === "operation" && (
                <OperationStep
                  operationType={(get(mission, "operation_type") as OperationType) ?? "bvlos"}
                  altitude={Number(get(mission, "volume.max_altitude_agl_m") ?? 118)}
                  onChange={(patch) => save(patch)}
                />
              )}

              {step === "map" && (
                <MapStep
                  geometry={geometry}
                  derived={derived}
                  layers={layers}
                  extrudeKey={extrudeKey}
                  deriving={deriveGeo.isPending}
                  adjacentPopulated={Boolean(get(mission, "adjacent_area_populated"))}
                  peak={(get(mission, "population_density_per_km2") as number) ?? null}
                  onToggleLayer={(k: LayerKey) => setLayers((l) => ({ ...l, [k]: !l[k] }))}
                  onDraw={(polygon) => setLocalGeometry(polygon)}
                  onCommit={(polygon) => {
                    setLocalGeometry(polygon);
                    patchDraft.mutate({ volume: { flight_geography: polygon } } as never, {
                      onSuccess: () =>
                        deriveGeo.mutate(undefined, {
                          onSuccess: (d) => {
                            setDerived(d);
                            setExtrudeKey((k) => k + 1);
                          },
                          onError: (e) =>
                            push({
                              tone: "warn",
                              text: e instanceof Error ? e.message : "Could not derive the volumes",
                            }),
                        }),
                    });
                  }}
                />
              )}

              {step === "ground" && (
                <GroundStep
                  value={(get(mission, "ground_environment") as GroundEnvironment) ?? null}
                  density={(get(mission, "population_density_per_km2") as number) ?? null}
                  adjacentPopulated={Boolean(get(mission, "adjacent_area_populated"))}
                  busy={sampleDensity.isPending}
                  onChange={(v) => save({ ground_environment: v })}
                  onDensity={(density, adjacent) =>
                    sampleDensity.mutate(
                      { density_per_km2: density, adjacent_area_populated: adjacent, source: "operator" },
                      {
                        onSuccess: (s) =>
                          push({
                            tone: "ok",
                            text: `Recorded ${density.toLocaleString("en-GB")} ppl/km² — band ${s.density_band.replace(/_/g, " ")}`,
                          }),
                      },
                    )
                  }
                />
              )}

              {step === "airspace" && (
                <AirspaceStep
                  mission={mission}
                  altitude={Number(get(mission, "volume.max_altitude_agl_m") ?? 0)}
                  onChange={(patch) => save(patch)}
                />
              )}

              {step === "mitigations" && (
                <MitigationsStep
                  mission={mission}
                  fitted={selectedDrone?.fitted_mitigations ?? []}
                  onChange={(kind, level) =>
                    save({ mitigations: { ...(get(mission, "mitigations") as object), [kind]: level } })
                  }
                />
              )}

              {step === "review" && (
                <ReviewStep
                  mission={mission}
                  drone={selectedDrone}
                  derived={derived}
                  pendingCount={pending.length}
                  missing={missingList}
                  running={running}
                  staged={staged}
                  error={runError}
                  limit={runLimit}
                  canRun={canRun && missingList.length === 0}
                  onRun={run}
                  onGo={advance}
                />
              )}
            </motion.div>
          </AnimatePresence>

          <div className="mt-auto pt-5 border-t border-hairline flex gap-2.5 justify-between flex-wrap">
            <Button
              variant="secondary"
              disabled={stepIndex(step) === 0}
              onClick={() => advance(STEPS[Math.max(0, stepIndex(step) - 1)].key)}
            >
              Back
            </Button>
            {step !== "review" ? (
              <Button onClick={() => advance(STEPS[stepIndex(step) + 1].key)}>Continue</Button>
            ) : (
              <span className="t-cap text-ink-low self-center">
                Running the determination is the last step.
              </span>
            )}
          </div>
        </div>

        {panelOpen ? (
          <IntakePanel
            className="w-full rail:w-[360px] rail:flex-none"
            facts={facts}
            fleet={fleet}
            extractor={extractor}
            busy={chat.isPending}
            error={extractError}
            limit={extractLimit}
            onHide={() => setPanelOpen(false)}
            onSend={(text) => {
              setExtractError(null);
              setExtractLimit(null);
              chat.mutate(text, {
                onSuccess: (r) => setExtractor(r.extractor),
                onError: (e) => {
                  if (isPlanLimit(e)) {
                    setExtractLimit(e);
                    return;
                  }
                  setExtractError(e instanceof Error ? e.message : "Extraction failed.");
                },
              });
            }}
            onConfirm={(id) => confirmFact.mutate(id)}
            onReject={(id) => rejectFact.mutate(id)}
            onEdit={(s) => advance(s)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setPanelOpen(true)}
            className="self-start bg-sheet min-h-11 px-4 t-micro-10 text-ink-mid hover:text-ink-hi border-0 tr-ui"
          >
            Describe the mission
          </button>
        )}
      </div>
    </main>
  );
}

/** Required fields the draft does not yet carry, in the wizard's words. */
function missingFields(mission: Mission): string[] {
  const required: [string, string][] = [
    ["drone_id", "Aircraft"],
    ["operation_type", "Operation type"],
    ["volume.flight_geography", "Flight geography"],
    ["volume.max_altitude_agl_m", "Maximum altitude"],
    ["ground_environment", "Ground environment"],
    ["airspace_class", "Airspace class"],
  ];
  return required
    .filter(([path]) => {
      const v = get(mission, path);
      return v === undefined || v === null || v === "";
    })
    .map(([, label]) => label);
}

// ------------------------------------------------------------------ steps

function StartPanel({
  busy,
  limit,
  onStart,
}: {
  busy: boolean;
  limit: ApiError | null;
  onStart: (name: string, site: string) => void;
}) {
  const [name, setName] = useState("");
  const [site, setSite] = useState("");
  return (
    <main className="flex-1 bg-sheet p-4 md:p-6 flex flex-col gap-5 items-start">
      <div>
        <span className="t-micro text-ink-low">New operation</span>
        <h2 className="m-0 mt-2 t-h2 text-ink-hi">Name the operation</h2>
        <p className="m-0 mt-2 t-body-sm text-ink-mid max-w-[52ch] pretty">
          The wizard collects the facts the engine needs. Nothing reaches the engine until
          you confirm it at the last step.
        </p>
      </div>
      <form
        className="flex flex-col gap-5 w-full max-w-[460px]"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) onStart(name.trim(), site.trim());
        }}
      >
        <FieldLabel label="Operation name">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Powerline corridor — Mur valley"
            required
          />
        </FieldLabel>
        <FieldLabel label="Site">
          <Input value={site} onChange={(e) => setSite(e.target.value)} placeholder="Graz Süd, AT" />
        </FieldLabel>
        {limit && <PlanLimit error={limit} />}
        <Button type="submit" size="lg" disabled={busy || !name.trim()}>
          {busy ? "Starting" : "Start the wizard"}
        </Button>
      </form>
      <div className="pt-5 border-t border-hairline flex flex-col gap-3 w-full max-w-[460px]">
        <p className="m-0 t-cap text-ink-low pretty">
          Not sure what the engine needs? Have it build a finished one — a real
          powerline inspection, run through the same engine, that you can then edit.
        </p>
        <WorkedExampleButton />
      </div>
    </main>
  );
}

function AircraftStep({
  fleet,
  value,
  onChange,
}: {
  fleet: Drone[];
  value: string;
  onChange: (id: string) => void;
}) {
  if (!fleet.length) {
    return (
      <div className="flex flex-col gap-4 items-start max-w-[52ch]">
        <h3 className="m-0 t-h3 text-ink-hi">No aircraft on file</h3>
        <p className="m-0 t-body-sm text-ink-mid pretty">
          The aircraft&apos;s characteristic dimension and maximum speed choose the iGRC
          column, so the engine cannot run without one. Add it once and every operation
          can use it.
        </p>
        <ButtonLink href="/app/fleet/">Add an aircraft</ButtonLink>
      </div>
    );
  }
  return (
    <div className="grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(240px,1fr))]">
      {fleet.map((d) => (
        <label
          key={d.id}
          className={cn(
            "bg-sheet-well hover:bg-sheet-raised tr-ui p-4 flex flex-col gap-2.5 cursor-pointer",
            value === d.id && "shadow-[inset_2px_0_0_var(--accent)]",
          )}
        >
          <span className="flex items-center gap-2.5">
            <input
              type="radio"
              name="aircraft"
              checked={value === d.id}
              onChange={() => onChange(d.id)}
              className="size-[18px]"
            />
            <span className="t-data text-[15px] font-semibold leading-[1.3] text-ink-hi">
              {d.name}
            </span>
          </span>
          <span className="grid grid-cols-2 gap-1.5 t-data-sm text-ink-mid">
            <span>Max dim {d.max_dimension_m} m</span>
            <span>MTOM {d.mtom_kg} kg</span>
            <span>V max {d.max_speed_ms} m/s</span>
            <span>KE {(d.kinetic_energy_j / 1000).toFixed(1)} kJ</span>
          </span>
          <span className="t-cap text-ink-low">
            Fitted: {d.fitted_mitigations.length ? d.fitted_mitigations.join(", ") : "none"}
          </span>
        </label>
      ))}
    </div>
  );
}

function OperationStep({
  operationType,
  altitude,
  onChange,
}: {
  operationType: OperationType;
  altitude: number;
  onChange: (patch: Record<string, unknown>) => void;
}) {
  const aboveBand = altitude > 152.4;
  return (
    <div className="flex flex-col gap-5 max-w-[620px]">
      <div>
        <span className="t-micro text-ink-low">Operation type</span>
        <Segmented
          className="mt-2.5"
          label="Operation type"
          size="lg"
          value={operationType}
          onChange={(v) => onChange({ operation_type: v })}
          options={[
            { value: "vlos", label: "VLOS" },
            { value: "evlos", label: "EVLOS" },
            { value: "bvlos", label: "BVLOS" },
          ]}
        />
      </div>
      <FieldLabel label="Maximum altitude (m AGL)">
        <Input
          type="number"
          min={1}
          max={1000}
          value={altitude}
          onChange={(e) =>
            onChange({ volume: { max_altitude_agl_m: Number(e.target.value) || 0 } })
          }
          className="tnum"
        />
      </FieldLabel>
      <p className="m-0 t-body-sm text-ink-mid pretty">
        The air risk tree splits at <strong className="text-ink-hi font-semibold">500 ft</strong>,
        which is 152 m AGL — not the round 150 m. This flight is{" "}
        {aboveBand ? "above" : "at or below"} that boundary.
      </p>
      {aboveBand && (
        <div className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
          <span className="t-micro-10 text-sail-3">Above 500 ft</span>
          <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">
            Above the band boundary the air risk class rises, and in controlled airspace or
            a Mode-S veil it reaches ARC d. The airspace step is where that is settled.
          </p>
        </div>
      )}
    </div>
  );
}

function MapStep({
  geometry,
  derived,
  layers,
  extrudeKey,
  deriving,
  adjacentPopulated,
  peak,
  onToggleLayer,
  onDraw,
  onCommit,
}: {
  geometry: GeoJSONPolygon | null;
  derived: GeoDerive | null;
  layers: Layers;
  extrudeKey: number;
  deriving: boolean;
  adjacentPopulated: boolean;
  peak: number | null;
  onToggleLayer: (k: LayerKey) => void;
  onDraw: (polygon: GeoJSONPolygon) => void;
  onCommit: (polygon: GeoJSONPolygon) => void;
}) {
  return (
    <div className="flex gap-sheet flex-wrap bg-hairline">
      <MapVolumeEditor
        className="flex-1 min-w-[min(280px,100%)] aspect-[16/10]"
        value={geometry}
        onChange={onDraw}
        onCommit={onCommit}
        derived={derived ?? undefined}
        layers={layers}
        extrudeKey={extrudeKey}
      />
      <div className="w-full rail:w-[280px] rail:flex-none bg-sheet flex flex-col gap-4 p-4 rail:pl-4">
        <LayerControl layers={layers} onToggle={onToggleLayer} hasBasemap={Boolean(env.mapStyleUrl)} />
        <div className="pt-4 border-t border-hairline">
          <AreaReadout derived={deriving ? null : derived} />
        </div>
        <div className="pt-4 border-t border-hairline">
          <DensityLegend peak={peak} />
        </div>
        <DerivationNotes derived={derived} />
        <AdjacentWarning derived={derived} populated={adjacentPopulated} />
      </div>
    </div>
  );
}

function GroundStep({
  value,
  density,
  adjacentPopulated,
  busy,
  onChange,
  onDensity,
}: {
  value: GroundEnvironment | null;
  density: number | null;
  adjacentPopulated: boolean;
  busy: boolean;
  onChange: (v: GroundEnvironment) => void;
  onDensity: (density: number, adjacent: boolean) => void;
}) {
  const [entered, setEntered] = useState(density ?? 84);
  const [adjacent, setAdjacent] = useState(adjacentPopulated);

  return (
    <div className="flex flex-col gap-5 max-w-[720px]">
      <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
        {GROUND_OPTIONS.map((o) => (
          <RadioRow
            key={o.value}
            name="ground"
            checked={value === o.value}
            onChange={() => onChange(o.value)}
            title={o.title}
            body={o.body}
          />
        ))}
      </div>

      <div className="p-4 bg-sheet-well rounded-sm flex flex-col gap-3">
        <span className="t-micro text-ink-low">Peak population density in the buffer</span>
        <p className="m-0 t-cap text-ink-mid pretty">
          The density band is the iGRC row, so this number moves the determination. No
          population raster is bundled in this build — enter the figure you can evidence,
          and it is recorded with its source.
        </p>
        <div className="flex gap-2.5 flex-wrap items-end">
          <FieldLabel label="ppl/km²" className="flex-1 min-w-[140px]">
            <Input
              type="number"
              min={0}
              value={entered}
              onChange={(e) => setEntered(Number(e.target.value) || 0)}
              className="tnum"
            />
          </FieldLabel>
          <Button variant="secondary" disabled={busy} onClick={() => onDensity(entered, adjacent)}>
            {busy ? "Recording" : "Record"}
          </Button>
        </div>
        <label className="flex items-center gap-2.5 min-h-11 cursor-pointer">
          <input
            type="checkbox"
            checked={adjacent}
            onChange={(e) => setAdjacent(e.target.checked)}
            className="size-[18px]"
          />
          <span className="t-body-sm text-ink-mid pretty">
            People live or gather in the adjacent area, outside the ground risk buffer.
            The containment step takes this into account.
          </span>
        </label>
        {density !== null && (
          <span className="t-data-sm text-ink-hi tnum">
            Recorded: {density.toLocaleString("en-GB")} ppl/km²
          </span>
        )}
      </div>
    </div>
  );
}

function AirspaceStep({
  mission,
  altitude,
  onChange,
}: {
  mission: Mission;
  altitude: number;
  onChange: (patch: Record<string, unknown>) => void;
}) {
  const aboveBand = altitude > 152.4;
  const cls = (get(mission, "airspace_class") as AirspaceClass) ?? "g";
  const controlled = Boolean(get(mission, "controlled_airspace"));
  const aerodrome = Boolean(get(mission, "near_aerodrome"));
  const atypical = Boolean(get(mission, "atypical_airspace"));

  return (
    <div className="flex flex-col gap-5 max-w-[760px]">
      <div className="grid gap-5 grid-cols-[repeat(auto-fit,minmax(240px,1fr))]">
        <FieldLabel label="Airspace class">
          <Select value={cls} onChange={(e) => onChange({ airspace_class: e.target.value })}>
            {AIRSPACE_CLASSES.map((c) => (
              <option key={c} value={c}>
                {c.toUpperCase()}
                {c === "g" ? " — uncontrolled" : ""}
              </option>
            ))}
          </Select>
        </FieldLabel>
        <div className="flex flex-col gap-2">
          <span className="t-micro text-ink-low">Altitude band</span>
          <div className="min-h-11 px-3 flex items-center bg-sheet-well rounded-sm">
            <span className="t-data-13 text-ink-hi">
              {aboveBand ? "Above 500 ft (152 m) AGL" : "At or below 500 ft (152 m) AGL"}
            </span>
          </div>
          <span className="t-cap text-ink-low">
            Derived from the altitude at step 2. The engine computes it from the
            transcribed threshold, so it cannot disagree with the determination.
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
        <Checkbox
          checked={controlled}
          onChange={(v) => onChange({ controlled_airspace: v })}
          title="Controlled airspace"
          body="A CTR, TMA or any class A–E volume. Above 500 ft this reaches ARC d."
        />
        <Checkbox
          checked={aerodrome}
          onChange={(v) => onChange({ near_aerodrome: v })}
          title="Inside the aerodrome environment"
          body="Confirm against your national definition — proximity alone is not the same thing. In the aerodrome environment, class B, C or D reaches ARC d."
        />
        <Checkbox
          checked={atypical}
          onChange={(v) => onChange({ atypical_airspace: v })}
          title="Atypical or segregated airspace"
          body="A reserved or danger area where other traffic is excluded. This short-circuits the air risk tree to ARC a."
        />
      </div>
    </div>
  );
}

function Checkbox({
  checked,
  onChange,
  title,
  body,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  title: string;
  body: string;
}) {
  return (
    <label className="bg-sheet-well hover:bg-sheet-raised tr-ui p-4 flex gap-3 items-start cursor-pointer min-h-11">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-[18px] flex-none mt-[3px]"
      />
      <span>
        <span className="block t-data text-[14px] font-semibold leading-[1.3] text-ink-hi">
          {title}
        </span>
        <span className="block mt-1 t-cap text-ink-mid pretty">{body}</span>
      </span>
    </label>
  );
}

function MitigationsStep({
  mission,
  fitted,
  onChange,
}: {
  mission: Mission;
  fitted: string[];
  onChange: (kind: string, level: Robustness) => void;
}) {
  const claims = (get(mission, "mitigations") as Record<string, Robustness>) ?? {};
  return (
    <div className="flex flex-col gap-4">
      <p className="m-0 t-body-sm text-ink-mid max-w-[64ch] pretty">
        A mitigation lowers the risk class only if you can evidence it at the robustness
        you claim. The engine refuses a level the SORA table does not offer, so a greyed
        out button and a refused determination mean the same thing.
      </p>
      <div className="grid gap-sheet bg-hairline border border-hairline grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
        {MITIGATIONS.map((spec) => (
          <MitigationCard
            key={spec.kind}
            spec={spec}
            value={claims[spec.kind] ?? "none"}
            fitted={fitted}
            onChange={(level) => onChange(spec.kind, level)}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewStep({
  mission,
  drone,
  derived,
  pendingCount,
  missing,
  running,
  staged,
  error,
  limit,
  canRun,
  onRun,
  onGo,
}: {
  mission: Mission;
  drone: Drone | undefined;
  derived: GeoDerive | null;
  pendingCount: number;
  missing: string[];
  running: boolean;
  staged: ReturnType<typeof useStagedRun>;
  error: string | null;
  limit: ApiError | null;
  canRun: boolean;
  onRun: () => void;
  onGo: (s: StepKey) => void;
}) {
  const claims = (get(mission, "mitigations") as Record<string, Robustness>) ?? {};
  const claimed = Object.entries(claims)
    .filter(([, v]) => v && v !== "none")
    .map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`)
    .join(" · ");
  const altitude = Number(get(mission, "volume.max_altitude_agl_m") ?? 0);

  const rows: [string, string, StepKey][] = [
    ["Aircraft", drone ? `${drone.name}${drone.registration ? ` · ${drone.registration}` : ""}` : "—", "aircraft"],
    [
      "Operation",
      `${String(get(mission, "operation_type") ?? "—").toUpperCase()} · ${altitude || "—"} m AGL`,
      "operation",
    ],
    [
      "Flight geography",
      derived ? `${derived.flight_geography_km2.toFixed(2)} km² drawn` : get(mission, "volume.flight_geography") ? "drawn" : "—",
      "map",
    ],
    [
      "Ground environment",
      `${String(get(mission, "ground_environment") ?? "—").replace(/_/g, " ")}${
        get(mission, "population_density_per_km2") ? ` · ${Number(get(mission, "population_density_per_km2")).toLocaleString("en-GB")} ppl/km²` : ""
      }`,
      "ground",
    ],
    [
      "Airspace",
      `Class ${String(get(mission, "airspace_class") ?? "—").toUpperCase()}${
        get(mission, "near_aerodrome") ? " · aerodrome environment" : ""
      }${get(mission, "atypical_airspace") ? " · atypical" : ""}`,
      "airspace",
    ],
    ["Mitigations", claimed || "none claimed", "mitigations"],
  ];

  return (
    <div className="flex flex-col gap-4 max-w-[760px]">
      <p className="m-0 t-body-sm text-ink-mid pretty">
        <strong className="text-ink-hi font-semibold">Nothing below has reached the engine.</strong>{" "}
        Confirm each fact, or correct it, before the determination runs.
      </p>

      <div className="flex flex-col gap-sheet bg-hairline border border-hairline">
        {rows.map(([label, value, step]) => (
          <button
            key={label}
            type="button"
            onClick={() => onGo(step)}
            className="bg-sheet-well hover:bg-sheet-raised tr-ui px-4 py-3.5 min-h-11 flex justify-between items-center gap-4 border-0 text-left"
          >
            <span className="t-body-sm text-ink-mid">{label}</span>
            <span className="t-data-13 text-ink-hi text-right">{value}</span>
          </button>
        ))}
      </div>

      {missing.length > 0 && (
        <div role="status" className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
          <span className="t-micro-10 text-sail-3">Not yet complete</span>
          <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">
            Still needed: {missing.join(", ")}.
          </p>
        </div>
      )}

      {pendingCount > 0 && (
        <div role="status" className="p-3 bg-sheet-well border-l-[3px] border-sail-3 rounded-sm">
          <span className="t-micro-10 text-sail-3">
            {pendingCount} fact{pendingCount === 1 ? "" : "s"} unconfirmed
          </span>
          <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">
            Confirm or reject every extracted fact in the panel. The engine will not run
            on a fact nobody has agreed to.
          </p>
        </div>
      )}

      {limit && <PlanLimit error={limit} />}

      {error && (
        <div role="alert" className="p-3 bg-sheet-well border-l-[3px] border-sail-6 rounded-sm">
          <span className="t-micro-10 text-sail-6">The determination did not run</span>
          <p className="m-0 mt-1.5 t-cap text-ink-mid pretty">{error}</p>
        </div>
      )}

      {running ? (
        <div className="p-4 bg-sheet-well rounded-sm">
          <ComputationProgress {...staged} />
        </div>
      ) : (
        <Button size="lg" disabled={!canRun} onClick={onRun}>
          Run determination
        </Button>
      )}

      <div className="pt-4 border-t border-hairline flex flex-col gap-3">
        <RulebaseStamp />
        <Disclaimer />
      </div>
    </div>
  );
}
