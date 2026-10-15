"use client";

import { cn } from "@/lib/cn";

export type StepKey =
  | "aircraft"
  | "operation"
  | "map"
  | "ground"
  | "airspace"
  | "mitigations"
  | "review";

export const STEPS: { key: StepKey; label: string; title: string }[] = [
  { key: "aircraft", label: "Aircraft", title: "Select aircraft" },
  { key: "operation", label: "Operation", title: "Operation type and envelope" },
  { key: "map", label: "Map", title: "Flight geography" },
  { key: "ground", label: "Ground", title: "Ground environment" },
  { key: "airspace", label: "Airspace", title: "Airspace" },
  { key: "mitigations", label: "Mitigations", title: "Mitigations claimed" },
  { key: "review", label: "Review", title: "Review and confirm" },
];

export const stepIndex = (key: StepKey): number => STEPS.findIndex((s) => s.key === key);

/**
 * Seven ticks. Upcoming is a hairline ring, current is lime with the numeral in ink,
 * complete is a filled alt sheet — and steps past the furthest reached are disabled, so
 * the stepper is a map of where the operator has been rather than a free-for-all.
 */
export function WizardStepper({
  current,
  furthest,
  onGo,
}: {
  current: StepKey;
  furthest: StepKey;
  onGo: (k: StepKey) => void;
}) {
  const currentAt = stepIndex(current);
  const furthestAt = stepIndex(furthest);

  return (
    <nav
      aria-label="Wizard steps"
      className="bg-sheet px-3 flex items-center gap-sheet border-b border-hairline overflow-x-auto no-scrollbar flex-nowrap"
    >
      {STEPS.map((step, i) => {
        const isCurrent = i === currentAt;
        const isComplete = i < currentAt;
        const disabled = i > furthestAt;
        return (
          <button
            key={step.key}
            type="button"
            onClick={() => !disabled && onGo(step.key)}
            disabled={disabled}
            aria-current={isCurrent ? "step" : undefined}
            className={cn(
              "flex items-center gap-2 bg-transparent border-0 min-h-11 px-2.5 t-micro tracking-[.08em] whitespace-nowrap text-left tr-ui",
              isCurrent ? "text-ink-hi" : isComplete ? "text-ink-mid" : "text-ink-low",
              disabled && "opacity-35 cursor-not-allowed",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "flex items-center justify-center size-[22px] flex-none rounded-pill text-[10px] font-semibold leading-none",
                isCurrent
                  ? "bg-accent text-accent-ink"
                  : isComplete
                    ? "bg-sheet-alt text-ink-hi"
                    : "border border-hairline-strong text-ink-low",
              )}
            >
              {i + 1}
            </span>
            <span>{step.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
