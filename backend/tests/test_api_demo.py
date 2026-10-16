"""The worked example.

Its value depends entirely on being real: a canned SAIL in a fixture would make the
product look like it works without demonstrating that it does. So the tests here are
mostly about the example being indistinguishable from an operation somebody drew by
hand — same engine, same storage, same plan accounting, same editability.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.plans import PLANS
from tests.conftest import make_token


def seed(client: TestClient, auth: dict[str, str]) -> dict[str, Any]:
    res = client.post("/api/v1/demo/example", headers=auth)
    assert res.status_code in (200, 201), res.text
    return dict(res.json())


# ------------------------------------------------------------------ it is real


def test_the_worked_example_is_computed_by_the_engine_not_canned(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    operation = seed(client, auth)
    determination = client.get(
        f"/api/v1/operations/{operation['id']}/determination", headers=auth
    )
    assert determination.status_code == 200, determination.text
    d = determination.json()

    # The whole chain, with a justification for every step.
    assert d["igrc"] == 5
    assert d["final_grc"] == 4
    assert d["initial_arc"] == "c"
    assert d["residual_arc"] == "b"
    assert d["sail"] == "III"
    assert len(d["trace"]) > 40, "a worked example with a thin trace shows nothing"
    assert all(node.get("rule_id") for node in d["trace"])
    assert d["rulebase_version"], "the example is pinned like any other determination"

    # And it is honest about the rulebase it ran against.
    assert d["is_verified"] is False
    assert d["warnings"], "the UNVERIFIED warnings apply to the example too"


def test_the_example_has_something_for_every_screen_to_show(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """A SAIL in the middle of the range, so the advisor and the OSO matrix are not empty."""
    operation = seed(client, auth)
    oid = operation["id"]

    osos = client.get(f"/api/v1/operations/{oid}/osos", headers=auth).json()
    assert sum(1 for o in osos if o["required_robustness"] != "none") > 5

    volumes = client.post(f"/api/v1/operations/{oid}/geo/derive", headers=auth).json()
    assert volumes["flight_geography_km2"] > 1
    assert volumes["ground_risk_buffer_km2"] > volumes["contingency_volume_km2"]
    assert volumes["derivations"], "every volume names the rule that produced it"

    from app.db import get_repo

    get_repo().update_org(signed_in["id"], {"plan": "pro"})
    advice = client.post(
        f"/api/v1/operations/{oid}/counterfactual", json={"limit": 3}, headers=auth
    ).json()
    assert advice["suggestions"], "the example should have room to improve, or it teaches nothing"
    assert all(s["resulting_sail"] == "II" for s in advice["suggestions"])


def test_the_example_is_labelled_so_nobody_mistakes_it_for_a_real_flight(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    operation = seed(client, auth)
    assert "worked example" in operation["name"].lower()
    draft = client.get(f"/api/v1/operations/{operation['id']}/draft", headers=auth).json()
    assert draft["mission"].get("demo") is True


def test_the_example_is_the_operators_own_data_and_can_be_changed(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """A starting point, not a read-only showroom."""
    operation = seed(client, auth)
    oid = operation["id"]

    renamed = client.patch(
        f"/api/v1/operations/{oid}", json={"name": "My first real survey"}, headers=auth
    )
    assert renamed.status_code == 200, renamed.text

    edited = client.patch(
        f"/api/v1/operations/{oid}/draft",
        json={"volume": {"max_altitude_agl_m": 95}},
        headers=auth,
    )
    assert edited.status_code == 200, edited.text

    rerun = client.post(f"/api/v1/operations/{oid}/determine?force=true", headers=auth)
    assert rerun.status_code == 200, rerun.text

    assert client.delete(f"/api/v1/operations/{oid}", headers=auth).status_code == 204


# ------------------------------------------------------------------ it behaves


def test_seeding_twice_gives_one_example_not_two(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    first = seed(client, auth)
    second = client.post("/api/v1/demo/example", headers=auth)
    assert second.status_code == 200, "the second call should return the first example"
    assert second.json()["id"] == first["id"]
    assert len(client.get("/api/v1/operations", headers=auth).json()) == 1
    # And it reuses the example aircraft rather than adding a second to the fleet.
    assert len(client.get("/api/v1/drones", headers=auth).json()) == 1


def test_deleting_the_example_lets_a_fresh_one_be_built(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    first = seed(client, auth)
    client.delete(f"/api/v1/operations/{first['id']}", headers=auth)
    again = client.post("/api/v1/demo/example", headers=auth)
    assert again.status_code == 201
    assert again.json()["id"] != first["id"]


def test_the_example_is_reported_before_it_is_built(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    assert client.get("/api/v1/demo/example", headers=auth).json() is None
    made = seed(client, auth)
    assert client.get("/api/v1/demo/example", headers=auth).json()["id"] == made["id"]


def test_the_example_counts_against_the_plan_like_anything_else(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """No side door: a free account that has used its operations is told so."""
    limit = PLANS["free"].operations or 0
    for i in range(limit):
        created = client.post("/api/v1/operations", json={"name": f"Real {i}"}, headers=auth)
        assert created.status_code == 201, created.text

    refused = client.post("/api/v1/demo/example", headers=auth)
    assert refused.status_code == 402
    body = refused.json()
    assert body["code"] == "plan_limit"
    assert body["feature"] == "operations"


def test_the_example_belongs_to_one_organisation_only(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    mine = seed(client, auth)
    stranger = {"Authorization": f"Bearer {make_token(uuid4())}"}
    client.post("/api/v1/auth/session", headers=stranger)
    assert client.get("/api/v1/demo/example", headers=stranger).json() is None
    assert client.get(f"/api/v1/operations/{mine['id']}", headers=stranger).status_code == 404


def test_the_example_needs_authentication(client: TestClient) -> None:
    assert client.post("/api/v1/demo/example").status_code == 401
    assert client.get("/api/v1/demo/example").status_code == 401


def test_the_example_can_be_exported_as_a_dossier(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """The end of the journey the example exists to demonstrate."""
    from app.db import get_repo

    get_repo().update_org(signed_in["id"], {"plan": "pro"})
    operation = seed(client, auth)
    made = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={"format": "pdf"}, headers=auth
    )
    assert made.status_code == 201, made.text
    got = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{made.json()['id']}/download",
        headers=auth,
    )
    assert got.content.startswith(b"%PDF-")
