# Environment variables

Every setting SORA Copilot reads, what it does, and where to get it. This is the
reference; `.env.example` at the repo root is the file you copy.

```bash
cp .env.example backend/.env        # backend settings
cp .env.example frontend/.env.local # the NEXT_PUBLIC_* ones
```

**The product runs with none of this configured.** Authentication, persistence, the
language model and payments each report themselves as unconfigured rather than failing,
so you can see the whole thing working before creating a single account. What you lose
without each one is in the *Without it* column.

Where to get each credential — which dashboard, which button — is in
[Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md).

---

## Two rules

**`SUPABASE_SERVICE_ROLE_KEY` and `STRIPE_SECRET_KEY` bypass every security control they
touch.** They belong in the backend's environment and nowhere else — never in the
frontend, never committed, never in a screenshot.

**Anything named `NEXT_PUBLIC_*` is compiled into the JavaScript the browser
downloads.** Treat it as published the moment you build. It also means changing one
needs a **rebuild**, not a restart.

---

## Backend — `backend/.env`

### Supabase — sign-in, database, file storage

| Variable | Required | Default | What it is |
|---|---|---|---|
| `SUPABASE_URL` | production | — | Project URL, `https://<ref>.supabase.co`. |
| `SUPABASE_SERVICE_ROLE_KEY` | production | — | **Server secret.** Bypasses row-level security by design; the backend holds it and the browser never does. |
| `SUPABASE_JWT_SECRET` | production | — | Verifies the access token on every request. `app/deps.py` resolves `org_id` from the verified `sub` and never from a request body. |

*Without them:* an in-memory store. Everything works; nothing survives a restart, and
`/healthz` reports `supabase_configured: false`. In `ENV=production` the app **refuses
to start** without all three — a compliance product should not come up half-configured
and look healthy.

### Anthropic — conversational intake and dossier prose

| Variable | Required | Default | What it is |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | no | — | Used only by `app/services/llm.py`. |
| `ANTHROPIC_MODEL` | no | `claude-sonnet-5-5` | Override only if you have a reason. |
| `LLM_MONTHLY_CALL_CAP` | no | `500` | Calls per organisation per month, checked **before** the call. |

*Without it:* a deterministic regex extractor, labelled as such in the panel. The wizard
form collects the same facts either way.

> The language model never computes a determination. Ground risk, air risk, SAIL, OSOs,
> robustness and containment come from the clingo engine and only from it. That is
> enforced structurally: the module that calls Anthropic has no import path — directly or
> transitively — to the module that writes determinations, and `tests/test_boundary.py`
> fails the build if one ever appears.

### Stripe — taking money

Optional, but **set both secrets or neither**: a checkout whose webhook cannot be
verified would take money and never grant the plan.

| Variable | Required | Default | What it is |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | no | — | **Server secret.** `sk_test_…` until you have run a real checkout. |
| `STRIPE_WEBHOOK_SECRET` | no | — | `whsec_…`. Without it the webhook endpoint **refuses every request** rather than trusting an unverified payload. |
| `STRIPE_PRICE_PRO` | no | — | A **price** id (`price_…`), not a product id (`prod_…`). |
| `STRIPE_PRICE_TEAM` | no | — | As above. |
| `STRIPE_PRICE_DOSSIER` | no | — | The one-off dossier purchase. |
| `STRIPE_RETURN_URL` | no | `http://localhost:3000/app/settings/` | The **frontend** origin plus a path. Only a *path* is ever taken from a request and resolved against this, so a checkout cannot redirect a payment confirmation off-site. |

*Without them:* every account sits on the free plan, the plan panel says payments are
not configured, and no button is offered that would fail.

> A plan is derived from the configured price id and from nothing else — never from a
> product's name, never from event metadata. Renaming a product in the Stripe dashboard
> cannot change what a customer is entitled to, and a forged `plan` field in an event
> body buys nothing.

### Rulebase and HTTP

| Variable | Required | Default | What it is |
|---|---|---|---|
| `RULEBASE_VERSION` | no | `2.5.0-rc1` | The version determinations pin to. Must exist in `rulebase_versions`. |
| `CORS_ORIGINS` | production | `http://localhost:3000` | Comma-separated. Add the deployed frontend origin. |
| `ENV` | no | `development` | `development` \| `test` \| `production`. |
| `GIT_SHA` | no | `unknown` | Injected at deploy time; surfaced by `/healthz` so a run traces to a commit. On Render, map `RENDER_GIT_COMMIT` across. |

---

## Frontend — `frontend/.env.local`

All five are compiled into the browser bundle. None is a secret.

| Variable | Required | Default | What it is |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | for sign-in | — | Same value as `SUPABASE_URL`. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | for sign-in | — | The anon key is *designed* to be public and is constrained by row-level security. |
| `NEXT_PUBLIC_API_URL` | yes | `http://localhost:8000` | Where the backend is. Point at Render in production. |
| `NEXT_PUBLIC_SITE_URL` | no | `https://sora-copilot.pages.dev` | Resolves the social-card URL at build time. |
| `NEXT_PUBLIC_MAP_STYLE_URL` | no | — | A MapLibre style JSON URL. |

*Without the Supabase pair:* the sign-in page says so plainly and names the two
variables, rather than failing opaquely.

*Without a map style:* the volume editor draws on a plain graticule and says the basemap
is not configured. **The geometry, the derived volumes and the determination are
unaffected** — the basemap is an aid to drawing, not an input. If your provider's key is
in the URL, restrict it by HTTP referrer: this one really is public.

---

## Minimum viable configurations

**Local, nothing configured** — both sides run, in-memory, deterministic extractor, free
plan:

```bash
cd backend  && make dev     # :8000, API docs at /docs
cd frontend && npm run dev  # :3000
```

**A real deployment people can sign up to** — the three Supabase keys, `CORS_ORIGINS`,
`ENV=production`, and the frontend's `NEXT_PUBLIC_SUPABASE_*` + `NEXT_PUBLIC_API_URL`.
Apply migrations `001`, `002` and `003` in order.

**Taking money** — add the five Stripe variables and `STRIPE_RETURN_URL`.

---

## Checking it

```bash
# Which variables are missing, and what is degraded as a result.
curl -s https://<host>/healthz | jq

# Is the database actually reachable?
curl -s https://<host>/healthz/deep | jq

# The whole product, end to end, against a deployed host.
BASE=https://<host> SUPABASE_JWT_SECRET=<secret> backend/scripts/smoke.sh
```

A test in the backend suite asserts that every field of the `Settings` model appears in
`.env.example`, so a new setting cannot be added without appearing in the template you
copy.
