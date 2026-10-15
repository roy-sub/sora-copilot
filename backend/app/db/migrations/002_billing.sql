-- 002_billing.sql — Stripe subscriptions, dossier credits, and the webhook's idempotency log.
--
-- Build spec §12 phase 8. Apply after 001. Never edit this file once it has been applied.
--
-- Two things here exist because Stripe is an external system that will, eventually, send
-- the same event twice and send events out of order:
--
--   * `stripe_events` records every event id the webhook has already applied, so a
--     redelivery is a no-op rather than a second month of credits.
--   * `subscriptions.current_period_end` and the event's timestamp let a late-arriving
--     older event be discarded instead of overwriting newer state.
--
-- Plan state lives on `orgs.plan` (001) and is the only thing the request path reads.
-- `subscriptions` is the record of *why* the plan is what it is.

-- ---------------------------------------------------------------- orgs: credits

alter table public.orgs
  add column if not exists dossier_credits integer not null default 0
      check (dossier_credits >= 0),
  add column if not exists stripe_subscription_id text,
  -- When the current paid period ends. Null on free. The request path does not read it:
  -- a lapsed subscription is downgraded by the webhook, not by a clock in the API.
  add column if not exists plan_period_end timestamptz;

-- ---------------------------------------------------------------- subscriptions

create table if not exists public.subscriptions (
  id                      uuid primary key default gen_random_uuid(),
  org_id                  uuid not null references public.orgs(id) on delete cascade,
  stripe_subscription_id  text not null unique,
  stripe_customer_id      text not null,
  stripe_price_id         text not null,
  plan                    text not null
                          check (plan in ('free','pro','team','consultancy','per_dossier')),
  status                  text not null
                          check (status in ('trialing','active','past_due','canceled',
                                            'incomplete','incomplete_expired','unpaid','paused')),
  current_period_end      timestamptz,
  cancel_at_period_end    boolean not null default false,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);
create index if not exists subscriptions_org_idx on public.subscriptions(org_id);

drop trigger if exists subscriptions_touch on public.subscriptions;
create trigger subscriptions_touch before update on public.subscriptions
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- the webhook's memory

create table if not exists public.stripe_events (
  id            text primary key,          -- Stripe's own event id, e.g. evt_...
  type          text not null,
  org_id        uuid references public.orgs(id) on delete set null,
  -- Stripe's `created`, so an event that arrives after a newer one can be recognised.
  event_created timestamptz,
  payload       jsonb,
  applied_at    timestamptz not null default now()
);
create index if not exists stripe_events_org_idx on public.stripe_events(org_id, applied_at desc);

-- ---------------------------------------------------------------- dossier purchases

-- One row per credit bought, so the ledger explains a balance rather than only stating it.
create table if not exists public.dossier_purchases (
  id                     uuid primary key default gen_random_uuid(),
  org_id                 uuid not null references public.orgs(id) on delete cascade,
  stripe_session_id      text not null unique,
  stripe_payment_intent  text,
  credits                integer not null check (credits > 0),
  amount_cents           integer,
  currency               text,
  created_at             timestamptz not null default now()
);
create index if not exists dossier_purchases_org_idx on public.dossier_purchases(org_id, created_at desc);

-- ---------------------------------------------------------------- RLS

do $$
declare t text;
begin
  foreach t in array array['subscriptions','stripe_events','dossier_purchases']
  loop
    execute format('alter table public.%I enable row level security;', t);
    execute format('alter table public.%I force row level security;', t);
  end loop;
end $$;

-- Members may read their own billing records. Nobody writes them from the browser: only
-- the webhook does, through the service-role key, which bypasses RLS by design.
do $$
declare t text;
begin
  foreach t in array array['subscriptions','dossier_purchases']
  loop
    execute format('drop policy if exists %1$s_org_read on public.%1$s;', t);
    execute format(
      'create policy %1$s_org_read on public.%1$s for select
         using (org_id in (select public.current_user_org_ids()));', t);
  end loop;
end $$;

-- stripe_events gets no policy at all: it holds raw provider payloads and is for the
-- server only. With RLS forced and no policy, a browser session sees nothing.
