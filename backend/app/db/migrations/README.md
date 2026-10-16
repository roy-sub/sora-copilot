# Migrations

Numbered SQL files, applied in order. **Never edit a migration that has been applied** —
corrections land as the next number, so a database can always be rebuilt by replaying
them from 001.

## Applying

```bash
cd backend
make migrate-status     # what would run; changes nothing
make migrate            # apply what is missing
```

`scripts/migrate.py` reads `DATABASE_URL` (the Postgres connection string from
Supabase → Connect → Session pooler, **not** `SUPABASE_URL`), keeps a ledger in
`public.schema_migrations`, and applies each pending file in its own transaction.

Re-running is a no-op, in two independent ways. The migrations are themselves
replayable — every `create` is `if not exists`, and each policy and trigger is dropped
`if exists` before it is created, verified by running the whole set twice against a
Postgres 16 — and the ledger means the runner skips them anyway. The ledger also stores
each file's SHA-256 and refuses to continue if an applied file has since been edited,
which is where the rule above stops being something a person has to remember.

For a database whose schema was already created by hand, `--baseline` records the files
as applied without running them.

**From the Supabase SQL editor**, with no connection string and no terminal: open
`bundle.sql` — the same migrations concatenated in order, wrapped in a transaction,
with the ledger rows at the end — paste the whole file, Run. `make bundle` regenerates
it and a test fails if the committed bundle has drifted from the migrations, so it is
never a second source of truth. `docs/Supabase Setup.md` is the walkthrough.

**Supabase CLI**, if you have it linked: `supabase db push`.

## What 001 sets up

- `postgis` and `pgcrypto`
- every table in build spec §8, plus `data_region` and `rulebase_pin` on `orgs` so the
  settings screen has somewhere to write
- `drones.kinetic_energy_j` as a **generated** column, so it can never drift from mass
  and speed
- `determinations` with a unique index on `(operation_id, mission_hash, rulebase_version)`
  for idempotent re-runs, and a check constraint that **refuses a determination with an
  empty trace**
- `proposed_facts` with a check that a confirmed or rejected fact names who decided it
- RLS enabled on every table and forced on all but `rulebase_versions` — the published
  rulebase, which carries a read-for-everyone policy — with the `current_user_org_ids()` membership
  policy pattern
- a trigger that gives each new user an org and an owner membership on first sign-in
- the three storage buckets
- rulebase version `2.5.0-rc1`, marked `verified = false`. `004_rulebase_rc2.sql`
  adds `2.5.0-rc2`; `005_rulebase_2_5_1.sql` adds `2.5.1`, the first version with
  every table transcribed from the adopted text, and makes it current

## A note on RLS

The backend uses the service-role key, which **bypasses RLS**. The real authorisation
gate is `app/deps.py`, which resolves `org_id` from the verified JWT and never from the
request. RLS is here so that any direct browser access is safe by default. See
`docs/ARCHITECTURE.md`.
