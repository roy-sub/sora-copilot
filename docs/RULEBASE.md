# The rulebase — how to add or verify a rule

## The absolute rule

**Do not invent regulatory values.** Every number comes from a transcribed official
source. A plausible guess in a compliance product is worse than a visible gap, because a
gap gets filled and a guess gets submitted to an authority.

Where a table has not been transcribed yet, the seed values stay in place and are marked
UNVERIFIED **everywhere**: in the CSV header, in `Determination.warnings`, and as a
banner on the verdict screen.

**As of rulebase 2.5.1 no table is a seed any more.** All fourteen are transcribed from
the adopted text, so no determination carries an UNVERIFIED warning. The machinery above
stays, because the next amendment will arrive before its transcription does.

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
# adopted_by: EASA ED Decision 2025/018/R of 29 September 2025 — AMC and GM to …
# basis: What was actually checked, and against which source. Required when verified.
# note: A note may wrap across several lines; continuation lines are any # line
#       that is not "key: value", so a note can contain a colon.
final_grc,arc_a,arc_b,arc_c,arc_d
2,I,II,IV,VI
```

`table`, `document`, `version` and `section` are required. `verified` must be exactly
`true` or `false`. A table missing a required field, or with a row wider than its header,
or with no rows at all, **raises** — it is never read partially.

**Every table has to answer "how do you know?".** A table claiming `verified: true` must
also carry `basis:` — one sentence naming what was checked and against which source — and
the loader refuses it without one, so verification cannot be a one-word edit. A table
saying `verified: false` must carry `needs:` — the document *and* the specific open
question — because that sentence is what the operator reads in the verdict banner, and
"something here is unverified" is not a work item while "Figure 4, all thirteen branches"
is. `adopted_by:` records how the EU adopted the source, which is what makes the table
citable in a dossier read by an EU authority.

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
3. Set `verified: true` **in that table only**, and write `basis:` saying what you
   checked against what. Drop `needs:`. Verification is per table, one at a time.
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
transcription is done.

## The source documents

SORA 2.5 is not merely a JARUS guideline in the EU any more. **EASA ED Decision
2025/018/R of 30 September 2025** issues the whole SORA 2.5 package as AMC and GM to
Regulation (EU) 2019/947 (Issue 1, Amendment 4), consolidated in the *Easy Access Rules
for Unmanned Aircraft Systems*, revision of June 2026. That consolidated book is the
source every regulatory table is transcribed from, and `adopted_by:` records the ED
Decision that adopted it, because a dossier is read by an EU authority and "JARUS says
so" is a weaker citation than "this is the AMC".

The book was downloaded over a verified TLS connection, extracted with `pdftotext`, and
read page by page. Every page number in a `page:` field and in a `basis:` sentence is the
book's own printed page, so a reviewer can open the PDF at that page and see the table.

| Section of the Easy Access Rules | Page | Transcribed into |
|---|---|---|
| AMC1 Article 11, S.4.2 Step #2 — Table 1 | 63 | `igrc`, `igrc_columns`, and the 250 g row of `thresholds` |
| AMC1 Article 11, S.4.3 Step #3 — Table 5 | 67 | `m1_m2` |
| AMC1 Article 11, S.4.3 Step #3 — certified-category ceiling | 68 | `thresholds` |
| AMC1 Article 11, S.4.6 Step #6 — Table 6 | 73 | `tmpr` |
| AMC1 Article 11, S.4.7 Step #7 — Table 3 | 75 | `sail` |
| AMC1 Article 11, S.4.8 Step #8 — adjacent area, S.4.8.3(b) | 76 | `thresholds` |
| AMC1 Article 11, S.4.8 Step #8 — Tables 8 to 13 | 77–78 | `containment` |
| AMC1 Article 11, S.4.9 Step #9 — Table 14 | 81–82 | `oso` |
| AMC1 Article 11 Annex A — A.5.2 | 104–107 | `buffers` |
| AMC1 Article 11 Annex C — Table C.1 | 128 | `arc`, and the altitude bands of `thresholds` |
| AMC1 Article 11 Annex C — Table C.2 | 129 | `arc_residual` |
| Austro Control publication | — | `90_national_at.lp` |

Annexes B and E carry the robustness criteria behind the mitigations and the OSOs. The
engine does not model those criteria — it reports which objective is required at which
robustness, and the operator's evidence is what satisfies it — so no table transcribes
them, and `OSO_TEXT` in the frontend is explicitly labelled as our summary rather than
the clause.

## What is still a seed

Nothing. All fourteen tables report `verified: true`; run `make rulebase` for the live
list, and `make rulebase --strict` passes.

Eleven of the fourteen are regulatory, transcribed from the pages above. Eight of those
eleven had not been checked before 2.5.1, and **seven of the eight were wrong** — six of
them in ways that change a determination, the seventh in the volumes drawn on the map:

- `arc` had ten branches where Table C.1 has twelve. The Mode-S Veil / transponder
  mandatory zone classes (AEC 2 and AEC 7) and the above-FL600 class (AEC 11) were
  missing outright, so an operation in a TMZ was given the wrong initial ARC.
- `arc_residual` lowered any ARC by one class for any claimed strategic mitigation.
  Table C.2 sells a reduction for a *demonstrated* local density rating, not for a
  claim, and ARC-d can fall two classes rather than one. The worked example moved from
  SAIL III to SAIL IV until a demonstrated rating was supplied.
- `containment` was a two-tier guess recorded with an open conflict. S.4.8.1(c) names
  three levels — low, medium and high — so the Netherlands ILT AltMoC's basic/enhanced
  was a national exemption, not SORA 2.5. Step #8 now computes a level.
- `oso` matched the SORA 2.0 grid on sixteen of seventeen rows; OSO#04 read
  low/medium/high at SAIL IV/V/VI where Table 14 says medium/high/high.
- `m1_m2` was missing M1(B) operational restrictions entirely — the gap its own note
  flagged — which is a −1 at medium and a −2 at high robustness.
- `buffers` had the reaction time and the bank angle right and the rest wrong: the
  horizontal contingency volume is the sum of five terms, not one position error, and
  the ground risk buffer is H_CV + CD/2, not H_CV alone.
- `thresholds` moved the altitude band from 152.4 m to **150 m**. Table C.1 writes every
  altitude row as "150 m (~500 ft) AGL": 150 m is the figure and 500 ft is the
  approximation of it, which is the opposite of what PLAN.md §0 had decided.

`tmpr` was the one that had been right by luck; it is now the table's own four rows.

The three non-regulatory tables are verified for a different reason and must never be
read as a regulatory claim. `cf_costs.csv`, `density_environment_hint.csv` and
`citations.csv` are **ours, not the regulation's**: effort weights that only rank
counterfactual suggestions, thresholds that only prefill a form field the operator then
confirms, and an index. None of them can change an iGRC, a GRC, an ARC, a SAIL, an OSO or
a containment result, all of which come from the clingo rules and the regulatory tables
alone. Their `basis:` says exactly that, in those words, so the flag cannot later be
mistaken for a transcription.

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
