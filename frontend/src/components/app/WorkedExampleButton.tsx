"use client";

/**
 * "Show me a worked example" — the fastest way to understand what this product does.
 *
 * It does not open a tour or a video. It builds a real operation in the operator's own
 * organisation, runs it through the engine, and lands them on the verdict with a live
 * derivation tree. Everything they see from that point is their own data, editable and
 * deletable, which is both more honest and more useful than a showroom.
 *
 * The button says what it will cost, because it does cost: an operation and a
 * determination against the plan, like drawing one by hand.
 */

import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/Toast";
import { PlanLimit, isPlanLimit } from "@/components/PlanLimit";
import { useSeedWorkedExample } from "@/lib/hooks";
import { useEffect, useRef, useState } from "react";

/**
 * Honours `/app/?example=1`, which the marketing CTAs point at.
 *
 * Read after mount rather than through `useSearchParams`: under a static export that
 * hook forces a Suspense boundary whose fallback differs from the hydrated page, which
 * React reports as a hydration mismatch. The param is only needed once, so an effect
 * is both simpler and correct.
 */
export function useExampleRequestedByUrl(onRequested: () => void): void {
  const fired = useRef(false);
  useEffect(() => {
    if (fired.current) return;
    if (new URLSearchParams(window.location.search).get("example") !== "1") return;
    fired.current = true;
    // Drop the param so a refresh does not try to seed a second time.
    window.history.replaceState(null, "", window.location.pathname);
    onRequested();
  }, [onRequested]);
}


export function WorkedExampleButton({
  variant = "secondary",
  size,
}: {
  variant?: "primary" | "secondary";
  size?: "lg";
}) {
  const router = useRouter();
  const { push } = useToast();
  const seed = useSeedWorkedExample();
  const [limit, setLimit] = useState<ApiError | null>(null);

  return (
    <div className="flex flex-col gap-3 items-start">
      <Button
        variant={variant}
        size={size}
        disabled={seed.isPending}
        onClick={() => {
          setLimit(null);
          seed.mutate(undefined, {
            onSuccess: (operation) => {
              router.push(`/app/operations/view/?id=${encodeURIComponent(operation.id)}`);
            },
            onError: (e) => {
              if (isPlanLimit(e)) {
                setLimit(e);
                return;
              }
              push({
                tone: "fail",
                text:
                  e instanceof ApiError
                    ? (e.problem.detail ?? e.problem.title)
                    : "The worked example could not be built.",
              });
            },
          });
        }}
      >
        {seed.isPending ? "Running the engine…" : "Show me a worked example"}
      </Button>
      {limit && <PlanLimit error={limit} compact />}
    </div>
  );
}
