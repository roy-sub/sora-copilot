"""The country packs: honest about what they do not know, and tied to a real SAIL.

The pack is the one place in the product where this project wrote prose about another
country's administrative process. These tests are what stop that prose from hardening
into something the UI presents as regulation (build spec HARD RULE 3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.national import PackError, available, load_pack, tailor
from app.national.loader import PACKS_ROOT, SAIL_ORDER

# ------------------------------------------------------------------ the packs themselves


def test_every_pack_on_disk_loads() -> None:
    packs = available()
    assert {p.country for p in packs} == {"AT", "DE", "EU"}


def test_austria_pack_is_the_one_phase_7_asks_for() -> None:
    pack = load_pack("AT")
    assert pack.authority == "Austro Control GmbH"
    kinds = {i.kind for i in pack.items}
    # "Austro Control process notes and forms checklist" — all three must be present.
    assert {"process", "form", "attachment"} <= kinds


def test_no_pack_claims_to_be_complete() -> None:
    """Until an authority's publication is transcribed, `complete` is false everywhere."""
    for pack in available():
        assert pack.complete is False, f"{pack.country} claims completeness"


def test_every_item_is_marked_unverified_and_says_where_to_look() -> None:
    """The owner has supplied no authority document, so nothing may read as official."""
    for pack in available():
        for item in pack.items:
            assert item.provenance == "seed", f"{item.id} claims official provenance"
            assert item.source, f"{item.id} is unverified but does not say where to verify it"


def test_an_unverified_pack_produces_a_warning_naming_the_authority() -> None:
    warning = load_pack("AT").warning()
    assert warning is not None
    assert warning.startswith("UNVERIFIED")
    assert "Austro Control GmbH" in warning
    assert "14 of 14" in warning


def test_a_fully_official_pack_produces_no_warning() -> None:
    """Guard the guard: the banner must disappear once the pack is transcribed."""
    pack = load_pack("AT")
    official = pack.model_copy(
        update={
            "items": tuple(
                i.model_copy(update={"provenance": "official", "source": "doc §1"})
                for i in pack.items
            )
        }
    )
    assert official.warning() is None
    assert official.unverified_ids == ()


def test_packs_never_quote_a_number_they_have_not_verified() -> None:
    """A fee, a duration or a sum insured is a regulatory value. None may be invented.

    The seeds deliberately say "ask the authority" instead. This test is the thing that
    keeps a plausible-looking figure from being typed in later without a source.
    """
    import re

    money_or_time = re.compile(
        r"(€\s?\d|\d+\s?(?:EUR|euro)|\d+\s?(?:working\s+)?(?:days?|weeks?|months?))",
        re.IGNORECASE,
    )
    offenders = [
        (i.id, m.group(0))
        for pack in available()
        for i in pack.items
        if not i.verified
        for m in [money_or_time.search(f"{i.title} {i.detail}")]
        if m
    ]
    assert not offenders, f"unverified items quote a figure: {offenders}"


def test_item_ids_are_prefixed_with_their_country() -> None:
    for pack in available():
        for item in pack.items:
            assert item.id.startswith(f"{pack.country.lower()}.")


def test_an_unknown_country_raises_rather_than_returning_an_empty_pack() -> None:
    with pytest.raises(PackError, match="no national pack"):
        load_pack("FR")


def test_a_malformed_pack_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "at.json"
    bad.write_text(json.dumps({"country": "AT", "items": []}), encoding="utf-8")
    monkeypatch.setattr("app.national.loader.PACKS_ROOT", tmp_path)
    load_pack.cache_clear()
    try:
        with pytest.raises(PackError, match="malformed"):
            load_pack("AT")
    finally:
        load_pack.cache_clear()


def test_duplicate_item_ids_raise(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item: dict[str, Any] = {"id": "at.process.x", "kind": "process", "title": "X"}
    (tmp_path / "at.json").write_text(
        json.dumps(
            {
                "country": "AT",
                "country_name": "Austria",
                "authority": "A",
                "summary": "s",
                "items": [item, item],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.national.loader.PACKS_ROOT", tmp_path)
    load_pack.cache_clear()
    try:
        with pytest.raises(PackError, match="share the id"):
            load_pack("AT")
    finally:
        load_pack.cache_clear()


def test_the_packs_directory_is_not_empty() -> None:
    """A vacuous pass would be worse than a failure."""
    assert list(PACKS_ROOT.glob("*.json"))


# ------------------------------------------------------------------ tailoring


def test_a_sail_gated_item_is_pending_below_its_sail_and_due_at_it() -> None:
    gated = next(i for i in load_pack("AT").items if i.min_sail == "III")
    due_low, pending_low = tailor("AT", sail="II")
    assert gated.id in {i.id for i in pending_low}
    assert gated.id not in {i.id for i in due_low}

    due_high, _ = tailor("AT", sail="III")
    assert gated.id in {i.id for i in due_high}


def test_tailoring_never_loses_an_item() -> None:
    pack = load_pack("AT")
    for sail in (None, *SAIL_ORDER):
        due, pending = tailor("AT", sail=sail)
        assert len(due) + len(pending) == len(pack.items)
        assert {i.id for i in due}.isdisjoint({i.id for i in pending})


def test_an_oso_tied_item_follows_the_determination_not_a_guess() -> None:
    crew = next(i for i in load_pack("AT").items if i.id.endswith("crew_training"))
    assert crew.osos
    due, pending = tailor("AT", sail="III", required_osos=frozenset({"OSO#01"}))
    assert crew.id in {i.id for i in pending}
    due, _ = tailor("AT", sail="III", required_osos=frozenset({crew.osos[0]}))
    assert crew.id in {i.id for i in due}


def test_a_certified_category_operation_has_no_sail_and_still_gets_a_checklist() -> None:
    due, _pending = tailor("AT", sail="certified_category")
    assert due, "an out-of-SORA operation still has registration and insurance to do"
    assert all(i.min_sail is None for i in due)


# ------------------------------------------------------------------ the API


def test_countries_endpoint_lists_the_packs(client: TestClient) -> None:
    res = client.get("/api/v1/national")
    assert res.status_code == 200, res.text
    by_code = {row["country"]: row for row in res.json()}
    assert by_code["AT"]["authority"] == "Austro Control GmbH"
    assert by_code["AT"]["unverified"] == by_code["AT"]["items"]
    assert by_code["AT"]["complete"] is False


def test_pack_endpoint_returns_the_warning_and_the_sources(client: TestClient) -> None:
    res = client.get("/api/v1/national/AT")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["warning"].startswith("UNVERIFIED")
    assert len(body["unverified_ids"]) == len(body["items"])
    assert all(item["source"] for item in body["items"])


def test_pack_endpoint_is_case_insensitive(client: TestClient) -> None:
    assert client.get("/api/v1/national/at").status_code == 200


def test_an_unsupported_country_is_a_404_that_names_the_alternatives(client: TestClient) -> None:
    res = client.get("/api/v1/national/FR")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "country_unsupported"
    assert "AT" in body["detail"]


def test_the_checklist_needs_authentication(client: TestClient, operation: dict[str, Any]) -> None:
    res = client.get(f"/api/v1/national/operations/{operation['id']}/checklist")
    assert res.status_code == 401


def test_the_checklist_follows_the_determination(
    client: TestClient, auth: dict[str, str], complete_draft: dict[str, Any], operation: dict[str, Any]
) -> None:
    """Before a run there is no SAIL; after one, the checklist is cut to it."""
    before = client.get(
        f"/api/v1/national/operations/{operation['id']}/checklist", headers=auth
    ).json()
    assert before["sail"] is None
    assert before["country"] == "AT"
    assert before["disclaimer"].startswith("SORA Copilot prepares")

    run = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert run.status_code == 200, run.text
    sail = run.json()["sail"]

    after = client.get(
        f"/api/v1/national/operations/{operation['id']}/checklist", headers=auth
    ).json()
    assert after["sail"] == sail
    # The SAIL III manual is due for this operation; the SAIL IV design evidence is not.
    due = {i["id"] for i in after["due"]}
    pending = {i["id"] for i in after["pending"]}
    assert "at.attachment.manual" in due
    assert "at.attachment.design_evidence" in pending
    assert after["warning"].startswith("UNVERIFIED")


def test_the_checklist_counts_what_is_already_attached(
    client: TestClient,
    auth: dict[str, str],
    complete_draft: dict[str, Any],
    operation: dict[str, Any],
    pro: dict[str, Any],
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    files = {"file": ("survey.pdf", b"%PDF-1.7 survey", "application/pdf")}
    up = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files=files,
        data={"oso_id": "OSO#08"},
        headers=auth,
    )
    assert up.status_code == 201, up.text
    body = client.get(
        f"/api/v1/national/operations/{operation['id']}/checklist", headers=auth
    ).json()
    assert body["evidence_attached"] == 1
    assert body["dossier_versions"] == 0


def test_another_orgs_operation_is_a_404_not_a_403(
    client: TestClient, operation: dict[str, Any]
) -> None:
    from uuid import uuid4

    from tests.conftest import make_token

    stranger = {"Authorization": f"Bearer {make_token(uuid4())}"}
    client.post("/api/v1/auth/session", headers=stranger)
    res = client.get(
        f"/api/v1/national/operations/{operation['id']}/checklist", headers=stranger
    )
    assert res.status_code == 404


def test_the_country_follows_the_organisation(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    patch = client.patch("/api/v1/orgs/me", json={"country": "DE"}, headers=auth)
    assert patch.status_code == 200, patch.text
    body = client.get(
        f"/api/v1/national/operations/{operation['id']}/checklist", headers=auth
    ).json()
    assert body["country"] == "DE"
    assert body["authority"].startswith("Luftfahrt-Bundesamt")


def test_the_pack_cannot_reach_the_engine() -> None:
    """A country pack is administrative, not analytical. Nothing in it may compute.

    The boundary test covers app/engine and app/services/llm.py; this covers the one
    other place where regulatory-looking content lives.
    """
    import ast
    import importlib

    root = Path(importlib.import_module("app.national").__file__ or "").parent
    paths = sorted(root.glob("*.py"))
    assert len(paths) >= 3, f"expected the national package at {root}, found {paths}"

    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                targets = [node.module]
            for target in targets:
                assert not target.startswith(("app.engine", "app.db", "app.services")), (
                    f"{path.name}:{node.lineno} imports {target!r}; a country pack must not "
                    "be able to reach the engine, the database or a service"
                )


def test_that_boundary_check_would_catch_a_real_violation(tmp_path: Path) -> None:
    """Guard the guard: the same walk must reject an engine import."""
    import ast

    offending = tmp_path / "loader.py"
    offending.write_text("from app.engine.runner import determine\n", encoding="utf-8")
    tree = ast.parse(offending.read_text(encoding="utf-8"))
    found = [
        n.module
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("app.engine")
    ]
    assert found == ["app.engine.runner"]
