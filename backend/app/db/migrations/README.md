# Migrations

Numbered SQL files, applied in order. **Never edit a migration that has been applied** —
corrections land as the next number, so a database can always be rebuilt by replaying
them from 001.

## Applying

**Supabase SQL editor** (simplest for the free tier): open the project → SQL Editor →
paste the file → Run. Apply them in numeric order.

**Supabase CLI**, if you have it linked:

```bash
supabase db push
```

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
- RLS enabled and forced on every table, with the `current_user_org_ids()` membership
  policy pattern
- a trigger that gives each new user an org and an owner membership on first sign-in
- the three storage buckets
- rulebase version `2.5.0-rc1`, marked `verified = false`

## A note on RLS

The backend uses the service-role key, which **bypasses RLS**. The real authorisation
gate is `app/deps.py`, which resolves `org_id` from the verified JWT and never from the
request. RLS is here so that any direct browser access is safe by default. See
`docs/ARCHITECTURE.md`.
