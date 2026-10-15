"use client";

/**
 * Plan, usage and the two buttons that leave for Stripe.
 *
 * The usage meters are the point of this panel. A compliance tool is bought once and
 * used in bursts, so "9 of 10 determinations this month" has to be visible before the
 * tenth, not after it. Every number comes from the backend's own count — the same count
 * the gate reads when it refuses — so the panel cannot flatter the plan.
 */

import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { useBilling, useBillingPortal, useCheckout } from "@/lib/hooks";
import type { BillingState, PlanName, PlanSummary } from "@/lib/api-client";
import { cn } from "@/lib/cn";

/** Usage key → the label and the limit it is measured against. */
const METERS: { key: string; label: string; limit: (p: PlanSummary["limits"]) => number | null | undefined }[] = [
  { key: "operations", label: "Operations", limit: (l) => l.operations },
  { key: "drones", label: "Aircraft", limit: (l) => l.drones },
  {
    key: "determinations_this_month",
    label: "Determinations this month",
    limit: (l) => l.determinations_per_month,
  },
  { key: "dossiers_this_month", label: "Dossiers this month", limit: (l) => l.dossiers_per_month },
  { key: "evidence", label: "Evidence files", limit: (l) => l.evidence_files },
  { key: "seats", label: "Seats", limit: (l) => l.seats },
];

function Meter({ label, used, limit }: { label: string; used: number; limit: number | null | undefined }) {
  const unlimited = limit === null || limit === undefined;
  const excluded = limit === 0;
  // A limit of one has nothing to meter: a full bar for the only seat a single-seat
  // plan has reads as an alarm about the normal state.
  const meterable = !unlimited && !excluded && limit > 1;
  const ratio = meterable ? Math.min(1, used / limit) : 0;
  // Colour is never the only signal: the count is always written out.
  const tone = ratio >= 1 ? "bg-sail-5" : ratio >= 0.8 ? "bg-sail-3" : "bg-accent";

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-baseline gap-3">
        <span className="t-data-sm text-ink-mid">{label}</span>
        <span className="t-data-sm text-ink-hi tnum">
          {excluded ? "not included" : unlimited ? `${used} · no limit` : `${used} / ${limit}`}
        </span>
      </div>
      {meterable && (
        <div className="h-[5px] bg-sheet-alt overflow-hidden rounded-sm" aria-hidden>
          <div className={cn("h-full", tone)} style={{ width: `${ratio * 100}%` }} />
        </div>
      )}
    </div>
  );
}

function PlanCard({
  plan,
  current,
  canManage,
  onBuy,
  pending,
}: {
  plan: PlanSummary;
  current: boolean;
  canManage: boolean;
  onBuy: (p: PlanName) => void;
  pending: boolean;
}) {
  const buyable = plan.purchasable && !current && canManage;
  return (
    <div
      className={cn(
        "p-4 flex flex-col gap-2.5 bg-sheet-well",
        current && "border-l-[3px] border-accent",
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="t-data-13 text-ink-hi">{plan.label}</span>
        <span className="t-data-sm text-ink-low">{plan.price_label}</span>
      </div>
      <span className="t-cap text-ink-low">
        {plan.limits.counterfactuals ? "Counterfactual advisor" : "No counterfactual advisor"}
        {" · "}
        {plan.limits.uses_dossier_credits
          ? "dossiers by credit"
          : plan.limits.dossiers_per_month === 0
            ? "no dossier export"
            : "unlimited dossiers"}
      </span>
      {current ? (
        <span className="t-micro-10 text-accent">Current plan</span>
      ) : buyable ? (
        <Button variant="secondary" onClick={() => onBuy(plan.name)} disabled={pending}>
          {plan.name === "per_dossier" ? "Buy one" : `Move to ${plan.label}`}
        </Button>
      ) : plan.name === "free" ? (
        // The free plan is never "purchasable"; saying so would read as a fault.
        <span className="t-cap text-ink-low">What every account starts on</span>
      ) : (
        <span className="t-cap text-ink-low">
          {!plan.purchasable ? "Not available on this deployment" : "Ask an owner"}
        </span>
      )}
    </div>
  );
}

export function BillingPanel() {
  const { data, isLoading, isError, error } = useBilling();
  const checkout = useCheckout();
  const portal = useBillingPortal();

  if (isLoading) {
    return (
      <section className="bg-sheet-well p-5 flex flex-col gap-3.5" aria-busy>
        <span className="t-micro text-ink-low">Plan</span>
        {[1, 0.6, 0.35].map((o, i) => (
          <div key={i} className="h-10 bg-sheet-alt" style={{ opacity: o }} />
        ))}
      </section>
    );
  }

  if (isError || !data) {
    return (
      <section className="bg-sheet-well p-5 flex flex-col gap-2">
        <span className="t-micro text-ink-low">Plan</span>
        <p className="m-0 t-body-sm text-ink-mid pretty">
          {error instanceof ApiError
            ? (error.problem.detail ?? error.problem.title)
            : "The plan could not be read. Your work is unaffected."}
        </p>
      </section>
    );
  }

  const state: BillingState = data;
  const limits = state.plan.limits;

  return (
    <section className="bg-sheet-well p-5 flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="t-micro text-ink-low">Plan</span>
        {state.status && (
          <span className="t-micro-10 text-ink-low">
            {state.status.replace("_", " ")}
            {state.cancel_at_period_end ? " · ends at period end" : ""}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="t-h2 text-ink-hi">{state.plan.label}</span>
        <span className="t-data-sm text-ink-low">{state.plan.price_label}</span>
      </div>

      {limits.uses_dossier_credits || state.dossier_credits > 0 ? (
        <div className="px-3.5 py-2.5 bg-sheet-alt rounded-sm flex justify-between gap-3 t-data-sm">
          <span className="text-ink-mid">Dossier credits</span>
          <span className="text-ink-hi tnum">{state.dossier_credits}</span>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 pt-3 border-t border-hairline">
        {METERS.filter((m) => m.key in state.usage).map((m) => (
          <Meter key={m.key} label={m.label} used={state.usage[m.key] ?? 0} limit={m.limit(limits)} />
        ))}
      </div>

      {state.current_period_end && (
        <span className="t-cap text-ink-low tnum">
          Renews {new Date(state.current_period_end).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </span>
      )}

      {!state.billing_configured ? (
        <p className="m-0 t-cap text-ink-mid pretty">
          Payments are not configured on this deployment, so nothing can be bought here.
          The plan is whatever the database says it is. See the Third Party Setup Guide in docs/.
        </p>
      ) : (
        <>
          <div className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(170px,1fr))] bg-hairline border border-hairline">
            {state.plans.map((p) => (
              <PlanCard
                key={p.name}
                plan={p}
                current={p.name === state.plan.name}
                canManage={state.can_manage}
                onBuy={(name) => checkout.mutate(name)}
                pending={checkout.isPending}
              />
            ))}
          </div>
          <div className="flex gap-2.5 flex-wrap">
            {state.portal_available && state.can_manage && (
              <Button
                variant="secondary"
                onClick={() => portal.mutate()}
                disabled={portal.isPending}
              >
                {portal.isPending ? "Opening Stripe…" : "Manage payment and invoices"}
              </Button>
            )}
          </div>
          {!state.can_manage && (
            <span className="t-cap text-ink-low pretty">
              Only an owner or admin of this organisation can change the plan.
            </span>
          )}
          {(checkout.isError || portal.isError) && (
            <span className="t-cap text-sail-5 pretty">
              {(() => {
                const e = checkout.error ?? portal.error;
                return e instanceof ApiError
                  ? (e.problem.detail ?? e.problem.title)
                  : "Stripe could not be reached. Nothing has been charged.";
              })()}
            </span>
          )}
        </>
      )}
    </section>
  );
}
