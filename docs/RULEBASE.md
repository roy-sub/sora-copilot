# The rulebase — how to add or verify a rule

## The absolute rule

**Do not invent regulatory values.** Every number comes from a transcribed official
source. A plausible guess in a compliance product is worse than a visible gap, because a
gap gets filled and a guess gets submitted to an authority.

Where a table has not been transcribed yet, the seed values stay in place and are marked
UNVERIFIED **everywhere**: in the CSV header, in `Determination.warnings`, and as a
banner on the verdict screen.

## The pipeline

```
tables/*.csv            transcribed by a human, with provenance and a verified flag
    │
    │  scripts/build_rulebase.py — validates; refuses on a malformed row
    ▼
*.lp fact files         generated, never hand-edited
    │
    │  clingo rules in 00_core.lp … 90_national_*.lp reason over them
    ▼
answer set              exactly one; more than one is a bug
    │
    │  engine/trace.py reads because/3 atoms only
    ▼
Determination + Trace   every node cited, rulebase version pinned
```

## The CSV contract

Each table starts with a header block of `#` lines:

```csv
# table: sail
# document: JARUS SORA 2.5 main body
# version: 2.5
# section: SAIL determination matrix
# page: 42
# url: https://…
# verified: true
# note: A note may wrap across several lines; continuation lines are any # line
#       that is not "key: value", so a note can contain a colon.
final_grc,arc_a,arc_b,arc_c,arc_d
2,I,II,IV,VI
```

`table`, `document`, `version` and `section` are required. `verified` must be exactly
`true` or `false`. A table missing a required field, or with a row wider than its header,
or with no rows at all, **raises** — it is never read partially.

Conventions the loader and the tests rely on:

- **An empty cell is not zero.** In `igrc.csv` an empty cell means the combination is
  outside SORA and the operation needs the certified category. In `m1_m2.csv` an empty
  `grc_delta` with `precondition: not_claimable` means that robustness level cannot be
  claimed — the UI shows it disabled rather than hiding it, so the path to it stays visible.
- **`*` is a wildcard**, read as "any", never as data.
- **Ordered tables carry a `priority` column** (`arc.csv`), and the first row whose
  conditions all hold wins. That is how a decision tree's precedence survives being
  flattened into rows.

## Verifying a table

1. Get the official document. Read the actual table, not a summary of it.
2. Correct the values in the CSV. Fill in `page` and `url`.
3. Set `verified: true` **in that table only**. Verification is per table, one at a time.
4. Set `verified` on the matching rows of `citations.csv`.
5. Run `make rulebase` — it reports what is still a seed.
6. Run `make test`. Golden cases must pass. If a golden case now fails, the *case* may
   have encoded the seed's mistake: re-derive its expected values from the document
   before touching the engine.
7. Add a `CHANGELOG.md` entry and bump `VERSION`.
8. Insert the new version into `rulebase_versions` and flip `is_current`. Existing
   determinations keep the version they were computed against — a bump never rewrites a
   record.

`make rulebase --strict` fails when any table is unverified. Use it in CI once the
transcription is done; it is not useful before then, because the honest state today is
that nothing is verified.

## What is still a seed

Everything. Run `make rulebase` for the list, which is also in `PLAN.md` §8. To verify
them, the following are needed:

| Document | Verifies |
|---|---|
| JARUS SORA 2.5 main body | `igrc.csv`, `sail.csv`, `oso.csv`, `containment.csv` |
| JARUS SORA 2.5 Annex B | `m1_m2.csv`, `buffers.csv` |
| JARUS SORA 2.5 Annex C | `arc.csv`, `arc_residual.csv` |
| JARUS SORA 2.5 Annex D | `tmpr.csv` |
| Austrian national annex | `90_national_at.lp` |

`cf_costs.csv` is **ours, not the regulation's**. It only ranks counterfactual
suggestions and never touches a determination, so verifying it means the owner agreeing
the effort weights are sensible, not finding them in a document.

## ASP conventions

Predicates are lower snake case: `fact/2`, `igrc/1`, `grc/1`, `arc_initial/1`,
`arc_residual/1`, `sail/1`, `oso_required/2`, `containment/1`.

**Every derived atom carries a justification.** For each rule concluding `X`, derive
`because(X, RuleId, Premises)` in the same rule body:

```prolog
% default → override pattern; use it consistently
grc(V) :- grc_default(V), not grc_overridden.
grc(V) :- grc_override(V, _RuleId).
grc_overridden :- grc_override(_, _).
because(grc(V), RuleId, (grc_default(V),)) :-
    grc(V), grc_default(V), not grc_overridden, RuleId = "sora25.grc.default".
```

And an integrity constraint makes an unjustified conclusion unsatisfiable, so the engine
cannot return a value it cannot explain.

Rule ids are stable strings: `sora25.<section>.<rule>` for core, `at.<rule>` / `de.<rule>`
for national, `pdra.<id>.<rule>` for shortcuts. Every id maps to exactly one row of
`citations.csv`, and the trace formatter refuses an id that is missing from it — which is
how a node can never render without a citation.

## Golden tests

`backend/tests/golden/` holds worked examples: a JSON mission, the expected iGRC, GRC,
ARC, SAIL and OSO set, and the rulebase version the case was verified against. Sources
are published SORA worked examples, EASA guidance material, and any case the owner
supplies.

**An engine change may not land with a failing golden case.** Not "may not ship" — may
not land.
