"""The transcribed tables must be parseable, provenanced, and honest about verification.

Hard rule 3: no invented regulatory values. These tests cannot tell a true value from a
false one — only the official document can. What they can do is guarantee that every
table says where it came from, that an unverified table is loudly unverified, and that
the seed values match the shapes the spec and the regulation describe.
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


def test_every_expected_table_loads() -> None:
    assert set(load_rulebase()) == EXPECTED_TABLES


def test_version_file_matches_the_spec_seed() -> None:
    assert rulebase_version() == "2.5.0-rc1"


@pytest.mark.parametrize("name", sorted(EXPECTED_TABLES))
def test_table_declares_its_provenance(name: str) -> None:
    t = load_rulebase()[name]
    assert t.document, f"{name} does not name the document it was transcribed from"
    assert t.section, f"{name} does not name the section"
    assert t.rows, f"{name} has no rows"


def test_no_table_claims_to_be_verified_yet() -> None:
    """Every table is a seed until the owner supplies the official documents.

    This test is expected to change — deliberately, one table at a time, together with a
    CHANGELOG entry. It exists so verification cannot happen by accident.
    """
    assert unverified_tables() == sorted(EXPECTED_TABLES)


def test_unverified_tables_produce_a_warning_the_user_will_see() -> None:
    warnings = warnings_for(["igrc", "sail"])
    assert len(warnings) == 2
    assert all(w.startswith("UNVERIFIED:") for w in warnings)
    assert all("must not be submitted" in w for w in warnings)


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


def test_thresholds_use_the_regulation_not_a_round_number() -> None:
    """500 ft is 152.4 m, which is 15240 cm. The design copy's 150 m is not the rule."""
    rows = {r["key"]: r for r in load_rulebase()["thresholds"].rows}
    assert int(rows["altitude_band_500ft"]["value"]) == 15240
    assert rows["altitude_band_500ft"]["unit"] == "cm"
    assert int(rows["small_ua_mtom"]["value"]) == 250
    assert int(rows["grc_certified_ceiling"]["value"]) == 7


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


def test_containment_yields_no_level_while_unverified() -> None:
    """We will not show a containment level we cannot source (PLAN.md §6.4)."""
    for row in load_rulebase()["containment"].rows:
        assert row["level"] == ""
        assert row["assessment_required"] == "true"


def test_unclaimable_mitigation_levels_are_empty_and_marked() -> None:
    rows = {(r["kind"], r["robustness"]): r for r in load_rulebase()["m1_m2"].rows}
    # M2 has no low level; M1 sheltering has no high level.
    assert rows[("m2_impact", "low")]["grc_delta"] == ""
    assert rows[("m2_impact", "low")]["precondition"] == "not_claimable"
    assert rows[("m1_strategic", "high")]["grc_delta"] == ""


def test_every_rule_id_in_a_table_has_a_citation() -> None:
    """A trace node can never render without a citation, so the index must be complete."""
    tables = load_rulebase()
    cited = {r["rule_id"] for r in tables["citations"].rows}
    for name in ("arc", "arc_residual", "containment", "tmpr"):
        for row in tables[name].rows:
            rule_id = row.get("rule_id", "")
            assert rule_id in cited, f"{name}.csv rule_id {rule_id!r} is missing from citations.csv"


def test_cf_costs_is_marked_as_ours_not_the_regulations() -> None:
    t = load_rulebase()["cf_costs"]
    assert "not a regulatory source" in t.document
    assert not t.verified


def test_a_table_without_a_verified_header_is_rejected(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("# table: bad\n# document: d\n# version: 1\n# section: s\nk,v\n1,2\n")
    with pytest.raises(RulebaseError, match="verified"):
        load_table(bad)


def test_a_table_with_no_rows_is_rejected(tmp_path) -> None:
    bad = tmp_path / "empty.csv"
    bad.write_text("# table: e\n# document: d\n# version: 1\n# section: s\n# verified: false\nk,v\n")
    with pytest.raises(RulebaseError, match="no data rows"):
        load_table(bad)
