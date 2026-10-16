# Rulebase changelog

Every change to a `.csv` table or a `.lp` rule gets an entry here and a `VERSION` bump.
Determinations pin the version they were computed against, so a bump never alters a
record that already exists.

The `verified` flag in each table header is the only thing that decides whether a
determination carries an UNVERIFIED warning. Flipping it to `true` is a deliberate act:
the loader refuses a table that claims verification without a `basis:` line saying what
was checked and against which source, and refuses an unverified one without a `needs:`
line saying what is still missing — see `docs/RULEBASE.md`.

## 2.5.0-rc2 — unreleased

**Three regulatory tables verified, and every table now answers "how do you know?".**

Verified against the JARUS SORA 2.5 Main Body release (`JAR_doc_25`) cross-checked with
the Norwegian CAA's own SORA 2.5 calculator, an authority implementation of the same
tables, and with JARUS Annex F:

- `igrc` — every cell, every population density band, and the `>50 000 ppl/km²` cut-off
  beyond which the operation is not part of SORA. Annex F confirms the final table has
  no iGRC 11, so the scale caps at 10.
- `igrc_columns` — the five dimension/speed pairs: 1 m / 25 m/s, 3 m / 35 m/s,
  8 m / 75 m/s, 20 m / 120 m/s, 40 m / 200 m/s. The 6 m / 250 m/s columns that circulate
  in some write-ups are from an earlier draft and were rejected.
- `sail` — Table 7, SAIL determination, plus the rule that a final GRC above 7 leaves
  SORA for the certified category.

`cf_costs`, `density_environment_hint` and `citations` are marked verified for a
different reason: they are the product's own data, not transcriptions, and their basis
says so in terms that cannot be mistaken for a regulatory claim.

Every regulatory table now also records **how the EU adopted its source**: EASA ED
Decision 2025/018/R of 29 September 2025 issues the SORA 2.5 package as AMC and GM to
Regulation (EU) 2019/947, consolidated in the Easy Access Rules for UAS, revision of
June 2026. That matters for a dossier read by an EU authority, and it was missing.

Research also found real defects in the seeds, now written into each table's `needs:`
rather than left as a vague doubt:

- `arc` is **structurally short**, not merely unchecked. SORA 2.5 aggregates the airspace
  into *thirteen* collision risk categories assigned from the decision tree at Figure 4;
  the seed is a ten-branch reconstruction. Step #4 also allows a published collision risk
  map to set the initial ARC instead of the tree, which the engine does not model.
- `containment` sits on a genuine conflict in the published material: several sources say
  SORA 2.5 replaced basic/enhanced with three tiers (low, medium, high), while the
  Netherlands ILT AltMoC of 6 September 2024, written against SORA 2.5, says the two
  levels remain. Two anchors are established: basic containment is "no probable failure
  of the UAS or any external system supporting the operation shall lead to operation
  outside of the operational volume", and the rate the argument must meet is 10^-SAIL per
  flight hour. The table still yields `assessment_required` and no level.
- `oso` has the right seventeen rows — the count fell from 24 by merging, with OSO#10
  folding into OSO#05 — but its robustness grid is the SORA 2.0 grid restricted to the
  survivors, which is a guess. The real one is the Step #9 table, where `NR` marks an OSO
  not required at a SAIL.
- `m1_m2` needs Main Body Table 5, "Mitigations for Final GRC determination".
- `thresholds` is three-quarters done: the 250 g / 25 m/s provision and the GRC-above-7
  boundary are confirmed; the 500 ft AGL band boundary is not, because it lives in
  Figure 4.
- `buffers` has the 1:1 ground risk buffer sourced from the Main Body; the
  contingency-volume parameters and the adjacent-area ring are not.

The eight remaining tables could not be closed in this pass because the container's
network policy blocks `jarus-rpas.org` and `easa.europa.eu`, so the release PDFs could
not be opened. That is also why no table cites a page number: sections and table numbers
are cited instead, and each `basis:` says so rather than implying a page was read.

## 2.5.0-rc1 — superseded

Seed skeleton. **No table is verified.** Values are placeholders transcribed from the
build spec's seed SAIL matrix and from the shapes in SORA 2.5 as understood during the
design phase. They exist so the pipeline can be built and tested end to end; they are
not fit for a real assessment and the UI says so.

Awaiting, to verify: JARUS SORA 2.5 main body, Annexes B, C and D, and the Austrian
national annex. Files to fill in are listed in `PLAN.md` §8.
