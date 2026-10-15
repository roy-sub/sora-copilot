# Architecture

## The one invariant

**The language model never computes a determination.**

Ground risk class, air risk class, SAIL, the OSO set, robustness levels and containment
are computed by the clingo rules engine and by nothing else. The model has two jobs:
turn an operator's prose into candidate facts that the operator confirms, and turn the
engine's output into readable prose.

This is the product. A compliance tool whose numbers come from a language model is
worth nothing to a compliance officer, and the officer is the person who decides whether
to trust it. So the boundary is not a promise in a README — it is three mechanisms, all
of which are tested.

```
                   ┌─────────────────────────────────────────┐
  operator's       │  services/llm.py                        │
  prose  ─────────▶│  the ONLY module importing anthropic    │
                   │                                         │
                   │  emits ProposedFact objects — inert     │
                   └──────────────────┬──────────────────────┘
                                      │  status: pending
                                      ▼
                   ┌─────────────────────────────────────────┐
                   │  proposed_facts table                   │
                   │                                         │
                   │  pending ──▶ confirmed   (user action)  │
                   │          └─▶ rejected    (user action)  │
                   └──────────────────┬──────────────────────┘
                                      │  status == confirmed ONLY
                                      ▼
                   ┌─────────────────────────────────────────┐
                   │  services/determination.py              │
                   │  assembles a validated Mission          │
                   └──────────────────┬──────────────────────┘
                                      │
                                      ▼
   ╔══════════════════════════════════════════════════════════════════╗
   ║  app/engine/**            PURE                                   ║
   ║                                                                  ║
   ║  facts.py    Mission ──▶ ASP ground atoms                        ║
   ║  runner.py   clingo --models=1 over rulebase/sora_2_5/*.lp       ║
   ║  trace.py    because/3 atoms ──▶ TraceNode tree                  ║
   ║                                                                  ║
   ║  may import:  stdlib · clingo · clorm · z3 · pydantic            ║
   ║               app.domain                                         ║
   ║  may NOT:     anthropic · httpx · requests · app.db · app.services║
   ╚══════════════════════════════════════════╤═══════════════════════╝
                                              │
                                              ▼
                   ┌─────────────────────────────────────────┐
                   │  Determination                          │
                   │  + full trace, every node cited         │
                   │  + pinned rulebase_version              │
                   │  + warnings for UNVERIFIED tables       │
                   └──────────────────┬──────────────────────┘
                                      │  read-only
                                      ▼
                   ┌─────────────────────────────────────────┐
                   │  services/llm.py again, for prose only  │
                   │  may not restate, contradict or         │
                   │  recompute any risk value               │
                   └─────────────────────────────────────────┘
```

The model appears twice and computes nothing either time. On the way in it proposes; on
the way out it describes. The arrow from the engine to the prose job is one-way: a
`Determination` is already final when the model sees it.

## Mechanism 1 — import isolation

`app/engine/**` may import only the standard library, `clingo`, `clorm`, `z3`,
`pydantic`, and `app/domain/**`. It may not import `app/services/llm.py`, `anthropic`,
`httpx`, `requests`, or anything under `app/db/**`.

`app/domain` is the only internal dependency, and it imports nothing from `app` but
itself — so it can never pull the engine towards the network or the database.

## Mechanism 2 — a test that enforces it

`backend/tests/test_boundary.py` walks the **AST** of every file under `app/engine/` and
fails on any import outside the allowed set. It also asserts that:

- `app/services/llm.py` imports nothing from `app.engine`, `app.db` or
  `app.services.determination`
- `app/services/llm.py` contains no executable reference to the `determinations` table
- `anthropic` is imported by exactly one module in the whole application
- `stripe` is imported by exactly one module, `app/services/billing.py`, which in turn
  can reach neither the engine nor the determination service
- `app/services/plans.py` imports nothing from `app` at all, so plan limits stay readable
  on a deployment with no payment provider configured
- nothing under `app/engine/` can reach `app/national/` — a country *pack* is
  administrative, and only the rulebase's `90_national_*.lp` files may change a
  determination for a country

AST inspection rather than a runtime check matters: it fails on an import that is merely
*present*, long before anybody calls it.

Reachability is checked **transitively**, not one file at a time: the spec says "no
import path", and a module two hops from the database is still a module that can reach
it. This is worth labouring because an earlier version of the test recorded only the
package named in a `from X import Y` and therefore *passed* with a real two-hop path from
`llm.py` to the database in place. It was rewritten to record `X.Y` as well, and then
verified the only way such a test can be: by inserting the violation and watching it
fail.

Several tests exist to prove the suite is not vacuous — the engine package must contain
files, the docstring filter is tested against a literal it must catch, and the transitive
check is run against a graph that is known to contain a violation.

## Mechanism 3 — the data-flow gate

A `ProposedFact` carries `field`, `value`, `confidence`, `source_span` and
`status: pending | confirmed | rejected`. It is inert. `status` leaves `pending` only
through an explicit user action on
`POST /api/v1/operations/{id}/facts/{fact_id}/confirm`.

The determination service reads facts with `status == confirmed` and nothing else.
`POST /determine` returns **409** with the list of unconfirmed fields rather than running
on a partial mission. In the database, a check constraint refuses a confirmed or rejected
fact that does not record who decided it and when.

There is no code path from a pending fact to the engine.

## Why answer set programming

Three properties the regulation needs and a procedural implementation does not give:

1. **Justification is structural.** Every rule that concludes `X` also derives
   `because(X, RuleId, Premises)`. The trace formatter reads only `because/3`, and an
   integrity constraint makes a model with an unjustified conclusion *unsatisfiable*. A
   determination without a complete trace cannot be produced — not produced and flagged.
2. **Non-monotonicity is the point.** National annexes and PDRA/STS shortcuts are
   defeasible overrides over a default, which is how the regulation itself is layered.
   The `default → override` pattern is written out in `docs/RULEBASE.md`.
3. **Determinism is checkable.** The determination path runs with `--models=1`, and more
   than one answer set is treated as a rulebase bug that the tests assert on, rather than
   an ambiguity to be resolved at runtime.

## Request path

```
browser (static export, Cloudflare Pages)
  │  Supabase Auth in the browser; access token as a Bearer header
  ▼
FastAPI on Render (Docker, Frankfurt, free tier — sleeps after ~15 min idle)
  │  deps.py verifies the JWT and resolves org_id from org_members
  │  ── org_id is NEVER read from a request body or query string
  ▼
Supabase Postgres (EU) + PostGIS + Storage
```

## Authorisation: which layer is load-bearing

The backend holds the **service-role key, which bypasses row-level security by design**.
So:

- The **real gate** is `app/deps.py`. It verifies the Supabase JWT, takes `sub`, and
  looks up org membership. Every org-scoped query is filtered by that `org_id`.
- **RLS is defence-in-depth.** It is enabled *and forced* on every table with the
  `current_user_org_ids()` membership policy, so that any future direct browser access
  is safe by default and a mistake in the backend is not automatically a data leak.

Do not mistake the second for the first.

## One dossier, two formats

The dossier is what reaches an authority, and an operator wants DOCX to edit alongside
the authority's own forms or PDF to file. A PDF whose SAIL did not match the DOCX's
would be the worst bug this product could ship, so there is no second code path in which
it could happen: `services/dossier.py` describes the document **once**, against the
`Writer` protocol in `services/docwriter.py`, and a backend turns those calls into
`.docx` (python-docx) or `.pdf` (WeasyPrint, through print CSS).

The vocabulary is deliberately small — headings, paragraphs, bullets, key/value tables,
grid tables, notes, images, page breaks. Anything richer would start to encode layout in
the content path, which is where drift begins.

The PDF is rendered from HTML rather than converted from the DOCX: converting would need
LibreOffice, which does not fit on a free tier. A test renders both formats from the same
determination and asserts every risk value, the disclaimer, the UNVERIFIED banner and the
trace appear in each; another asserts the running header is on every page of the PDF.

## Invitations have no link

Inviting a colleague stores an **address**, not a token, and sends nothing. The
invitation is claimed on first sign-in, matched against the `email` claim of a Supabase
JWT the backend has already verified. So an invitation can only ever be taken by someone
who has proved control of that address to Supabase Auth — there is no secret to forward,
leak or replay, and the product needs no email sender.

The cost is that an invitation typed to the wrong address is claimable by whoever owns
it, which is why invitations expire after 14 days and why withdrawing one takes effect
immediately.

Seats are the one plan limit that cannot be checked only at the moment of use: two people
accepting at the same instant would put a five-seat organisation at six. So a **pending
invitation holds a seat** — members plus pending invitations is what is measured against
the plan.

## Plan gating

Commercial limits are the one place a request is refused for a reason that is not
regulatory, so they are kept somewhere obvious and shaped identically everywhere:

- `app/services/plans.py` says what a plan *means*. Pure data and pure functions, no
  Stripe, no database — it is read on every gated request including on a deployment with
  no payment provider at all.
- `app/services/billing.py` says how a plan is *bought*. The only module that imports
  `stripe`.
- `app/api/v1/gate.py` turns a limit into a **402** carrying `feature`, `plan`, `limit`,
  `used` and `upgrade_to`, so the frontend renders the upgrade panel from the fields
  rather than parsing prose.

Two ordering rules carry weight:

- **Ownership is checked before the gate** on every operation-scoped endpoint. A 402 on
  somebody else's operation would confirm that it exists, so those answer 404.
- **A dossier credit is checked before generation and spent after it.** A credit must not
  be burned by an export that then fails in the renderer or the object store.

The webhook is the only unauthenticated write endpoint in the product. Its payload is
verified against the endpoint secret before any field is read; the event id is claimed in
the database *before* the handler runs, so a redelivery is a no-op rather than a second
month of credits; the organisation comes from `client_reference_id` or `metadata.org_id`,
values this product set itself, never from an email; and a plan is derived from a
configured price id, so renaming a product in the Stripe dashboard cannot change what a
customer is entitled to.

## Errors

Every error is RFC 7807 `application/problem+json` with a machine-readable `code`, so
the frontend branches on the code and never on prose. Field-level validation adds
`errors[]`; the 409 from `/determine` adds `unconfirmed_fields[]`; the 402 from a plan
limit adds `feature`, `plan`, `limit`, `used` and `upgrade_to`.

## Free-tier shape

No Redis, no Celery, no always-on worker. Background work uses FastAPI `BackgroundTasks`;
scheduled work uses Supabase `pg_cron` or a Render Cron Job.

One consequence worth stating: a Render free instance can be put to sleep mid-job, so a
queued `BackgroundTasks` job can vanish silently. Dossier generation is therefore
**synchronous** — a single-operation DOCX renders in a second or two — while keeping the
`{job_id, status}` response shape so an async path can land later without an API break.

The same sleep is why `/healthz` has no dependencies: an external uptime monitor pings it
to keep the instance awake, and it has to stay green while Supabase is paused.
