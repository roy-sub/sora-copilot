# Rulebase changelog

Every change to a `.csv` table or a `.lp` rule gets an entry here and a `VERSION` bump.
Determinations pin the version they were computed against, so a bump never alters a
record that already exists.

The `verified` flag in each table header is the only thing that decides whether a
determination carries an UNVERIFIED warning. Flipping it to `true` is a deliberate act
that requires the official document in hand — see `docs/RULEBASE.md`.

## 2.5.0-rc1 — unreleased

Seed skeleton. **No table is verified.** Values are placeholders transcribed from the
build spec's seed SAIL matrix and from the shapes in SORA 2.5 as understood during the
design phase. They exist so the pipeline can be built and tested end to end; they are
not fit for a real assessment and the UI says so.

Awaiting, to verify: JARUS SORA 2.5 main body, Annexes B, C and D, and the Austrian
national annex. Files to fill in are listed in `PLAN.md` §8.
