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
