"""The transcribed tables must be parseable, provenanced, and honest about verification.

Hard rule 3: no invented regulatory values. These tests cannot tell a true value from a
false one — only the official document can. What they can do is guarantee that every
table says where it came from, that an unverified table is loudly unverified, and that
the seed values match the shapes the spec and the regulation describe.

They also guarantee that verification cannot be claimed cheaply: a table that says
``verified: true`` must state its basis, and one that says false must state what it still
needs, so the operator's warning names the open question instead of only its existence.
"""

from __future__ import annotations

import pytest

from app.engine.rulebase.loader import (
    RulebaseError,
    load_rulebase,
    load_table,
    rulebase_version,
    unverified_tables,
    warnings_for,
)

EXPECTED_TABLES = {
    "arc",
    "arc_residual",
    "buffers",
    "cf_costs",
    "citations",
    "containment",
    "igrc",
    "density_environment_hint",
    "igrc_columns",
    "m1_m2",
    "oso",
    "sail",
    "thresholds",
    "tmpr",
}

#: Not transcribed from anything: the product's own weights, hints and index.
OURS = {"cf_costs", "citations", "density_environment_hint"}


def test_every_expected_table_loads() -> None:
    assert set(load_rulebase()) == EXPECTED_TABLES


def test_version_file_matches_the_spec_seed() -> None:
    assert rulebase_version() == "2.5.1"


@pytest.mark.parametrize("name", sorted(EXPECTED_TABLES))
def test_table_declares_its_provenance(name: str) -> None:
    t = load_rulebase()[name]
    assert t.document, f"{name} does not name the document it was transcribed from"
    assert t.section, f"{name} does not name the section"
    assert t.rows, f"{name} has no rows"


#: Nothing. Every table is transcribed from the EASA Easy Access Rules, June 2026
#: revision, which carries the SORA 2.5 package as adopted by ED Decision 2025/018/R.
STILL_SEEDS: set[str] = set()


def test_exactly_the_tables_we_have_checked_claim_verification() -> None:
    """Verification moves one table at a time, with a CHANGELOG entry and a basis.

    The set is empty now. It stays a test rather than being deleted because the next
    rulebase edition starts the cycle again, and because a table that silently lost its
    basis would otherwise reappear as a seed with nobody noticing.
    """
    assert unverified_tables() == sorted(STILL_SEEDS)


@pytest.mark.parametrize("name", sorted(EXPECTED_TABLES))
def test_a_table_answers_how_do_you_know(name: str) -> None:
    t = load_rulebase()[name]
    if t.verified:
        assert t.basis, f"{name} claims verification without saying what was checked"
        assert len(t.basis) > 60, f"{name}'s basis is too short to be a real answer"
    else:
        assert t.needs, f"{name} is unverified without saying what it needs"
        assert len(t.needs) > 60, f"{name}'s needs is too short to be actionable"


def test_no_table_produces_a_warning_any_more() -> None:
    """The whole chain is transcribed, so a determination carries no UNVERIFIED note."""
    assert warnings_for(sorted(EXPECTED_TABLES)) == []


def test_an_unverified_table_would_still_warn(tmp_path) -> None:
    """The machinery has to keep working for the next rulebase edition.

    Asserting "nothing warns" against a rulebase where nothing can warn would pass
    whether or not the warning still worked, so this builds a seed table and reads the
    sentence an operator would get.
    """
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "# table: seed\n# document: Some document\n# version: 1\n# section: Some section\n"
        "# verified: false\n# needs: The official text, which nobody has supplied, and in "
        "particular its Figure 4.\nk,v\n1,2\n",
        encoding="utf-8",
    )
    table = load_table(seed)
    warning = table.warning() or ""
    assert warning.startswith("UNVERIFIED:")
    assert "must not be submitted" in warning
    assert "Figure 4" in warning, "the warning carries the table's own open question"


def test_every_regulatory_table_records_the_eu_adoption() -> None:
    """SORA 2.5 is EU law through an ED Decision, and a dossier is read in the EU."""
    tables = load_rulebase()
    for name in EXPECTED_TABLES - OURS:
        assert tables[name].adopted_by, f"{name} does not record how the EU adopted it"
        assert "2025/018/R" in tables[name].adopted_by
        assert "2019/947" in tables[name].adopted_by


def test_sail_matrix_matches_the_spec_seed_shape() -> None:
    rows = {r["final_grc"]: r for r in load_rulebase()["sail"].rows}
    assert set(rows) == {"2", "3", "4", "5", "6", "7"}
    # Build spec §6.3: GRC ≤2 × ARC a → SAIL I; GRC 7 × any ARC → SAIL VI.
    assert rows["2"]["arc_a"] == "I"
    assert rows["2"]["arc_d"] == "VI"
    assert rows["7"]["arc_a"] == "VI"
    # ARC d is SAIL VI across the whole table in the seed matrix.
    assert {r["arc_d"] for r in rows.values()} == {"VI"}


def test_igrc_columns_keep_the_speed_limit() -> None:
    """SORA 2.5's iGRC columns are dimension AND speed pairs (PLAN.md §6.1).

    Dropping the speed limit would put a small, fast aircraft in the wrong column and
    therefore give it the wrong intrinsic ground risk.
    """
    rows = load_rulebase()["igrc_columns"].rows
    assert [int(r["col"]) for r in rows] == [1, 2, 3, 4, 5]
    assert [int(r["max_dimension_cm"]) for r in rows] == [100, 300, 800, 2000, 4000]
    assert [int(r["max_speed_cms"]) for r in rows] == [2500, 3500, 7500, 12000, 20000]


def test_igrc_columns_are_monotone() -> None:
    """Both limits must rise together, or "the first column where both hold" is wrong."""
    rows = load_rulebase()["igrc_columns"].rows
    dims = [int(r["max_dimension_cm"]) for r in rows]
    speeds = [int(r["max_speed_cms"]) for r in rows]
    assert dims == sorted(dims)
    assert speeds == sorted(speeds)


def test_igrc_band_indices_are_contiguous_and_ordered() -> None:
    rows = load_rulebase()["igrc"].rows
    assert [int(r["band_index"]) for r in rows] == list(range(len(rows)))


def test_exactly_one_igrc_band_is_unbounded() -> None:
    """The top band has no ceiling; every other band must have one."""
    rows = load_rulebase()["igrc"].rows
    unbounded = [r for r in rows if r["max_density"] == ""]
    assert len(unbounded) == 1
    assert unbounded[0]["density_band"] == "over_50000"


def test_thresholds_use_the_figure_the_table_prints() -> None:
    """Annex C Table C.1 writes "150 m (~500 ft) AGL" — 150 m is the figure.

    This test used to assert the opposite, 15240 cm, on the reading that 500 ft was the
    rule and 150 m the rounding. The adopted text settles it the other way.
    """
    rows = {r["key"]: r for r in load_rulebase()["thresholds"].rows}
    assert int(rows["altitude_band_150m"]["value"]) == 15_000
    assert rows["altitude_band_150m"]["unit"] == "cm"
    assert int(rows["altitude_fl600"]["value"]) == 1_828_800
    assert int(rows["small_ua_mtom"]["value"]) == 250
    assert int(rows["grc_certified_ceiling"]["value"]) == 7
    # Step #8's adjacent ground area: 3 minutes at maximum speed, floored and capped.
    assert int(rows["adjacent_area_seconds"]["value"]) == 180
    assert int(rows["adjacent_area_min"]["value"]) == 500_000
    assert int(rows["adjacent_area_max"]["value"]) == 3_500_000


def test_igrc_out_of_scope_cells_are_empty_not_zero() -> None:
    """An empty cell means 'not part of SORA', and must never be read as iGRC 0."""
    top = next(r for r in load_rulebase()["igrc"].rows if r["density_band"] == "over_50000")
    assert top["col_3"] == ""
    assert top["col_1"] == "7"


def test_no_igrc_cell_is_zero() -> None:
    """iGRC starts at 1. A 0 anywhere would mean a transcription slip read as a value."""
    for row in load_rulebase()["igrc"].rows:
        for col in range(1, 6):
            cell = row[f"col_{col}"]
            assert cell == "" or int(cell) >= 1, f"{row['density_band']} col_{col} = {cell!r}"


def test_assembly_is_not_a_density_band() -> None:
    """Assembly of people pins the top row; it is not a column (PLAN.md §6.2)."""
    bands = {r["density_band"] for r in load_rulebase()["igrc"].rows}
    assert "assembly_of_people" not in bands
    assert "over_50000" in bands


def test_oso_table_has_the_seventeen_sora_25_osos() -> None:
    """SORA 2.5 has 17 OSOs; the design copy's "~24" was SORA 2.0."""
    ids = [r["oso_id"] for r in load_rulebase()["oso"].rows]
    assert len(ids) == 17
    assert ids[0] == "OSO#01"
    assert "OSO#13" in ids
    assert "OSO#24" in ids
    # No OSO numbered 10-12, 14, 15, 21 or 22 in SORA 2.5.
    assert not {f"OSO#{n:02d}" for n in (10, 11, 12, 14, 15, 21, 22)} & set(ids)


def test_oso_robustness_values_are_from_the_enum() -> None:
    allowed = {"none", "low", "medium", "high"}
    for row in load_rulebase()["oso"].rows:
        for sail in ("sail_i", "sail_ii", "sail_iii", "sail_iv", "sail_v", "sail_vi"):
            assert row[sail] in allowed, f"{row['oso_id']} {sail} = {row[sail]!r}"


def test_oso_robustness_never_decreases_as_sail_rises() -> None:
    """A higher SAIL cannot require less of an OSO. Catches transcription slips."""
    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    for row in load_rulebase()["oso"].rows:
        levels = [order[row[c]] for c in ("sail_i", "sail_ii", "sail_iii", "sail_iv", "sail_v", "sail_vi")]
        assert levels == sorted(levels), f"{row['oso_id']} is not monotone: {levels}"


def test_containment_is_three_tiered_and_covers_six_tables() -> None:
    """S.4.8.1(c): low, medium and high. SORA 2.0's basic/enhanced is not this.

    This test used to assert that every containment row had NO level, because the seed
    could not source one. There are 156 cells now, across the six tables keyed by UA
    characteristic dimension.
    """
    rows = load_rulebase()["containment"].rows
    assert {r["level"] for r in rows} == {"low", "medium", "high", "out_of_scope"}
    assert {int(r["table_no"]) for r in rows} == {8, 9, 10, 11, 12, 13}
    assert {int(r["max_dimension_cm"]) for r in rows} == {100, 300, 800, 2000, 4000}
    assert {r["sail"] for r in rows} == {"I", "II", "III", "IV", "V", "VI"}
    # Only the 3 m pair asks the sheltering question; the rest state an assumption.
    assert {r["shelter"] for r in rows if int(r["table_no"]) in (9, 10)} == {"true", "false"}
    assert {r["shelter"] for r in rows if int(r["table_no"]) not in (9, 10)} == {"*"}


def test_unclaimable_mitigation_levels_are_empty_and_marked() -> None:
    rows = {(r["kind"], r["robustness"]): r for r in load_rulebase()["m1_m2"].rows}
    # Table 5: M2 has no low level; M1(A) sheltering has no high level.
    assert rows[("m2_impact", "low")]["grc_delta"] == ""
    assert rows[("m2_impact", "low")]["precondition"] == "not_claimable"
    assert rows[("m1_strategic", "high")]["grc_delta"] == ""


def test_table_5_has_all_four_mitigations_including_m1b() -> None:
    """M1(B), operational restrictions, was missing from the seed entirely.

    An operator could not claim a mitigation the regulation offers, which cost them up
    to two GRC — and the seed's own note said so without being able to fix it.
    """
    rows = {(r["kind"], r["robustness"]): r for r in load_rulebase()["m1_m2"].rows}
    assert rows[("m1_operational", "low")]["precondition"] == "not_claimable"
    assert rows[("m1_operational", "medium")]["grc_delta"] == "-1"
    assert rows[("m1_operational", "high")]["grc_delta"] == "-2"


def test_the_oso_grid_is_table_14_not_sora_2_0() -> None:
    """OSO#04 is where the two differ, so it is the row worth pinning."""
    rows = {r["oso_id"]: r for r in load_rulebase()["oso"].rows}
    assert len(rows) == 17
    oso4 = rows["OSO#04"]
    assert [oso4[f"sail_{s}"] for s in ("i", "ii", "iii", "iv", "v", "vi")] == [
        "none", "none", "none", "medium", "high", "high",
    ]


def test_every_rule_id_in_a_table_has_a_citation() -> None:
    """A trace node can never render without a citation, so the index must be complete."""
    tables = load_rulebase()
    cited = {r["rule_id"] for r in tables["citations"].rows}
    for name in ("arc", "arc_residual", "containment", "tmpr"):
        for row in tables[name].rows:
            rule_id = row.get("rule_id", "")
            assert rule_id in cited, f"{name}.csv rule_id {rule_id!r} is missing from citations.csv"


@pytest.mark.parametrize("name", sorted(OURS))
def test_our_own_tables_are_marked_as_ours_not_the_regulations(name: str) -> None:
    """These three are the product's own data. Saying so is the point of the field.

    They are `verified: true` because there is no official source to check them against
    — and the basis has to say exactly that, so nobody later mistakes the flag for a
    regulatory claim.
    """
    t = load_rulebase()[name]
    assert "SORA Copilot" in t.document
    assert t.verified
    assert "not a transcribed regulatory table" in (t.basis or "")
    assert "never be presented as one" in (t.basis or "")


def test_our_own_tables_cannot_reach_a_determination() -> None:
    """The guard behind the flag above: ours rank and prefill, they never decide."""
    basis = load_rulebase()["cf_costs"].basis or ""
    for word in ("iGRC", "GRC", "ARC", "SAIL", "OSO", "containment"):
        assert word in basis
    assert "clingo" in basis


def test_a_table_claiming_verification_without_a_basis_is_rejected(tmp_path) -> None:
    bad = tmp_path / "noBasis.csv"
    bad.write_text("# table: b\n# document: d\n# version: 1\n# section: s\n"
                   "# verified: true\nk,v\n1,2\n")
    with pytest.raises(RulebaseError, match="basis"):
        load_table(bad)


def test_an_unverified_table_without_a_needs_is_rejected(tmp_path) -> None:
    bad = tmp_path / "noNeeds.csv"
    bad.write_text("# table: b\n# document: d\n# version: 1\n# section: s\n"
                   "# verified: false\nk,v\n1,2\n")
    with pytest.raises(RulebaseError, match="needs"):
        load_table(bad)


def test_a_table_without_a_verified_header_is_rejected(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("# table: bad\n# document: d\n# version: 1\n# section: s\nk,v\n1,2\n")
    with pytest.raises(RulebaseError, match="verified"):
        load_table(bad)


def test_a_table_with_no_rows_is_rejected(tmp_path) -> None:
    bad = tmp_path / "empty.csv"
    bad.write_text("# table: e\n# document: d\n# version: 1\n# section: s\n"
                   "# verified: false\n# needs: " + "the official text, " * 4 + "\nk,v\n")
    with pytest.raises(RulebaseError, match="no data rows"):
        load_table(bad)
