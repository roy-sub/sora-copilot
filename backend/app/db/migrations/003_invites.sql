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
