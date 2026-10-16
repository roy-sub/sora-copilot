# Supabase Setup — everything done from the dashboard

**Do I need `DATABASE_URL` and the terminal?** No. That route exists to save you the
pasting; it is not required. Everything below happens in the Supabase dashboard in your
browser, and the result is identical — the same SQL, in the same order, in one
transaction.

**Time:** about 10 minutes, most of it copying keys.
**You need:** your Supabase project (you already have `sora-copilot`), and this repo
cloned so you can open one file.

---

## Step 1 — Create the schema

A new Supabase project is an **empty** database. It has Supabase's own `auth` and
`storage` schemas and nothing of yours. Every table this app reads and writes has to be
created, and this step is what creates them.

1. Open the file **`backend/app/db/migrations/bundle.sql`** from this repo in any text
   editor. It is the five migrations concatenated in order, wrapped in a transaction.
2. Select all of it and copy it. (It is about 700 lines. Copy the whole thing — the
   `begin;` at the top and the `commit;` at the bottom are part of it.)
3. In the dashboard: **SQL Editor** → **New query** (the `+ New` tab you already have
   open).
4. Paste, then **Run** (or `Ctrl`+`Enter`).

You should see **Success. No rows returned**. That is what success looks like for a
schema change — it creates things, it does not return a table of results.

**If it fails**, nothing was created. The whole file is one transaction, so a failure
leaves the database exactly as it was: fix the cause and paste it again. The most common
cause is a partial copy — scroll to the end of what you pasted and check the last line
is `commit;`.

**Running it a second time is harmless.** Every `create` is guarded and every policy and
trigger is dropped first, so a re-paste is a no-op. (Checked, not assumed: the whole set
was run twice against a Postgres 16 and the second run changed nothing.)

<details>
<summary>What those five migrations create</summary>

| File | What it adds |
|---|---|
| `001_init.sql` | The `postgis` and `pgcrypto` extensions, every table, row-level security on all of them, the trigger that gives each new user an organisation on first sign-in, the three storage buckets, and rulebase `2.5.0-rc1` |
| `002_billing.sql` | Subscriptions, dossier credits, and the Stripe webhook's idempotency log |
| `003_invites.sql` | Organisation invitations, so a Team plan's five seats can actually be used |
| `004_rulebase_rc2.sql` | Rulebase `2.5.0-rc2` |
| `005_rulebase_2_5_1.sql` | Rulebase `2.5.1` — every table transcribed from the adopted EASA text — and makes it the current one |

The last two **insert a row** rather than editing the previous one. Determinations pin
the rulebase version they were computed against, so an old record has to keep describing
itself with the rules it was actually computed under.

A sixth table, `schema_migrations`, is the bookkeeping: it records which files have been
applied. You never touch it. It is what lets the command-line route (`make migrate`) know
the schema already exists, instead of running everything again.
</details>

---

## Step 2 — Check it worked

Still in the SQL Editor, new query, paste this and Run:

```sql
select filename from public.schema_migrations order by filename;
```

Expect exactly five rows: `001_init.sql` through `005_rulebase_2_5_1.sql`.

```sql
select version, is_current, verified from public.rulebase_versions order by version;
```

Expect three rows, and only `2.5.1` with `is_current = true` and `verified = true`.
**If more than one row says `is_current`, stop** — the app cannot decide which rulebase
to use. (It cannot normally happen: a unique index forbids it.)

```sql
select count(*) as tables from information_schema.tables where table_schema = 'public';
```

Expect **18**.

```sql
select id, public from storage.buckets order by id;
```

Expect `dossiers` (`false`), `evidence` (`false`) and `public-assets` (`true`). The first
two must stay private — evidence files and generated dossiers are reached only through
short-lived signed URLs minted by the backend.

```sql
select relname, relrowsecurity as enabled, relforcerowsecurity as forced
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r'
 order by relname;
```

Every row should say `enabled = true`. All but one also say `forced = true`;
`rulebase_versions` is the exception, deliberately — it is the published rulebase and
carries a read-for-everyone policy, so there is nothing in it to protect.

Supabase's **Advisors → Security** page will also flag anything with RLS off. It should
have nothing to say about this schema.

---

## Step 3 — Authentication

1. **Authentication** → **Sign In / Providers** → **Email**: make sure it is enabled,
   and that magic links are on.
2. **Authentication** → **URL Configuration** → **Redirect URLs**: add both
   - `http://localhost:3000/app/`
   - `https://<your-live-domain>/app/`

   Add the live one now even if you have not deployed yet. **A magic link to a URL that
   is not on this list fails silently** — the user clicks it, nothing happens, and
   nothing in the logs says why. This is the single most common "the app is broken"
   cause, and it is not an app bug.

---

## Step 4 — Copy the four values

1. **Project Settings** → **API**
   - **Project URL** → `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` (frontend)
   - **anon / public** key → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend)
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` (backend)
2. **Project Settings** → **API** → **JWT Settings** → **JWT Secret** →
   `SUPABASE_JWT_SECRET` (backend)

**The `service_role` key bypasses row-level security entirely.** It belongs in the
backend's environment and nowhere else — never in the frontend, never in a
`NEXT_PUBLIC_*` variable, never committed. Anything named `NEXT_PUBLIC_*` is compiled
into the browser bundle and is readable by anyone who opens your site.

[ENV Example](./ENV%20Example.md) lists every variable;
[Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md) walks through the rest
(Anthropic, Stripe, the map style).

---

## Step 5 — Nothing else

That is the whole database setup. Specifically, you do **not** need to:

- create any table, column, index or policy by hand — the bundle did all of it;
- enable row-level security anywhere — `001` does it for every table;
- create the storage buckets — the bundle creates all three;
- set up any Supabase Edge Function, cron job or database webhook — this app uses none;
- give Supabase your Stripe or Anthropic keys — those are the backend's, not Supabase's.

Carry on with [Deployment Guide](./Deployment%20Guide.md), Part 1 §2 (Render).

---

## Things that will bite you later

**The free tier pauses a project after about 7 days with no traffic.** Open the project
in the dashboard and choose **Restore**; it takes a few minutes and loses no data. While
it is paused, `/healthz` on your backend stays green on purpose — it answers without
touching the database, so your host does not kill the service. `/healthz/deep` is the one
that reports the database as unreachable. If the app is suddenly failing on every
request, check this first.

**Save your database password.** Supabase shows it once, at project creation. You do not
need it for anything above, but you will want it the day you need a direct connection.
It can be reset from Project Settings → Database.

**Never edit a migration that has already been applied.** Corrections land as the next
numbered file. A database should always be rebuildable by replaying `001` onwards — and
if someone does edit one, `make migrate` notices via a stored checksum and refuses to
continue rather than quietly running something else.

---

## If you later want the one-command route

Nothing above has to be undone. The bundle already wrote the ledger rows, so from a
terminal:

```bash
cd backend
echo 'DATABASE_URL=postgresql://postgres.<ref>:<password>@<host>:5432/postgres' >> .env
make migrate
```

reports **"Nothing to do: the database is up to date."** From then on, a new migration is
one command. Get the connection string from **Connect** at the top of the dashboard →
**Session pooler** → copy the URI and put your database password in it. Use port
**5432**; the transaction pooler on 6543 cannot run schema changes. `DATABASE_URL` is a
local convenience only — it does **not** go into Render, because the running backend
talks to Supabase over its HTTP API and never opens a Postgres connection.
