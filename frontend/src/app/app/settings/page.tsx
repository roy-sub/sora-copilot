"use client";

/**
 * Settings: organisation, members, data region, rulebase pinning, appearance.
 *
 * Pinning is the consequential one. A pin keeps determinations reproducible while an
 * application is open with an authority, so changing it is shown as what it is — a
 * decision that affects every future run — behind a modal that names the determinations
 * involved.
 */

import { useState } from "react";
import { PageHeader } from "@/components/app/Shell";
import { BillingPanel } from "@/components/app/BillingPanel";
import { MembersPanel } from "@/components/app/MembersPanel";
import { Disclaimer, RulebaseStamp } from "@/components/Brand";
import { Button, ButtonLink } from "@/components/ui/Button";
import { FieldLabel, Input, Segmented, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Dialog";
import { useToast } from "@/components/Toast";
import { ApiError } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { useHealth, useOperations, useOrg, useRulebase, useUpdateOrg } from "@/lib/hooks";
import type { Country } from "@/lib/api-client";
import { cn } from "@/lib/cn";

const AUTHORITIES: { value: Country; label: string }[] = [
  { value: "AT", label: "Austro Control (AT)" },
  { value: "DE", label: "Luftfahrt-Bundesamt (DE)" },
  { value: "EU", label: "Another EU member state" },
];

export default function Settings() {
  const { push } = useToast();
  const { theme, setTheme } = usePrefs();
  const { data: org } = useOrg();
  const { data: rulebase } = useRulebase();
  const { data: health } = useHealth();
  const { data: operations = [] } = useOperations();
  const update = useUpdateOrg();

  const [name, setName] = useState<string | null>(null);
  const [registration, setRegistration] = useState<string | null>(null);
  const [pinModal, setPinModal] = useState(false);

  const save = (patch: Parameters<typeof update.mutate>[0]) =>
    update.mutate(patch, {
      onSuccess: () => push({ tone: "ok", text: "Saved" }),
      onError: (e) =>
        push({
          tone: "fail",
          text: e instanceof ApiError ? (e.problem.detail ?? e.problem.title) : "Could not save",
        }),
    });

  const pinned = Boolean(org?.rulebase_pin);
  const determined = operations.filter((o) => o.sail);

  return (
    <>
      <PageHeader title="Settings" />
      <main className="flex-1 bg-sheet p-4 md:p-6 flex flex-col gap-sheet">
        <div className="grid gap-sheet grid-cols-[repeat(auto-fit,minmax(300px,1fr))] bg-hairline border border-hairline">
          {/* ---------------------------------------------------------- organisation */}
          <section className="bg-sheet-well p-5 flex flex-col gap-3.5">
            <span className="t-micro text-ink-low">Organisation</span>
            <FieldLabel label="Legal name" quiet>
              <Input
                value={name ?? org?.name ?? ""}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => name !== null && name !== org?.name && save({ name })}
              />
            </FieldLabel>
            <FieldLabel label="Operator registration" quiet>
              <Input
                className="tnum"
                placeholder="AUT8j2kx91mfq"
                value={registration ?? ""}
                onChange={(e) => setRegistration(e.target.value)}
                onBlur={() =>
                  registration && save({ operator_registration: registration })
                }
              />
            </FieldLabel>
            <FieldLabel label="Competent authority" quiet>
              <Select
                value={org?.country ?? "AT"}
                onChange={(e) => save({ country: e.target.value as Country })}
              >
                {AUTHORITIES.map((a) => (
                  <option key={a.value} value={a.value}>
                    {a.label}
                  </option>
                ))}
              </Select>
            </FieldLabel>
            <span className="t-cap text-ink-low pretty">
              The authority appears on the dossier cover. It does not change the
              determination: no national annex has been transcribed yet, so every country
              uses the EU baseline and the trace says so.
            </span>
          </section>

          {/* ---------------------------------------------------------- plan */}
          <BillingPanel />

          {/* ---------------------------------------------------------- members */}
          <MembersPanel />

          {/* ---------------------------------------------------------- data region */}
          <section className="bg-sheet-well p-5 flex flex-col gap-3.5">
            <span className="t-micro text-ink-low">Data region</span>
            <Segmented
              label="Data region"
              value={org?.data_region ?? "frankfurt"}
              onChange={(v) => save({ data_region: v })}
              options={[
                { value: "frankfurt", label: "EU · Frankfurt" },
                { value: "dublin", label: "EU · Dublin" },
              ]}
            />
            <p className="m-0 t-cap text-ink-low pretty">
              Evidence files, mission data and generated dossiers stay in the selected
              region. This records your choice; the region a deployment actually uses is
              set when its database is created.
            </p>
            {health && !health.supabase_configured && (
              <span className="t-cap text-sail-3 pretty">
                This deployment has no database configured, so nothing is persisted
                between restarts.
              </span>
            )}
          </section>

          {/* ---------------------------------------------------------- rulebase */}
          <section className="bg-sheet-well p-5 flex flex-col gap-3.5">
            <span className="t-micro text-ink-low">Rulebase pinning</span>
            <div className="flex flex-col gap-sheet">
              <label className="flex items-center gap-2.5 min-h-11 cursor-pointer">
                <input
                  type="radio"
                  name="rulebase"
                  checked={pinned}
                  onChange={() => setPinModal(true)}
                  className="size-[18px]"
                />
                <span className="t-data-13 text-ink-hi">
                  Pin to {rulebase?.version ?? "the current rulebase"}
                </span>
              </label>
              <label className="flex items-center gap-2.5 min-h-11 cursor-pointer">
                <input
                  type="radio"
                  name="rulebase"
                  checked={!pinned}
                  onChange={() => save({ rulebase_pin: null })}
                  className="size-[18px]"
                />
                <span className="t-data-13 text-ink-mid">Always use the latest rulebase</span>
              </label>
            </div>
            <p className="m-0 t-cap text-ink-low pretty">
              Pinning keeps determinations reproducible while an application is open with
              the authority. Existing dossiers always keep the rulebase they were
              generated against, pinned or not.
            </p>
            <div className="pt-3 border-t border-hairline flex flex-col gap-2">
              <RulebaseStamp authoritative />
              {rulebase && !rulebase.verified && (
                <>
                  <span className="t-cap text-sail-3 pretty">
                    {rulebase.unverified_tables.length} of {rulebase.tables.length} tables
                    are still transcribed from seeds.
                  </span>
                  <details className="t-cap text-ink-mid">
                    <summary className="cursor-pointer min-h-11 flex items-center">
                      What is still needed
                    </summary>
                    <ul className="m-0 mt-2 p-0 pl-4 list-disc flex flex-col gap-1">
                      {rulebase.sources_needed.map((s) => (
                        <li key={s} className="pretty">
                          {s}
                        </li>
                      ))}
                    </ul>
                  </details>
                </>
              )}
            </div>
          </section>

          {/* ---------------------------------------------------------- appearance */}
          <section className="bg-sheet-well p-5 flex flex-col gap-3.5">
            <span className="t-micro text-ink-low">Appearance</span>
            <div className="flex gap-sheet border border-hairline-strong rounded-pill overflow-hidden self-start">
              {(["dark", "light"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  aria-pressed={theme === t}
                  onClick={() => setTheme(t)}
                  className={cn(
                    "min-h-11 px-5 border-0 t-micro-10 tr-ui",
                    theme === t ? "bg-accent text-accent-ink" : "bg-transparent text-ink-mid",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <p className="m-0 t-cap text-ink-low pretty">
              Dark is the default. Light is for printed review and bright field
              conditions. The page ground stays black in both; only the sheets flip.
            </p>
          </section>

          {/* ---------------------------------------------------------- diagnostics */}
          <section className="bg-sheet-well p-5 flex flex-col gap-3.5">
            <span className="t-micro text-ink-low">This deployment</span>
            <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 t-data-sm">
              <dt className="text-ink-mid">Environment</dt>
              <dd className="m-0 text-ink-hi">{health?.env ?? "—"}</dd>
              <dt className="text-ink-mid">Rulebase</dt>
              <dd className="m-0 text-ink-hi tnum">{health?.rulebase_version ?? "—"}</dd>
              <dt className="text-ink-mid">Build</dt>
              <dd className="m-0 text-ink-hi tnum">{health?.git_sha ?? "—"}</dd>
              <dt className="text-ink-mid">Database</dt>
              <dd className="m-0 text-ink-hi">
                {health?.supabase_configured ? "configured" : "in-memory"}
              </dd>
              <dt className="text-ink-mid">Intake model</dt>
              <dd className="m-0 text-ink-hi">
                {health?.anthropic_configured ? "configured" : "deterministic extractor"}
              </dd>
            </dl>
            <div className="flex gap-2.5 flex-wrap">
              <ButtonLink href="/app/states/" variant="secondary">
                System states
              </ButtonLink>
              <ButtonLink href="/app/overlays/" variant="secondary">
                Overlays
              </ButtonLink>
            </div>
          </section>
        </div>

        <div className="bg-sheet pt-5">
          <Disclaimer variant="footer" />
        </div>
      </main>

      <Modal
        open={pinModal}
        onOpenChange={setPinModal}
        title="Change the pinned rulebase?"
        description="Pinning fixes which rulebase future determinations run against."
      >
        <div className="flex flex-col gap-4">
          <p className="m-0 t-body-sm text-ink-mid pretty">
            Pinning to <strong className="text-ink-hi">{rulebase?.version}</strong> means
            every future run uses it, even after a newer rulebase is deployed. Existing
            determinations are unaffected: each is already pinned to the rulebase it was
            computed against.
          </p>
          {determined.length > 0 && (
            <div className="flex flex-col gap-sheet bg-hairline border border-hairline max-h-48 overflow-y-auto">
              {determined.map((o) => (
                <div
                  key={o.id}
                  className="bg-sheet-well px-3.5 py-2.5 flex justify-between gap-3 t-data-sm"
                >
                  <span className="text-ink-hi truncate">{o.name}</span>
                  <span className="text-ink-low tnum">
                    SAIL {o.sail} · {o.rulebase_version}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2.5 flex-wrap">
            <Button
              onClick={() => {
                save({ rulebase_pin: rulebase?.version ?? null });
                setPinModal(false);
              }}
            >
              Pin to {rulebase?.version}
            </Button>
            <Button variant="secondary" onClick={() => setPinModal(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
