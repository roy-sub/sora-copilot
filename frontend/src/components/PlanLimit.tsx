"use client";

/**
 * The 402. One component, everywhere a plan limit can stop a request.
 *
 * Rendered from the problem's fields — feature, limit, used, upgrade_to — rather than
 * from its prose, so the number in the sentence and the number in the meter cannot
 * disagree. The tone is deliberately flat: being stopped by a limit is not an error the
 * operator made, and a product that shouts at the moment it asks for money is a product
 * people resent paying.
 */

import { ApiError } from "@/lib/api";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useCheckout } from "@/lib/hooks";
import type { PlanName } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  per_dossier: "Per dossier",
  pro: "Pro",
  team: "Team",
  consultancy: "Consultancy",
};

/** Whether an error is a plan refusal, narrowed so callers can render this panel. */
export function isPlanLimit(error: unknown): error is ApiError {
  return error instanceof ApiError && error.isPlanLimit;
}

export interface PlanLimitProps {
  error: ApiError;
  /** Set when the surrounding screen already explains the feature. */
  compact?: boolean;
  className?: string;
}

export function PlanLimit({ error, compact, className }: PlanLimitProps) {
  const p = error.problem;
  const checkout = useCheckout();
  const upgrade = (p.upgrade_to ?? null) as PlanName | null;
  const buyable = upgrade === "pro" || upgrade === "team" || upgrade === "per_dossier";
  const hasMeter = typeof p.limit === "number" && p.limit > 0 && typeof p.used === "number";

  return (
    <div
      className={cn(
        "bg-sheet-well rounded-sm border-l-[3px] border-accent flex flex-col gap-3",
        compact ? "p-4" : "p-5",
        className,
      )}
      role="status"
    >
      <div className="flex flex-col gap-1">
        <span className="t-micro-10 text-ink-low">
          {PLAN_LABEL[p.plan ?? "free"] ?? p.plan} plan
        </span>
        <span className={compact ? "t-data-13 text-ink-hi" : "t-h3 text-ink-hi"}>{p.title}</span>
      </div>

      {hasMeter && (
        <div className="flex flex-col gap-1.5" aria-hidden>
          <div className="h-[6px] bg-sheet-alt overflow-hidden rounded-sm">
            <div
              className="h-full bg-accent"
              style={{ width: `${Math.min(100, ((p.used ?? 0) / (p.limit || 1)) * 100)}%` }}
            />
          </div>
          <span className="t-data-sm text-ink-low tnum">
            {p.used} of {p.limit} used
          </span>
        </div>
      )}

      {p.detail && <p className="m-0 t-body-sm text-ink-mid pretty">{p.detail}</p>}

      <div className="flex flex-wrap gap-2.5">
        {buyable ? (
          <Button
            onClick={() => checkout.mutate(upgrade)}
            disabled={checkout.isPending}
          >
            {checkout.isPending
              ? "Opening Stripe…"
              : upgrade === "per_dossier"
                ? "Buy one dossier"
                : `Move to ${PLAN_LABEL[upgrade]}`}
          </Button>
        ) : null}
        <ButtonLink href="/pricing" variant="secondary">
          Compare plans
        </ButtonLink>
      </div>

      {checkout.isError && (
        <span className="t-cap text-sail-5 pretty">
          {checkout.error instanceof ApiError
            ? (checkout.error.problem.detail ?? checkout.error.problem.title)
            : "Stripe could not be reached. Nothing has been charged."}
        </span>
      )}
    </div>
  );
}

/**
 * The inline form: one line and a link, for a place where a panel would be too much —
 * a disabled button's helper text, a sidebar.
 */
export function PlanLimitLine({ error }: { error: ApiError }) {
  const p = error.problem;
  return (
    <span className="t-cap text-ink-mid pretty">
      {p.title}.{" "}
      <a className="text-accent underline underline-offset-2" href="/pricing">
        {p.upgrade_to ? `Available on ${PLAN_LABEL[p.upgrade_to] ?? p.upgrade_to}` : "See plans"}
      </a>
    </span>
  );
}
