# Deployment

Everything runs on free tiers. No Redis, no Celery, no always-on worker, no paid service
beyond the Anthropic API key.

| Piece | Where | Notes |
|---|---|---|
| Backend | Render — Docker web service, Frankfurt, free | Sleeps after ~15 min idle |
| Frontend | Cloudflare Pages | `npm run build`, output `out` |
| Database | Supabase Postgres, EU region, free | Pauses after ~7 days idle |

EU regions throughout: data residency is a stated selling point, not an afterthought.

## 1. Supabase

1. Create a project in an **EU region** (Frankfurt or Dublin — the settings screen lets
   an operator choose, so pick the one you will offer first).
2. SQL Editor → run `backend/app/db/migrations/001_init.sql`. It enables `postgis` and
   `pgcrypto`, creates every table with RLS enabled and forced, and seeds rulebase
   version `2.5.0-rc1`.
3. Authentication → Providers → Email: enable email, and enable magic links.
4. Authentication → URL Configuration → Redirect URLs: add
   `http://localhost:3000/app/` and `https://<your-pages-domain>/app/`. Magic links
   fail silently without this.
5. Project Settings → API: copy the project URL, the anon key and the service-role key.
   JWT Settings: copy the JWT secret.
6. Storage: the migration creates `evidence`, `dossiers` and `public-assets`. The first
   two are private and reached only through backend-minted signed URLs.

**A paused project** (about 7 days of no traffic on the free tier) is restored from the
Supabase dashboard — open the project and choose Restore. It takes a few minutes and
loses no data. `/healthz` stays green while it is paused, by design;
`/healthz/deep` is the one that reports the database as unreachable.

## 2. Backend on Render

1. New → Web Service → connect the repository.
2. Root directory `backend`, runtime **Docker**, region **Frankfurt**, instance **Free**.
3. Environment: every backend key from `.env.example`. Set `ENV=production` — the app
   refuses to start without the Supabase keys, which is the behaviour you want in
   production. Set `CORS_ORIGINS` to the Pages origin. Set `GIT_SHA` to the commit so
   `/healthz` can be traced back to a build.
4. Health check path `/healthz`.

The Dockerfile is multi-stage on `python:3.12-slim` and installs WeasyPrint's runtime
libraries (`libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libpangoft2-1.0-0`,
`libgdk-pixbuf-2.0-0`, `libffi8`, `shared-mime-info`) plus a font, so PDF output is not
blank. It runs as a non-root user and honours Render's `$PORT`.

### The cold start is a product problem, not just an ops one

A free instance sleeps after ~15 minutes and takes tens of seconds to wake. Two
mitigations, both already in place:

- `frontend/src/lib/api.ts` treats 502/503/504 and network failures as *warming*, not
  errors: it retries with backoff totalling ~31 s and reports progress through
  `onWarming`, so a screen can say the service is waking instead of showing a red box.
- `/healthz` has no dependencies and is pinged by an external free uptime monitor
  (UptimeRobot or similar, 5-minute interval) to keep the instance awake during the day.

## 3. Frontend on Cloudflare Pages

1. New project → connect the repository.
2. Build command `npm run build`, output directory `out`, root directory `frontend`.
3. Environment: every `NEXT_PUBLIC_*` key from `.env.example`. These are inlined at
   build time, so **changing one requires a rebuild**, not just a restart.

The build is a static export (`output: 'export'`, `trailingSlash: true`,
`images.unoptimized`). No SSR, no server actions, no route handlers — Pages serves files.

## 4. Media

Drop real assets into `frontend/public/media/` using the filenames in
`frontend/src/lib/media-manifest.ts` and rebuild. No code change: `MediaSlot` probes for
the file and falls back to the designed placeholder when it is missing. `?slots=1` shows
each slot's id and size budget.

## 5. Smoke test against production

```bash
curl -s https://<render-host>/healthz | jq
curl -s https://<render-host>/healthz/deep | jq      # expect database: ok
```

Then in a browser: sign up, land on an empty dashboard, and check that the UNVERIFIED
banner is visible wherever a risk value appears. If it is not, something is claiming
verification it does not have.

## Local development

```bash
cd backend  && make dev     # http://localhost:8000 · docs at /docs
cd frontend && npm run dev  # http://localhost:3000
```

Both run without any environment configuration. Auth and persistence report themselves
as unconfigured rather than crashing, so the skeleton is usable before a Supabase project
exists.

### Validating the migration without Supabase

`001_init.sql` can be executed against a plain Postgres 16 by shimming the
Supabase-managed pieces: create an `auth` schema with a `users` table and `uid()` /
`role()` functions, a `storage` schema with a `buckets` table, and — if PostGIS is not
installed — substitute `text` for `geography(Polygon,4326)` and drop the `using gist`
from the geography index. Everything else (constraints, generated columns, triggers,
policies, the PL/pgSQL blocks) runs unmodified, which is enough to catch real errors
before they reach the project.
