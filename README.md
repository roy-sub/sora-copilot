# SORA Copilot

**A neurosymbolic compliance engine for European drone operations.**

Live application: **[sora-copilot.com](https://sora-copilot.com/)**

SORA Copilot automates the Specific Operations Risk Assessment, the formal safety methodology that EU Regulation 2019/947 requires before any drone operation outside the open category may be authorised. An operator describes a mission; a symbolic rules engine computes the intrinsic ground risk class, the air risk class, the resulting SAIL level, the required Operational Safety Objectives and the containment requirements, and emits an authority-ready dossier in which every conclusion carries a derivation trace citing the regulation that produced it.

The system additionally answers the question an operator actually wants answered, which no static assessment tool addresses: not only whether this mission is permissible, but what minimal change to the mission would make it easier to authorise. That is formulated as an abductive search over the mission parameters.

This repository unifies two previously separate codebases. The `frontend/` and `backend/` directories each retain their own detailed technical README and documentation; this root document covers the system as a whole: why it exists, how it is designed, and which engineering and research decisions shaped it.

**Technical documentation lives with the code it describes.** Each half of the system carries its own developer-facing README — how to run it, how it is laid out, and what every moving part does. Read [`backend/README.md`](./backend/README.md) to work on the API, the rules engine or the rulebase, and [`frontend/README.md`](./frontend/README.md) to work on the application, the map editor or the design tokens.

---

## Table of contents

1. [Problem](#1-problem)
2. [What the system does](#2-what-the-system-does)
3. [Why this is a reasoning problem, not a generation problem](#3-why-this-is-a-reasoning-problem-not-a-generation-problem)
4. [System architecture](#4-system-architecture)
5. [The symbolic core](#5-the-symbolic-core)
6. [Abductive counterfactual reasoning](#6-abductive-counterfactual-reasoning)
7. [The geospatial facts layer](#7-the-geospatial-facts-layer)
8. [The AI layer and its enforced boundary](#8-the-ai-layer-and-its-enforced-boundary)
9. [Engineering decisions and trade-offs](#9-engineering-decisions-and-trade-offs)
10. [Correctness, testing and regulatory integrity](#10-correctness-testing-and-regulatory-integrity)
11. [Data model and reproducibility](#11-data-model-and-reproducibility)
12. [Deployment](#12-deployment)
13. [Repository layout and component documentation](#13-repository-layout-and-component-documentation)
14. [Running the project locally](#14-running-the-project-locally)
15. [Academic context](#15-academic-context)
16. [Complete codebase structure](#16-complete-codebase-structure)
17. [Current state and roadmap](#17-current-state-and-roadmap)
18. [Disclaimer](#18-disclaimer)

---

## 1. Problem

Under EU Regulation 2019/947, a drone operation that falls outside the open category, which covers most commercial work involving heavier aircraft, flight beyond visual line of sight, operation over populated areas or higher altitudes, requires an operational authorisation from the national aviation authority. That authorisation is granted on the basis of a SORA assessment conducted in accordance with the Acceptable Means of Compliance to Article 11, with SORA 2.5 adopted by EASA in 2024.

SORA is a genuinely formal methodology. It is a chain of table lookups, mitigation adjustments and matrix derivations: aircraft dimension and the population density of the overflown area produce an intrinsic ground risk class; ground mitigations reduce it to a final ground risk class; airspace characteristics produce an initial air risk class, which strategic mitigation reduces to a residual class; the two together determine a Specific Assurance and Integrity Level from I to VI; and that level expands into roughly twenty-four Operational Safety Objectives, each at a required robustness of low, medium or high, plus containment and adjacent-area requirements.

Every one of those steps is deterministic given the facts. Nevertheless, operators routinely pay aviation consultancies between one and five thousand euros per authorisation dossier and wait weeks for delivery, and must repeat the exercise whenever a mission parameter changes. Existing drone software manages flights, logs and mapping; none of it reasons about legality or produces a SORA dossier.

The consequence is not merely cost. Small operators decline work they could lawfully perform, because the assessment overhead exceeds the value of the job.

## 2. What the system does

An operator defines a mission through a guided intake: aircraft characteristics, operation type, the operational volume drawn directly on a map, altitude, the character of the overflown ground, airspace class and proximity to aerodromes, and the mitigations they intend to claim. The system then:

1. **Derives the operational volume geometry.** From the flight geography the operator draws, it computes the contingency volume, the ground risk buffer and the adjacent area, using buffer parameters transcribed from the methodology rather than estimated.
2. **Grounds the geospatial facts.** A population density figure for the ground risk buffer is classified into the density band the methodology uses, and a ground environment is suggested from that band with its rationale. The figure, the band and the source it came from are all presented to the operator for confirmation, with an override. No population raster is bundled yet, so the figure is supplied by the operator and recorded with its stated source; the sampling interface and the stored provenance are in place for a raster to be dropped in behind them.
3. **Computes the full risk chain.** Intrinsic ground risk class, the effect of each claimed mitigation at its claimed robustness, final ground risk class, initial and residual air risk class, tactical mitigation performance requirements, SAIL, the expanded set of Operational Safety Objectives with their required robustness levels, and containment requirements.
4. **Carries the shortcut paths.** Standard Scenarios and Predefined Risk Assessments are encoded as priority-based defeasible overrides rather than as special cases in application code, and take effect when the operator declares one. No shortcut has been transcribed yet: the layer is the contract a transcription must satisfy, and fires for nothing until its applicability conditions come from the published document.
5. **Renders the derivation.** The complete reasoning appears as an expandable tree in which every node names the rule that fired and the regulatory section it comes from, down to the ground facts at the leaves.
6. **Performs gap analysis.** Required Operational Safety Objectives are reconciled against the evidence the operator holds, producing an explicit list of what is unmet and at what robustness.
7. **Advises on counterfactuals.** The system searches for minimal changes to the mission that would lower the SAIL, and reports each with its resulting objective set and the evidence that new robustness level would demand.
8. **Generates the dossier.** The concept of operations, the SORA assessment tables, the objective compliance matrix, the emergency response plan skeleton and a justification appendix rendering the full trace, exported as an authority-ready document.
9. **Pins the rulebase.** Every determination records the rulebase version it was computed against and the hash of its input facts, so a conclusion survives a change to the encoded regulation: the stored operation can be replayed against a new version to establish whether an existing authorisation is affected. The replay runs on demand; running it continuously as an alerting pipeline is on the roadmap.

A free category checker, which determines whether an operation falls in the open, specific or certified category and estimates its SAIL, runs without an account.

## 3. Why this is a reasoning problem, not a generation problem

SORA is a worked example of the class of problem that symbolic methods solve well and statistical methods solve unreliably.

The methodology is a published, finite, table-driven procedure with correct answers. It is layered: an EASA baseline, national annexes from each aviation authority that override it, and Standard Scenario and Predefined Risk Assessment paths that supersede the general procedure when their applicability conditions hold. That layering is non-monotonic by construction. Adding the fact that an operation matches a Predefined Risk Assessment does not add to the general conclusion; it retracts and replaces it.

It is also a domain in which the reasoning must be auditable by a third party. The output is submitted to a national aviation authority whose case officer may interrogate any step. An assessment that cannot show its derivation is not a weaker product, it is an unusable one.

A language model can generate a plausible SAIL level and a plausible objective matrix, and can be wrong in ways indistinguishable from being right to the operator submitting it. A logic program either derives the conclusion from the encoded tables or it does not, and the derivation is the artifact that makes the submission defensible.

The architecture therefore splits along a strict perception and decision boundary:

| Responsibility | Component | Rationale |
| --- | --- | --- |
| Geometry derivation, density classification, airspace lookup | Geospatial service, deterministic | Measurable facts, computed not inferred, confirmed by the operator |
| Conversational intake into structured mission facts | LLM, proposals only | Unstructured input, tolerant of error because every fact is confirmed |
| Risk chain, SAIL, objectives, containment | Answer Set Programming | Non-monotonic, override-heavy, requires justification |
| Minimal mitigating change | Bounded combination search over the same encoding | Abductive search, not derivable by forward inference |
| Dossier prose | LLM, constrained to engine output | Natural language rendering of an already-decided structure |

The boundary is enforced in code and verified by a test, described in section 8.

## 4. System architecture

```
                 Browser (Next.js, static export, Cloudflare Pages)
                                     |
                             HTTPS, bearer JWT
                                     |
                FastAPI application (Python web service, Render, EU)
                                     |
       +-------------+---------------+---------------+-------------+
       |             |               |               |             |
    intake         geo            engine        counterfactual   dossier
    LLM, facts     volumes,       clingo / ASP   bounded search   DOCX, PDF,
    proposed       density,       risk chain,    re-running the   trace
    confirmed      airspace       trace          same engine      appendix
       |             |               |               |             |
       +-------------+---------------+---------------+-------------+
                                     |
              Supabase (EU): Postgres with PostGIS and row-level
              security, Auth, private storage
```

**Backend.** Python 3.12, FastAPI, Pydantic v2. The reasoning packages are architecturally isolated: `app/engine/` is pure, with no database access, no network access and no model access. It accepts validated domain objects and returns determinations with traces. Stateful concerns live in `app/services/`, transport in `app/api/v1/`.

**Frontend.** Next.js 15 with the App Router, compiled to a static export. MapLibre GL carries the operational volume editor with separate layers for flight geography, contingency volume and ground risk buffer; React Flow renders the derivation tree. All state is served by the backend API, so the entire frontend deploys as static assets on a CDN edge.

**Database.** Supabase Postgres with PostGIS for volume geometry, row-level security enforced at the database layer on every table and scoped through organisation membership. The backend derives organisation identity exclusively from the verified JWT, never from request bodies, and reaches Supabase over PostgREST rather than opening a Postgres socket.

**Data residency.** Database, object storage and compute are all hosted in EU regions. For operators submitting to Austro Control or the Luftfahrt-Bundesamt this is a procurement requirement rather than a preference, and it is a stated property of the product.

## 5. The symbolic core

### 5.1 The rulebase

The entire risk chain is an Answer Set Program, organised as modular logic programs: core declarations, intrinsic ground risk, ground mitigations, air risk, the SAIL matrix, objective expansion, containment, Standard Scenario and Predefined Risk Assessment routing, and one module per national annex.

Two properties hold throughout.

**Every derived atom carries its own justification.** Each rule that concludes `X` also derives `because(X, RuleId, Premises)` within the same rule body. An integrity constraint renders any answer set containing an unjustified conclusion unsatisfiable, so a determination without a trace is not a degraded result, it is an unsatisfiable program. The trace formatter reads only these justification atoms, which means the explanation shown to the operator and printed into the dossier appendix is generated from the derivation that produced the answer, not reconstructed afterwards.

**Regulatory values are transcribed, never inferred.** Each table in the methodology, the intrinsic ground risk matrix, the mitigation adjustments, the air risk assignment, the SAIL matrix, the objective matrix, the containment and tactical mitigation requirements, exists as a versioned CSV carrying the document, section and page it was transcribed from, plus an explicit verification flag. A build step compiles these into logic-program facts and refuses malformed rows. Any value not yet verified against its published source surfaces as a warning on the determination and a visible banner in the interface. In a compliance product a fabricated table value is a worse failure than a missing one. Every table of the current rulebase is verified: the eleven regulatory ones against the EASA Easy Access Rules carrying the SORA 2.5 package, and the three that are the project's own rather than the regulation's — the rule-to-source citation index, the intake density prefill hints and the counterfactual effort costs — labelled as such in their own provenance headers. Determinations therefore carry no unverified warning, and `make rulebase --strict` fails the build if any table ever regresses to a seed.

### 5.2 Defeasible layering

National annexes and the Standard Scenario and Predefined Risk Assessment paths are encoded as defeasible overrides over an EASA baseline, which is the structure the formalism exists to express:

```prolog
grc(V) :- grc_default(V), not grc_overridden.
grc(V) :- grc_override(V, _RuleId).
grc_overridden :- grc_override(_, _).
```

This matters beyond elegance. The same mission assessed under Austrian and German national rules can produce different obligations, and the system must be able to say which rule produced the difference. Encoding the baseline and the national delta as separate, individually citable modules makes that answerable; encoding them as branching application logic would not.

### 5.3 The deontic layer

The output of the chain is not a score. It is a set of normative positions: obligations the operator must discharge, in the form of Operational Safety Objectives at specified robustness levels; permissions conditional on authorisation; and prohibitions arising from geographical zones. These are modelled explicitly as deontic predicates rather than flattened into a checklist, which keeps the distinction between an objective that is unmet and an objective that does not apply, and makes the gap analysis a derived consequence rather than a separate computation.

## 6. Abductive counterfactual reasoning

The risk chain is a forward inference: given the mission, derive the SAIL. The question operators ask is the inverse. Given that this mission lands at SAIL III, what is the least costly change that would bring it to SAIL II?

This is abduction, not deduction, and it is the feature of the system with the most research content.

The implementation is a bounded combination search over the real engine. Candidate changes are enumerated across a discrete space — maximum altitude, ground environment band, operation type, population density band, and each mitigation claim at each robustness level — and combinations of increasing size are tried, single changes first, then pairs. Every candidate is re-run through clingo, and the search stops at the smallest size that finds anything, so what comes back is minimal. Suggestions are ranked by an effort cost assigned per parameter, so that lowering altitude by twenty metres is correctly preferred over fitting a parachute and evidencing it to medium robustness. That cost table is the project's, not the regulation's, and it orders the list without ever touching a determination.

Pairs are searched because single-parameter search is not enough in practice, and not only in theory: for a sparsely-populated BVLOS corridor inside an aerodrome environment with nothing claimed, no single change lowers the SAIL at all, because the operation needs a ground-risk reduction and an air-risk reduction together. An advisor that answers "nothing helps" there is worse than no advisor.

An SMT formulation was considered and deliberately rejected: encoding the SORA tables a second time in SMT, beside the clingo encoding, would mean two implementations of the same compliance rules — exactly the failure this architecture exists to prevent — and the usual safeguard, a test asserting the two agree, is an admission that they might not. Searching combinations against the one authoritative engine is slower and completely sound: every suggestion offered is a SAIL the solver actually produced. At roughly 16 ms per solve, a pair search costs about a second, which is affordable for an interactive advisor.

Each suggestion returns the change, the resulting SAIL, the delta in required objectives, and the evidence the new robustness level would demand, so that the operator can see not only that a change helps but what it would cost to actually satisfy.

## 7. The geospatial facts layer

The engine is purely logical and consumes ground atoms. Producing those atoms from the physical world is a separate problem, and the boundary between them is deliberate.

The operator draws the flight geography on a map. From it the service derives the contingency volume and the ground risk buffer using buffer parameters transcribed from the methodology, and the adjacent area ring. Geometry is stored in a geographic coordinate system and reprojected to a local equal-area projection for all area and buffer arithmetic, because computing areas in degrees is a correctness bug that produces plausible numbers.

Population density is classified into the band the intrinsic ground risk table defines, reading the band ceilings from that same table so the two cannot disagree, and a ground environment is suggested from the band together with the rationale for the suggestion. A controlled ground area and an assembly of people are never suggested, because they are claims about access control and about an event, not about a density figure. The density value, the band it maps to and the version of the source it came from are all persisted, so that a determination made today remains reproducible after the underlying dataset is updated. No gridded population raster is bundled yet; until one is, the figure is the operator's and is recorded as such, and the conservative reading — the maximum density within the ground risk buffer rather than the mean — is what the sampling interface is specified to take.

Critically, the density is presented to the operator for confirmation with an override. The system treats its own geospatial inference as a proposal about the world, not a fact, for the same reason it treats model extraction that way: the operator is accountable for the submission and must be able to see and correct what the machine believes.

## 8. The AI layer and its enforced boundary

The language model has exactly three jobs, and the system is built so that it cannot acquire a fourth.

**Conversational intake.** An operator may describe a mission in prose rather than completing the form. The model is invoked with a strict tool-use schema at temperature zero and returns `ProposedFact` objects: field, value, confidence, source span, and a status that begins as pending. The schema has no conclusion field, so there is nothing for the model to conclude into, and any field outside the proposable set is dropped before the response is returned. These appear in the interface as confirmable chips, never as conclusions.

**Dossier prose.** The generator receives the determination and the operator's confirmed inputs only. It is prohibited from restating, contradicting or recomputing any risk value, every factual sentence must correspond to a supplied fact, and the caller re-checks the output for invented risk vocabulary before it reaches a document.

**Trace explanation.** On request, it explains a single derivation node or objective in plain language, grounded in the citation that node already carries.

Three mechanisms enforce the boundary:

1. **Import isolation.** The engine package may import only the standard library, the solver bindings, Pydantic and the domain models. It may not import the model SDK, any HTTP client, the LLM service module, or the database layer.
2. **A test that enforces it.** A boundary test walks the abstract syntax tree of every file in the engine package and fails on any forbidden import. It additionally asserts that the LLM service module never imports the engine runner — transitively, not merely directly — and never writes to the determinations table. The architectural claim is continuously verified rather than documented and eroded.
3. **A data-flow gate.** The determination service reads only facts whose status is confirmed, which requires an explicit user action through a dedicated endpoint. There is no code path from a pending proposal to a determination, so a model hallucination cannot silently become a submitted risk assessment.

This is the architectural idea the project exists to demonstrate: the model is used where its failure mode is recoverable and visible, and excluded from every position where its failure mode would be silent.

## 9. Engineering decisions and trade-offs

**Answer Set Programming rather than a general-purpose rule engine.** The methodology is saturated with defaults and exceptions, and the national and Predefined Risk Assessment layers are overrides rather than additions. Encoding that in imperative code produces a conditional thicket that cannot explain itself. ASP expresses it natively and yields the derivation as a first-class object. The cost is a solver dependency and a narrower pool of maintainers; the mitigation is that rules are modular, versioned and generated from transcribed tables rather than hand-written per value.

**One encoding, searched, rather than a second encoding in SMT.** The counterfactual advisor could have been an optimisation problem over an SMT encoding of the same tables. That would have produced a second authority on what the regulation says, and the standard remedy — a cross-check test — concedes the possibility of disagreement. Re-running the one engine is the slower answer and the sound one; section 6 has the full reasoning.

**Determinism asserted, not assumed.** The determination path runs the solver constrained to a single model. More than one answer set indicates an under-constrained rulebase, which is a defect, and the test suite asserts against it rather than silently taking the first result.

**Static export rather than server-rendered frontend.** All state sits behind the API, so the frontend has no server-side data requirements. Compiling to static assets removes a class of runtime failure, puts the marketing site and the application shell on a CDN edge, and decouples frontend availability from backend availability.

**Generated API client.** The TypeScript client is generated from the backend OpenAPI schema. Contract drift between two independently developed codebases is a predictable defect source, and generating one side from the other eliminates it as a category.

**Deliberate infrastructure minimalism.** No message broker, no worker fleet, no cache tier, no container image. Background work uses request-scoped tasks; every dependency is a Python wheel and the document renderers carry their own typeface, so a checkout plus `pip install` is a working backend on any host that can run Python. This began as a constraint, since the production deployment runs within free infrastructure tiers, and became a design asset: fewer moving parts, a smaller failure surface, and an operational footprint a single engineer can hold completely in mind.

**Conservative defaults where the methodology permits latitude.** Where a buffer model admits several readings, the system applies the conservative one and labels it as such in the trace rather than selecting silently. An operator can argue for a less conservative model with their authority; they cannot argue for one they were never told had been chosen on their behalf.

## 10. Correctness, testing and regulatory integrity

Not every part of this system carries the same consequence of failure, and the testing strategy reflects that rather than pursuing uniform coverage.

**Golden cases from published worked examples.** Each case is a complete mission with its expected intrinsic ground risk class, final ground risk class, initial and residual air risk class, SAIL and objective set, recorded against the rulebase version it was verified under. Engine changes do not land with a failing golden case, and the suite is intended to be published alongside the encoding. Cases that must be refused — a mitigation claimed at a robustness the methodology does not permit, a parachute claimed without one fitted — are golden too, asserted as unsatisfiable rather than as a wrong answer.

**Trace completeness as an invariant.** The integrity constraint described in section 5 makes an untraced conclusion unsatisfiable rather than merely untested, which converts a documentation promise into a property of the program.

**Counterfactuals validated by the engine itself.** Every suggestion the advisor returns was produced by re-running the authoritative solver, so there is no second encoding to keep honest and no class of suggestion that holds in a model of the rules but not in the rules.

**Geospatial arithmetic tested against known areas.** Buffer and area computations are verified against analytically known geometries at several latitudes, because projection errors produce results that look entirely reasonable.

**The architectural boundary test** described in section 8, which converts a design principle into a continuously enforced invariant.

**Rulebase governance.** Every rulebase version carries a changelog and a source list. Determinations are pinned to the version that produced them and are idempotent with respect to the hash of their input facts, so a conclusion reached under one version of the methodology remains reproducible and explainable after the methodology moves.

## 11. Data model and reproducibility

The schema is organised around an operation: the aircraft record, the mission parameters, the three operational volume geometries, the geospatial facts snapshot with its source version, determinations with their full trace and pinned rulebase version, mitigation claims with evidence status, uploaded evidence, generated dossiers with their versions, and rulebase versions with their diffs and sources. Every table has row-level security enabled and is scoped through organisation membership.

Reproducibility is treated as a product requirement rather than an engineering nicety. An authorisation granted on the basis of a dossier generated in October must still be explainable in March, after the methodology, the population dataset and the national annex have all potentially changed. Every input that could affect a conclusion, including the version of the geospatial dataset it was sampled from, is persisted with the determination.

The regulatory change impact analysis is a direct consequence of this design. Because determinations are pinned and reproducible, a new rulebase version can be replayed against every stored operation to identify exactly which existing authorisations are affected and in what way, which is both the strongest retention feature in the product and a demonstration that versioned rules-as-code pays for itself operationally. Rulebase versions are inserted, never edited, for the same reason: a stored record has to keep describing itself correctly.

## 12. Deployment

| Component | Platform | Notes |
| --- | --- | --- |
| Backend | Render, Python web service, Frankfurt | No Dockerfile; every dependency is a wheel and the renderers bundle their own typeface |
| Frontend | Cloudflare Pages | Static export served from the edge; any static host works |
| Database, auth, storage | Supabase, EU region | Postgres with PostGIS and row-level security; schema applied from numbered SQL migrations |
| Payments | Stripe | Per-dossier one-time and tiered subscription, entitlement gating via a signature-verified, idempotent webhook |

The rulebase version currently in force is displayed on every determination and in every exported dossier, which makes the system's own knowledge boundary visible to the operator rather than implicit.

Two operational notes worth recording: the backend tier sleeps after roughly fifteen minutes idle, so the frontend renders an explicit warming state and retries with backoff on first contact rather than surfacing an error; and the free database tier pauses after about a week without traffic, which `/healthz/deep` reports and the shallow `/healthz` deliberately does not, so an uptime monitor pinging the backend awake never masks a paused database.

## 13. Repository layout and component documentation

```
sora-copilot/
├── backend/        FastAPI service, ASP engine, rulebase, geospatial layer, counterfactuals
├── frontend/       Next.js application, map editor, derivation tree, static export
├── design/         Design system, tokens, reference screens — read only
├── docs/           Architecture, rulebase governance, deployment and setup guides
├── PLAN.md         Phase-by-phase build state, decisions taken, what is still blocked
├── .env.example    Every variable for both halves, annotated
└── README.md       This document
```

Each half of the system carries its own full technical documentation, written for a reader intending to build, modify or extend that component:

- **[`backend/README.md`](./backend/README.md)** covers the service layout, the engine package, the rulebase compilation pipeline and table provenance, the counterfactual search, the geospatial derivation, the API surface and the test suite.
- **[`frontend/README.md`](./frontend/README.md)** covers the application structure, the generated API client, the operational volume map editor and its layer model, the derivation tree rendering, the design-token system and the static-export build.
- **[`docs/`](./docs/)** holds the cross-cutting documents: the architecture record, the rulebase and transcription governance notes, the deployment runbook, the Supabase and third-party setup guides, and the environment reference.

Section 16 expands this into the complete file-level structure.

## 14. Running the project locally

Prerequisites: **Python 3.12 or newer** and **Node.js 20**. No Docker, no container build. A Supabase project is optional — both halves run unconfigured, reporting auth, persistence, the intake model and payments as unavailable rather than crashing.

```bash
# Backend — http://localhost:8000, API docs at /docs
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python main.py

# Frontend — http://localhost:3000
cd frontend
npm install
npm run dev
```

The engine runs standalone from the command line without the web stack, which keeps the rulebase developable and testable in isolation from the application and makes the encoding usable as an independent artifact:

```bash
cd backend
.venv/bin/python -m app.engine.cli --example > mission.json   # a template mission
.venv/bin/python -m app.engine.cli mission.json               # the chain, the trace, any warnings
.venv/bin/python -m app.engine.cli mission.json --counterfactuals
```

To sign in and persist anything, copy `.env.example` to `backend/.env` and `frontend/.env.local`, fill in the Supabase keys, and apply the migrations in `backend/app/db/migrations/`. Component-specific setup, migration and environment details are in the two subdirectory READMEs linked above and in [`docs/`](./docs/).

## 15. Academic context

This project was built as an applied demonstration of knowledge representation and automated reasoning in a domain where their advantages over purely statistical methods are operational rather than rhetorical.

The formal content it exercises:

- **Non-monotonic and defeasible reasoning.** An EASA baseline defeated by national annexes, and both superseded by Standard Scenario and Predefined Risk Assessment paths when their applicability conditions hold, with conclusions that retract correctly when a fact is withdrawn.
- **Deontic modelling of a normative system.** Obligations, permissions and prohibitions represented explicitly rather than flattened into checklist state, so that the normative structure of the regulation survives into the data model.
- **Abductive and counterfactual reasoning as a product feature.** Minimal-change search over mission parameters, solved as a bounded combination search against the authoritative encoding, answering the inverse of the question the regulation is written to answer.
- **Rules as code with proof traces.** A regulatory corpus encoded as a versioned, source-linked logic program in which justification is derived rather than reconstructed, and every determination is reproducible against the rulebase and dataset versions that produced it.
- **Verifiable neurosymbolic separation.** A language model confined to perception and language, a symbolic reasoner holding every decision, and an architectural invariant enforced by a test rather than asserted in prose.

These areas map closely onto the research profile of TU Wien's Faculty of Informatics, in particular the Logic and Computation programme's treatment of knowledge representation, Answer Set Programming and non-monotonic reasoning, and the deontic logic and normative reasoning work on which the obligation modelling here directly draws. The intention was to take that apparatus out of the exercise sheet and into a deployed system operating on live European regulation, with real users and real consequences for being wrong, and to establish which parts of the theory survive that transition. The trace-completeness integrity constraint and the decision to refuse a second encoding of the rules are both answers to problems that only appeared once the system had to be trusted by someone submitting its output to an aviation authority.

The SORA encoding and an accompanying technical write-up are intended for release as an open artifact, since a publicly auditable formalisation of a published safety methodology has value independent of the product built on it.

## 16. Complete codebase structure

Generated files and dependency directories (`node_modules/`, `.venv/`, `.next/`, `out/`, `openapi.json`) are excluded; everything tracked in the repository is below.

```
sora-copilot/
├── README.md                               this document
├── PLAN.md                                 phase-by-phase build state, decisions, blockers
├── .env.example                            every variable for both halves, annotated
├── .gitignore
│
├── backend/                                FastAPI service + the symbolic engine
│   ├── README.md                           backend technical documentation
│   ├── pyproject.toml                      dependencies, ruff, mypy --strict, pytest, package data
│   ├── Makefile                            dev · test · lint · fmt · rulebase · openapi · migrate · smoke
│   ├── main.py                             entry point: `python main.py [--port N] [--prod]`
│   │
│   ├── app/
│   │   ├── main.py                         FastAPI app, CORS, RFC 7807 handlers, startup banner
│   │   ├── config.py                       pydantic-settings; production refuses to start under-configured
│   │   ├── deps.py                         JWT verification and org scoping — the authorisation gate
│   │   ├── problem.py                      RFC 7807 problem+json with a machine-readable `code`
│   │   │
│   │   ├── domain/                         Pydantic vocabulary shared by engine, API and frontend
│   │   │   ├── common.py                   enums, thresholds, Citation, GeoJSONPolygon, disclaimer
│   │   │   ├── mission.py                  Mission, OperationalVolume, mitigation claims
│   │   │   ├── determination.py            Determination, the computed chain
│   │   │   ├── oso.py                      Operational Safety Objectives and robustness
│   │   │   ├── trace.py                    TraceNode — the derivation graph
│   │   │   └── fields.py                   field labels and the proposable-field allowlist
│   │   │
│   │   ├── engine/                         PURE: stdlib, clingo, clorm, z3, pydantic, app.domain only
│   │   │   ├── runner.py                   facts in → Determination out; --models=1, loud failures
│   │   │   ├── facts.py                    Mission → ground atoms
│   │   │   ├── trace.py                    justification atoms → the derivation tree
│   │   │   ├── scale.py                    dimension and speed banding
│   │   │   ├── counterfactual.py           bounded combination search over the real engine
│   │   │   ├── cli.py                      `python -m app.engine.cli mission.json`
│   │   │   └── rulebase/
│   │   │       ├── loader.py               CSV tables + provenance + verified flags
│   │   │       ├── generate.py             CSV → clingo fact files (never hand-edited)
│   │   │       └── sora_2_5/
│   │   │           ├── VERSION             the rulebase version determinations pin to
│   │   │           ├── CHANGELOG.md        what changed between rulebase versions, and why
│   │   │           ├── 00_core.lp          declarations, the defeasible-override pattern
│   │   │           ├── 10_igrc.lp          intrinsic ground risk class
│   │   │           ├── 20_mitigations.lp   M1(A)/M1(B)/M1(C)/M2 adjustments → final GRC
│   │   │           ├── 30_arc.lp           initial and residual air risk class
│   │   │           ├── 40_sail.lp          the GRC × ARC → SAIL matrix
│   │   │           ├── 50_oso.lp           objective expansion with robustness levels
│   │   │           ├── 60_containment.lp   containment tiers and adjacent-area requirements
│   │   │           ├── 70_sts_pdra.lp      STS/PDRA override contract (none transcribed yet)
│   │   │           ├── 90_national_at.lp   Austria (Austro Control)
│   │   │           ├── 90_national_de.lp   Germany (LBA) — baseline only, nothing transcribed
│   │   │           └── tables/             every regulatory value, transcribed with provenance
│   │   │               ├── README.md       what a row must carry to be usable
│   │   │               ├── igrc.csv · igrc_columns.csv · thresholds.csv
│   │   │               ├── m1_m2.csv · arc.csv · arc_residual.csv · sail.csv
│   │   │               ├── oso.csv · containment.csv · tmpr.csv · buffers.csv
│   │   │               ├── citations.csv   document, section and page for each table
│   │   │               ├── density_environment_hint.csv   ours, not the regulation's
│   │   │               └── cf_costs.csv    counterfactual effort cost — ours, ordering only
│   │   │
│   │   ├── services/                       orchestration; stateful, impure, outside the engine
│   │   │   ├── determination.py            the confirmed-facts gate into the engine
│   │   │   ├── geo.py                      volumes, equal-area reprojection, density bands
│   │   │   ├── llm.py                      the ONLY module permitted to import `anthropic`
│   │   │   ├── intake.py                   proposed facts, confirmation lifecycle
│   │   │   ├── extract.py                  deterministic fact extraction — the no-LLM fallback
│   │   │   ├── dossier.py                  dossier content assembly
│   │   │   ├── docwriter.py                one content path rendered to DOCX and PDF
│   │   │   ├── mapimage.py                 the volume chart drawn into the dossier
│   │   │   ├── fonts.py                    bundled DejaVu, so documents render identically
│   │   │   ├── storage.py                  private buckets and backend-minted signed URLs
│   │   │   ├── billing.py                  Stripe checkout and the idempotent webhook
│   │   │   ├── plans.py                    tiers, seats, dossier credits, entitlements
│   │   │   └── demo.py                     the worked example, built through the real engine
│   │   │
│   │   ├── api/v1/                         routers; transport only
│   │   │   ├── schemas.py                  request and response models (the OpenAPI surface)
│   │   │   ├── deps_api.py                 shared router dependencies
│   │   │   ├── health.py                   /healthz and /healthz/deep
│   │   │   ├── orgs.py · drones.py · operations.py
│   │   │   ├── determine.py                run the chain, read determinations
│   │   │   ├── geo.py                      derive volumes, sample and confirm density
│   │   │   ├── intake_chat.py              conversational intake, proposals only
│   │   │   ├── dossier.py                  generate and download the dossier
│   │   │   ├── national.py                 country packs
│   │   │   ├── rulebase.py                 what the engine is reasoning with, and what is verified
│   │   │   ├── billing.py                  checkout, portal, webhook
│   │   │   ├── demo.py                     seed the worked example
│   │   │   ├── gate.py                     plan gating — the single 402 refusal shape
│   │   │   └── public.py                   the free category checker, unauthenticated
│   │   │
│   │   ├── national/                       the administrative half of an application
│   │   │   ├── models.py · loader.py
│   │   │   └── packs/  eu.json · at.json (Austria) · de.json (stub)
│   │   │
│   │   ├── db/
│   │   │   ├── client.py                   Supabase service-role client (PostgREST)
│   │   │   ├── repo.py · supabase_repo.py  the repository interface and its implementation
│   │   │   └── migrations/                 numbered SQL, applied in order
│   │   │       ├── README.md
│   │   │       ├── 001_init.sql            postgis, pgcrypto, every table with RLS, buckets
│   │   │       ├── 002_billing.sql         subscriptions, credits, webhook idempotency
│   │   │       ├── 003_invites.sql         organisation invitations and seats
│   │   │       ├── 004_rulebase_rc2.sql · 005_rulebase_2_5_1.sql
│   │   │       └── bundle.sql              the five concatenated, for the Supabase SQL editor
│   │   │
│   │   └── assets/fonts/                   DejaVu Sans + licence, bundled for deterministic PDFs
│   │
│   ├── scripts/
│   │   ├── build_rulebase.py               CSV → .lp; --strict fails on any unverified table
│   │   ├── bundle_migrations.py            regenerate bundle.sql
│   │   ├── export_openapi.py               write openapi.json, the frontend client's input
│   │   ├── migrate.py                      apply migrations, with a ledger and --baseline
│   │   ├── sample_dossier.py               render a dossier locally
│   │   └── smoke.sh                        walk the whole product against a running API
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_boundary.py                the neurosymbolic boundary, enforced by AST walk
│       ├── test_engine_golden.py           worked examples; a change may not land one failing
│       ├── test_engine_determinism.py      more than one answer set is a rulebase defect
│       ├── test_engine_trace.py            every conclusion carries its justification
│       ├── test_engine_counterfactual.py   minimality and ranking of suggestions
│       ├── test_rulebase_tables.py         provenance, verified flags, malformed rows
│       ├── test_domain.py · test_national.py · test_migrations.py
│       ├── test_api_flow.py                intake → determination → dossier, end to end
│       ├── test_api_intake.py · test_api_dossier.py · test_api_billing.py
│       ├── test_api_plans.py · test_api_seats.py · test_api_demo.py
│       ├── test_health.py · test_packaging.py · test_env_template.py
│       ├── test_media_assets.py · test_media_guide.py
│       └── golden/                         17 worked missions, including refusal cases
│
├── frontend/                               Next.js 15, App Router, static export
│   ├── README.md                           frontend technical documentation
│   ├── package.json                        dev · build · lint · gen:api · smoke
│   ├── next.config.ts                      output: "export", trailing slashes, no image optimisation
│   ├── tsconfig.json · postcss.config.mjs
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx · globals.css · error.tsx · not-found.tsx
│   │   │   ├── (marketing)/                page.tsx · pricing · legal · checker (free, no account)
│   │   │   ├── (auth)/signin/              email and magic link, completed in the browser
│   │   │   └── app/                        the authenticated product
│   │   │       ├── layout.tsx · page.tsx   shell and dashboard
│   │   │       ├── new/                    the intake wizard route
│   │   │       ├── operations/view/        the verdict surface
│   │   │       ├── dossiers/ · fleet/ · authority/ · settings/
│   │   │       └── overlays/ · states/     design reference routes
│   │   │
│   │   ├── components/
│   │   │   ├── wizard/                     Wizard · WizardStepper · IntakePanel · FactChip · MitigationCard
│   │   │   ├── verdict/                    Verdict · Chain · TraceTree · GapAnalysis · OsoDrawer
│   │   │   ├── map/                        MapVolumeEditor · MapPanels
│   │   │   ├── app/                        Shell · AuthGate · BillingPanel · MembersPanel · EmptyState
│   │   │   ├── marketing/                  Chrome · Tiers · Faq
│   │   │   ├── ui/                         Button · Dialog · Field
│   │   │   └── Brand · SailBadge · MediaSlot · Toast · PlanLimit · ComputationProgress
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                      RFC 7807 problems, cold-start retry, warming state
│   │   │   ├── api-client.ts               the typed surface, built on the generated types
│   │   │   ├── api-types.ts                GENERATED from backend/openapi.json
│   │   │   ├── auth.tsx · supabase.ts      session state, magic link, anon key only
│   │   │   ├── query.tsx · hooks.ts        React Query client and shared hooks
│   │   │   ├── geo.ts · upload.ts          GeoJSON helpers, evidence upload
│   │   │   ├── env.ts                      public env, validated once at build time
│   │   │   ├── prefs.tsx · cn.ts
│   │   │   └── media-manifest.ts           one registry entry per media slot
│   │   │
│   │   ├── data/                           marketing.ts · oso.ts
│   │   └── styles/tokens.css               the token system; mirrors tailwind.theme.ts
│   │
│   ├── public/media/                       hero, feature and empty-state assets
│   └── scripts/
│       ├── copy-maplibre-worker.mjs        pre-build; without it the map renders nothing
│       ├── smoke-ui.mjs                    real browser, geometry assertions, not DOM presence
│       └── make-media.mjs · media/studio.mjs
│
├── docs/
│   ├── ARCHITECTURE.md                     the architecture record and the boundary narrative
│   ├── RULEBASE.md                         transcription governance and verification
│   ├── SORA_Build_Spec.md                  the build specification the phases follow
│   ├── Deployment Guide.md                 Supabase → backend → frontend, in order
│   ├── Supabase Setup.md                   schema, auth, storage, with no terminal
│   ├── Third Party Setup Guide.md          which dashboard every credential comes from
│   ├── ENV Example.md                      what each variable does
│   ├── Media Setup Guide.md                the media slots and what fills them
│   ├── Final Manual Task.md                what the table transcription changed
│   └── HANDOFF-design-phase.md
│
└── design/                                 approved design system and screens — READ ONLY
    ├── HANDOFF.md · chats/
    └── project/
        ├── design-plan.md · components.md · motion.md · media-manifest.md
        ├── tokens.css · tailwind.theme.ts · support.js
        ├── *.dc.html                       the approved prototypes (SORA Copilot · SailBadge · MediaSlot)
        ├── screenshots/                    the approved reference screens
        ├── uploads/SORA Design Brief.md
        └── _ds/dronex-design-system-.../   the inherited design system and its tokens
```

## 17. Current state and roadmap

**Live and in production:** the SORA 2.5 core chain with full derivation traces, every regulatory table transcribed and verified against the adopted text; the geospatial layer with operator-confirmed density classification; the intake wizard and map-based volume editor; the verdict surface with derivation tree and gap analysis; the counterfactual advisor; dossier export with justification appendix; the Austrian country pack, marked unverified throughout by design, since it is this project's reading of the Austro Control process rather than a transcription of a published annex; the free category checker; payments.

**Next:** the German annex and further national packs, automated geographical zone ingestion from published ED-269 feeds, the first Standard Scenario and Predefined Risk Assessment transcriptions, which the routing layer is already encoded to accept, a bundled population raster behind the density sampling interface, the regulatory impact replay running continuously against stored operations as an alerting pipeline, a shared mitigation evidence library for multi-pilot organisations, and an API surface for integration with existing drone operations platforms.

## 18. Disclaimer

SORA Copilot prepares and verifies risk assessments and explains the methodology. The national aviation authority grants the operational authorisation. The system does not represent its users before any authority, makes no claim about the outcome of any application, and states this wherever it could otherwise be inferred.
