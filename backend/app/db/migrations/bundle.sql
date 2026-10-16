-- ---------------------------------------------------------------------------
-- SORA Copilot — the whole schema, in one paste.
--
-- GENERATED FILE. Do not edit: `cd backend && make bundle` rewrites it from
-- app/db/migrations/*.sql, and a test fails if the two disagree.
--
-- Supabase dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
-- It is wrapped in a transaction, so it either lands completely or not at all.
--
-- Safe to run on an empty database, and safe to run again: every create is
-- guarded, and each policy and trigger is dropped if it exists before being
-- created. Verified by running the whole set twice against a Postgres 16.
-- The ledger it writes at the end is what lets a later `make migrate` see that
-- these files have already been applied.
--
-- Bundled, in order:
--   001_init.sql
--   002_billing.sql
--   003_invites.sql
--   004_rulebase_rc2.sql
--   005_rulebase_2_5_1.sql
-- ---------------------------------------------------------------------------

begin;

-- ===========================================================================
-- 001_init.sql
-- ===========================================================================

-- 001_init.sql — SORA Copilot initial schema.
--
-- Build spec §8. Apply through the Supabase SQL editor or `supabase db push`.
-- Migrations are numbered and never edited once applied; corrections land as 002, 003.
--
-- RLS is defence-in-depth here, not the authorisation gate. The backend holds the
-- service-role key, which bypasses RLS by design, and org scoping is enforced in
-- app/deps.py from the verified JWT. RLS covers every table so that any future direct
-- browser access is safe. See docs/ARCHITECTURE.md.

create extension if not exists postgis;
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- helpers

create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------- orgs

create table if not exists public.orgs (
  id                  uuid primary key default gen_random_uuid(),
  name                text not null,
  country             text not null default 'AT' check (country in ('AT','DE','EU')),
  plan                text not null default 'free'
                      check (plan in ('free','pro','team','consultancy','per_dossier')),
  stripe_customer_id  text,
  data_region         text not null default 'frankfurt'
                      check (data_region in ('frankfurt','dublin')),
  -- Pinning keeps determinations reproducible while an application is open with the
  -- authority. Null means "always use the current rulebase".
  rulebase_pin        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

create table if not exists public.org_members (
  org_id     uuid not null references public.orgs(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null default 'member' check (role in ('owner','admin','member')),
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);
create index if not exists org_members_user_idx on public.org_members(user_id);

-- ---------------------------------------------------------------- fleet

create table if not exists public.drones (
  id                 uuid primary key default gen_random_uuid(),
  org_id             uuid not null references public.orgs(id) on delete cascade,
  name               text not null,
  registration       text,
  max_dimension_m    double precision not null check (max_dimension_m > 0),
  mtom_kg            double precision not null check (mtom_kg > 0),
  cruise_speed_ms    double precision not null check (cruise_speed_ms >= 0),
  max_speed_ms       double precision not null check (max_speed_ms > 0),
  -- Half m v squared at max speed. Generated, so it can never drift from the inputs.
  kinetic_energy_j   double precision
                     generated always as (0.5 * mtom_kg * max_speed_ms * max_speed_ms) stored,
  fitted_mitigations jsonb not null default '[]'::jsonb,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create index if not exists drones_org_idx on public.drones(org_id);

-- ---------------------------------------------------------------- operations

create table if not exists public.operations (
  id                  uuid primary key default gen_random_uuid(),
  org_id              uuid not null references public.orgs(id) on delete cascade,
  drone_id            uuid references public.drones(id) on delete set null,
  name                text not null,
  site                text,
  status              text not null default 'draft'
                      check (status in ('draft','determined','dossier_ready','submitted','authorised')),
  -- The wizard's working state and the confirmed Mission, as the domain model shapes it.
  mission             jsonb not null default '{}'::jsonb,
  flight_geography    geography(Polygon,4326),
  contingency_volume  geography(Polygon,4326),
  ground_risk_buffer  geography(Polygon,4326),
  created_by          uuid references auth.users(id) on delete set null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index if not exists operations_org_idx on public.operations(org_id);
create index if not exists operations_fg_gix on public.operations using gist (flight_geography);

-- ---------------------------------------------------------------- the LLM boundary

-- A proposed fact is inert. It reaches the engine only after an explicit user action
-- flips status to 'confirmed' (build spec §4). There is no code path from pending to
-- the engine, and this table is where that boundary is recorded.
create table if not exists public.proposed_facts (
  id           uuid primary key default gen_random_uuid(),
  operation_id uuid not null references public.operations(id) on delete cascade,
  field        text not null,
  value        jsonb not null,
  confidence   double precision check (confidence >= 0 and confidence <= 1),
  source_span  text,
  status       text not null default 'pending' check (status in ('pending','confirmed','rejected')),
  confirmed_by uuid references auth.users(id) on delete set null,
  confirmed_at timestamptz,
  created_at   timestamptz not null default now(),
  -- A confirmed or rejected fact must say who did it and when.
  constraint proposed_facts_decision_is_attributed check (
    status = 'pending' or (confirmed_by is not null and confirmed_at is not null)
  )
);
create index if not exists proposed_facts_operation_idx on public.proposed_facts(operation_id, status);

-- ---------------------------------------------------------------- geo

create table if not exists public.geo_facts (
  id                 uuid primary key default gen_random_uuid(),
  operation_id       uuid not null references public.operations(id) on delete cascade,
  density_per_km2    double precision,
  density_band       text,
  -- Pinned so a determination stays reproducible when the raster is updated.
  raster_version     text not null,
  airspace_snapshot  jsonb not null default '{}'::jsonb,
  -- True when the operator overrode the sampled value, which they are always offered.
  operator_override  boolean not null default false,
  sampled_at         timestamptz not null default now()
);
create index if not exists geo_facts_operation_idx on public.geo_facts(operation_id);

-- ---------------------------------------------------------------- determinations

create table if not exists public.rulebase_versions (
  version     text primary key,
  released_at timestamptz not null default now(),
  changelog   text,
  sources     jsonb not null default '[]'::jsonb,
  -- False while any table behind the version is still transcribed from a seed.
  verified    boolean not null default false,
  is_current  boolean not null default false
);

-- Exactly one current rulebase version.
create unique index if not exists rulebase_versions_one_current
  on public.rulebase_versions ((is_current)) where is_current;

create table if not exists public.determinations (
  id             uuid primary key default gen_random_uuid(),
  operation_id   uuid not null references public.operations(id) on delete cascade,
  rulebase_version text not null references public.rulebase_versions(version),
  mission_hash   text not null,
  -- Nullable, and null ONLY for the certified category: an operation outside SORA has
  -- no intrinsic ground risk class, and 0 is not one. The check below enforces that the
  -- absence cannot appear on a specific-category determination.
  igrc           integer,
  final_grc      integer,
  initial_arc    text not null check (initial_arc in ('a','b','c','d')),
  residual_arc   text not null check (residual_arc in ('a','b','c','d')),
  sail           text not null
                 check (sail in ('I','II','III','IV','V','VI','certified_category')),
  tmpr           text not null default 'none' check (tmpr in ('none','low','medium','high')),
  containment    jsonb not null,
  osos           jsonb not null default '[]'::jsonb,
  -- A determination without a trace is a bug, not a degraded result.
  trace          jsonb not null,
  warnings       jsonb not null default '[]'::jsonb,
  computed_at    timestamptz not null default now(),
  constraint determinations_trace_is_present check (jsonb_array_length(trace) > 0),
  constraint determinations_risk_classes_present check (
    (sail = 'certified_category') or (igrc is not null and final_grc is not null)
  )
);
-- Idempotency: the same mission against the same rulebase is the same determination.
create unique index if not exists determinations_idempotent
  on public.determinations(operation_id, mission_hash, rulebase_version);

create table if not exists public.mitigations (
  id              uuid primary key default gen_random_uuid(),
  operation_id    uuid not null references public.operations(id) on delete cascade,
  kind            text not null check (kind in
                  ('m1_strategic','m1_ers','m2_impact','strategic_air','tactical_air')),
  robustness      text not null default 'none' check (robustness in ('none','low','medium','high')),
  evidence_status text not null default 'none'
                  check (evidence_status in ('none','claimed','documented','verified')),
  notes           text,
  created_at      timestamptz not null default now(),
  unique (operation_id, kind)
);

-- ---------------------------------------------------------------- evidence and dossiers

create table if not exists public.evidence_files (
  id            uuid primary key default gen_random_uuid(),
  operation_id  uuid not null references public.operations(id) on delete cascade,
  oso_id        text,
  mitigation_id uuid references public.mitigations(id) on delete set null,
  storage_path  text not null,
  filename      text not null,
  bytes         bigint check (bytes >= 0),
  content_type  text,
  uploaded_by   uuid references auth.users(id) on delete set null,
  uploaded_at   timestamptz not null default now(),
  constraint evidence_attaches_to_something check (oso_id is not null or mitigation_id is not null)
);
create index if not exists evidence_files_operation_idx on public.evidence_files(operation_id);

create table if not exists public.dossiers (
  id               uuid primary key default gen_random_uuid(),
  operation_id     uuid not null references public.operations(id) on delete cascade,
  determination_id uuid references public.determinations(id) on delete set null,
  version          integer not null check (version > 0),
  storage_path     text not null,
  format           text not null default 'docx' check (format in ('docx','pdf')),
  note             text,
  generated_at     timestamptz not null default now(),
  unique (operation_id, version, format)
);
create index if not exists dossiers_operation_idx on public.dossiers(operation_id);

-- ---------------------------------------------------------------- phase 7

create table if not exists public.impact_alerts (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references public.orgs(id) on delete cascade,
  operation_id    uuid references public.operations(id) on delete cascade,
  from_version    text,
  to_version      text,
  severity        text not null default 'info' check (severity in ('info','warning','critical')),
  summary         text not null,
  created_at      timestamptz not null default now(),
  acknowledged_at timestamptz
);
create index if not exists impact_alerts_org_idx on public.impact_alerts(org_id, acknowledged_at);

-- ---------------------------------------------------------------- LLM accounting

create table if not exists public.llm_calls (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.orgs(id) on delete cascade,
  purpose       text not null check (purpose in ('intake','dossier_prose','trace_explanation')),
  model         text not null,
  prompt_hash   text not null,
  input_tokens  integer not null default 0,
  output_tokens integer not null default 0,
  latency_ms    integer not null default 0,
  created_at    timestamptz not null default now()
);
create index if not exists llm_calls_org_month_idx on public.llm_calls(org_id, created_at desc);

-- ---------------------------------------------------------------- updated_at triggers

do $$
declare t text;
begin
  foreach t in array array['orgs','drones','operations']
  loop
    execute format(
      'drop trigger if exists touch_%1$s on public.%1$s;
       create trigger touch_%1$s before update on public.%1$s
       for each row execute function public.touch_updated_at();', t);
  end loop;
end $$;

-- ---------------------------------------------------------------- first sign-in

-- A new user gets an organisation and an owner membership, so the app never renders a
-- signed-in account with nowhere to put an operation.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare new_org uuid;
begin
  insert into public.orgs (name)
  values (coalesce(nullif(new.raw_user_meta_data->>'organisation', ''), 'My organisation'))
  returning id into new_org;

  insert into public.org_members (org_id, user_id, role) values (new_org, new.id, 'owner');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------- RLS

-- Org membership of the calling user. A SQL-bodied function is parsed when it is
-- created, so it has to be defined after org_members exists. STABLE and SECURITY
-- DEFINER so the policies below can use it without recursing into org_members' own
-- policy.
create or replace function public.current_user_org_ids() returns setof uuid
language sql stable security definer set search_path = public as $$
  select org_id from public.org_members where user_id = auth.uid();
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'orgs','org_members','drones','operations','proposed_facts','geo_facts',
    'determinations','mitigations','evidence_files','dossiers','impact_alerts','llm_calls'
  ]
  loop
    execute format('alter table public.%I enable row level security;', t);
    execute format('alter table public.%I force row level security;', t);
  end loop;
end $$;

-- orgs and org_members key on the membership set directly.
drop policy if exists orgs_member_read on public.orgs;
create policy orgs_member_read on public.orgs for select
  using (id in (select public.current_user_org_ids()));

drop policy if exists orgs_admin_write on public.orgs;
create policy orgs_admin_write on public.orgs for update
  using (id in (select org_id from public.org_members
                where user_id = auth.uid() and role in ('owner','admin')));

drop policy if exists org_members_self_read on public.org_members;
create policy org_members_self_read on public.org_members for select
  using (org_id in (select public.current_user_org_ids()));

-- Every org-scoped table takes the same policy: visible if the row's org is one of mine.
do $$
declare t text;
begin
  foreach t in array array['drones','operations','impact_alerts','llm_calls']
  loop
    execute format('drop policy if exists %1$s_org_all on public.%1$s;', t);
    execute format(
      'create policy %1$s_org_all on public.%1$s for all
         using (org_id in (select public.current_user_org_ids()))
         with check (org_id in (select public.current_user_org_ids()));', t);
  end loop;
end $$;

-- Operation-scoped tables reach the org through their operation.
do $$
declare t text;
begin
  foreach t in array array[
    'proposed_facts','geo_facts','determinations','mitigations','evidence_files','dossiers'
  ]
  loop
    execute format('drop policy if exists %1$s_org_all on public.%1$s;', t);
    execute format(
      'create policy %1$s_org_all on public.%1$s for all
         using (operation_id in (select id from public.operations
                where org_id in (select public.current_user_org_ids())))
         with check (operation_id in (select id from public.operations
                where org_id in (select public.current_user_org_ids())));', t);
  end loop;
end $$;

-- The rulebase is public reference data: readable by any signed-in user, written only
-- by the service role (which bypasses RLS).
drop policy if exists rulebase_read on public.rulebase_versions;
alter table public.rulebase_versions enable row level security;
create policy rulebase_read on public.rulebase_versions for select
  using (auth.role() = 'authenticated');

-- ---------------------------------------------------------------- storage buckets

insert into storage.buckets (id, name, public)
values ('evidence', 'evidence', false),
       ('dossiers', 'dossiers', false),
       ('public-assets', 'public-assets', true)
on conflict (id) do nothing;

-- Private buckets are reached only through signed URLs minted by the backend
-- (dossiers: 15-minute expiry, build spec §8), so no end-user storage policy is needed.

-- ---------------------------------------------------------------- seed the rulebase

insert into public.rulebase_versions (version, changelog, sources, verified, is_current)
values (
  '2.5.0-rc1',
  'Seed skeleton. No table verified against an official source — see PLAN.md §8.',
  '[]'::jsonb,
  false,
  true
)
on conflict (version) do nothing;

-- ===========================================================================
-- 002_billing.sql
-- ===========================================================================

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

-- ===========================================================================
-- 003_invites.sql
-- ===========================================================================

-- 003_invites.sql — organisation invitations, so a Team plan's seats can be used.
--
-- Apply after 002. Never edit this file once it has been applied.
--
-- An invitation is claimed by EMAIL, taken from a verified Supabase JWT, not by a secret
-- link in a message. That is a deliberate choice for a product with no email sender: the
-- owner invites an address, tells their colleague to sign up with it, and the first
-- sign-in joins the organisation instead of creating a new one. There is no token to
-- leak, forward or replay, and an invitation is only ever claimable by someone who has
-- proved control of that address to Supabase Auth.
--
-- The cost is that an invitation to the wrong address is claimable by whoever owns it,
-- which is why invitations expire and why revoking one is immediate.

-- The member's address, denormalised from auth.users at join time.
--
-- Without it the backend cannot list who is in an organisation: reading auth.users needs
-- the Auth admin API, and a settings screen that shows a column of UUIDs is useless. It
-- is a copy, so it can go stale if someone changes their address in Supabase Auth; that
-- is an accepted cost for not reaching into the auth schema from application code.
alter table public.org_members add column if not exists email text;

create table if not exists public.org_invites (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.orgs(id) on delete cascade,
  -- Stored lowercased; the API normalises before writing. The unique index below is what
  -- stops one address collecting two pending invitations to the same organisation.
  email       text not null check (email = lower(email) and position('@' in email) > 1),
  role        text not null default 'member' check (role in ('admin','member')),
  invited_by  uuid references auth.users(id) on delete set null,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null default (now() + interval '14 days'),
  -- Set when the invitation is claimed. A claimed invitation is kept, not deleted, so
  -- "who let this person in, and when" stays answerable.
  accepted_at timestamptz,
  accepted_by uuid references auth.users(id) on delete set null,
  check ((accepted_at is null) = (accepted_by is null))
);

create index if not exists org_invites_org_idx on public.org_invites(org_id, created_at desc);
-- Claiming is a lookup by email across organisations, so it needs its own index.
create index if not exists org_invites_email_idx on public.org_invites(email) where accepted_at is null;
-- One pending invitation per address per organisation. A second invite to the same
-- person is an update, not a duplicate row.
create unique index if not exists org_invites_pending_uq
  on public.org_invites(org_id, email) where accepted_at is null;

alter table public.org_invites enable row level security;
alter table public.org_invites force row level security;

-- Members may read their organisation's invitations. Writes go through the backend's
-- service-role key, which bypasses RLS: the authorisation gate is app/deps.py.
drop policy if exists org_invites_org_read on public.org_invites;
create policy org_invites_org_read on public.org_invites for select
  using (org_id in (select public.current_user_org_ids()));

-- ===========================================================================
-- 004_rulebase_rc2.sql
-- ===========================================================================

-- Rulebase 2.5.0-rc2: the first version with verified tables in it.
--
-- A new version is a new row, never an update of the old one. Determinations pin the
-- version they were computed against, so 2.5.0-rc1 has to keep existing and keep saying
-- what it was, or a record already in the database would start describing itself with
-- rules it was not computed under.
--
-- `verified` on the row stays false: it means "every table behind this version is
-- verified", and eight still are not. See app/engine/rulebase/sora_2_5/CHANGELOG.md.

-- Stand the current version down FIRST. `rulebase_versions_one_current` is a plain
-- unique index, checked at the end of each statement rather than at commit, so
-- inserting a second current row and standing the old one down afterwards fails on the
-- insert — which is what happened the first time this was run against a real database.
update public.rulebase_versions set is_current = false where is_current;

insert into public.rulebase_versions (version, changelog, sources, verified, is_current)
values (
  '2.5.0-rc2',
  'igrc, igrc_columns and sail verified against the JARUS SORA 2.5 Main Body release '
  '(JAR_doc_25), cross-checked with the Norwegian CAA SORA 2.5 calculator and JARUS '
  'Annex F. Every regulatory table records the EU adoption (EASA ED Decision '
  '2025/018/R). Eight tables remain seeds, each stating what it needs.',
  jsonb_build_array(
    jsonb_build_object(
      'title', 'JARUS SORA 2.5 Main Body, Release (JAR_doc_25)',
      'url',   'http://jarus-rpas.org/wp-content/uploads/2024/06/SORA-v2.5-Main-Body-Release-JAR_doc_25.pdf'),
    jsonb_build_object(
      'title', 'EASA ED Decision 2025/018/R of 30 September 2025 — AMC and GM to Regulation (EU) 2019/947, Issue 1 Amendment 4',
      'url',   'https://www.easa.europa.eu/en/document-library/agency-decisions'),
    jsonb_build_object(
      'title', 'Norwegian CAA SORA 2.5 calculator (authority implementation, used as corroboration)',
      'url',   'https://training.caa.no/SORA-2.5-calculator/')
  ),
  false,
  true
)
on conflict (version) do update set is_current = true;

-- ===========================================================================
-- 005_rulebase_2_5_1.sql
-- ===========================================================================

-- Rulebase 2.5.1: the first version with every table transcribed from the adopted text.
--
-- A new version is a new row, never an update of the old one. Determinations pin the
-- version they were computed against, and several of the corrections in this release
-- change a verdict, so 2.5.0-rc1 and -rc2 have to keep existing and keep saying what
-- they were — otherwise a stored record would start describing itself with rules it was
-- not computed under.
--
-- `verified` is true for the first time: every table behind this version names the
-- document, section and page it was transcribed from.

-- Stand the current version down FIRST; see the note in 004. The unique index is
-- checked per statement, so the insert cannot be the thing that creates the overlap.
update public.rulebase_versions set is_current = false where is_current;

insert into public.rulebase_versions (version, changelog, sources, verified, is_current)
values (
  '2.5.1',
  'Every table transcribed from the EASA Easy Access Rules for UAS, revision of June '
  '2026, which incorporates ED Decision 2025/018/R — the SORA 2.5 package as AMC and GM '
  'to Regulation (EU) 2019/947, Issue 1, Amendment 4. Seven of the eight unchecked '
  'tables were wrong: the ARC tree was missing the transponder-mandatory-zone and above-FL600 '
  'categories, the residual ARC was giving away a class for a claim rather than a '
  'demonstrated density, containment is six tables rather than one row, Table 5''s '
  'M1(B) mitigation was absent, OSO#04 was a level low at SAIL IV to VI, and the '
  'altitude band is 150 m rather than 152.4 m.',
  jsonb_build_array(
    jsonb_build_object(
      'title', 'EASA Easy Access Rules for Unmanned Aircraft Systems (Regulation (EU) 2019/947 and Regulation (EU) 2019/945), revision of June 2026',
      'url',   'https://www.easa.europa.eu/en/downloads/110913/en'),
    jsonb_build_object(
      'title', 'ED Decision 2025/018/R of 30 September 2025 — AMC and GM to Regulation (EU) 2019/947, Issue 1, Amendment 4',
      'url',   'https://www.easa.europa.eu/en/document-library/agency-decisions')
  ),
  true,
  true
)
on conflict (version) do update set is_current = true;



-- ---------------------------------------------------------------------------
-- The migration ledger.
--
-- `scripts/migrate.py` keeps this table so that re-running is a no-op. Pasting
-- the bundle has applied the same files, so they are recorded here too and the
-- two routes agree about what has run. RLS is enabled and forced with no
-- policy, because 001 establishes that for every table in `public` and a
-- bookkeeping table is not an excuse to break it; the backend holds the
-- service-role key and bypasses RLS.
-- ---------------------------------------------------------------------------

create table if not exists public.schema_migrations (
  filename   text primary key,
  sha256     text not null,
  applied_at timestamptz not null default now()
);
alter table public.schema_migrations enable row level security;
alter table public.schema_migrations force row level security;

insert into public.schema_migrations (filename, sha256) values
  ('001_init.sql', '3dd60a44554a1a2942320f0ab8eeaa1a3db1362e588cdb963931399ecb57bbfe'),
  ('002_billing.sql', 'a53877f05cc73c1f8c8ddbbc65665458787991541f224655f2fab0ebcd54b179'),
  ('003_invites.sql', 'd47e333c0a26e74c427558bc2ebd6c5b509fda385d774137384471abe8e9bd8b'),
  ('004_rulebase_rc2.sql', '6839ca06e14b41a29983902a9ab22777baa464c36e6fd8f19f8e6d538b6e56d8'),
  ('005_rulebase_2_5_1.sql', '946836f31b96d4d12b342441d7eebaf2ef865c450d6a8bf79aae1b2451e81239')
on conflict (filename) do nothing;

commit;
