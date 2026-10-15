"""The whole authenticated flow, against the in-memory store.

This is the Phase 3 definition of done, as a test: create an aircraft and an operation
over the API, complete the wizard, and get a persisted determination with the rulebase
version pinned.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_an_unauthenticated_request_is_refused(client: TestClient) -> None:
    res = client.get("/api/v1/operations")
    assert res.status_code == 401
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["code"] == "unauthenticated"


def test_a_garbage_token_is_refused(client: TestClient) -> None:
    res = client.get("/api/v1/operations", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401
    assert res.json()["code"] == "unauthenticated"


def test_an_expired_token_is_refused(client: TestClient, user_id: Any) -> None:
    from tests.conftest import make_token

    token = make_token(user_id, expires_in=-10)
    res = client.get("/api/v1/operations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_signing_in_creates_an_organisation(signed_in: dict[str, Any]) -> None:
    assert signed_in["role"] == "owner"
    assert signed_in["seats_used"] == 1
    assert signed_in["plan"] == "free"


def test_a_new_account_has_no_operations(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    res = client.get("/api/v1/operations", headers=auth)
    assert res.status_code == 200
    assert res.json() == []


def test_kinetic_energy_is_computed_not_accepted(drone: dict[str, Any]) -> None:
    assert round(drone["kinetic_energy_j"], 1) == round(0.5 * 15.9 * 22**2, 1)


def test_a_drone_with_max_speed_below_cruise_is_refused(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    from tests.conftest import ALTA_X

    res = client.post(
        "/api/v1/drones", json={**ALTA_X, "cruise_speed_ms": 30, "max_speed_ms": 22}, headers=auth
    )
    assert res.status_code == 422
    assert res.json()["code"] == "validation_failed"


def test_determine_refuses_an_incomplete_mission(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "mission_incomplete"
    # The message must name what is missing, in the wizard's words.
    assert "Ground environment" in body["detail"]


def test_the_full_flow_produces_a_pinned_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    assert complete_draft["ready_to_determine"] is True
    assert complete_draft["missing_fields"] == []

    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert res.status_code == 200, res.text
    d = res.json()

    assert d["igrc"] == 5
    assert d["final_grc"] == 4
    assert d["initial_arc"] == "c"
    assert d["residual_arc"] == "b"
    assert d["sail"] == "III"
    assert d["rulebase_version"] == "2.5.0-rc1"
    assert d["mission_hash"]
    assert d["freshly_computed"] is True
    assert len(d["osos"]) == 17
    assert d["trace"], "a determination with no trace is a bug, not a degraded result"
    assert d["is_verified"] is False
    assert any("UNVERIFIED" in w for w in d["warnings"])


def test_every_trace_node_carries_a_citation_over_the_api(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    d = client.get(f"/api/v1/operations/{operation['id']}/determination", headers=auth).json()
    for node in d["trace"]:
        assert node["citation"]["document"]
        assert node["citation"]["section"]
        assert node["rule_id"]


def test_re_running_is_idempotent(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    """A dossier references a determination by id, so one computation must mean one id."""
    first = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    second = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    assert first["id"] == second["id"]
    assert second["freshly_computed"] is False


def test_forcing_a_rerun_still_returns_the_same_chain(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    first = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    forced = client.post(f"/api/v1/operations/{operation['id']}/determine?force=true", headers=auth).json()
    assert forced["sail"] == first["sail"]
    assert forced["mission_hash"] == first["mission_hash"]


def test_determining_moves_the_operation_out_of_draft(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    assert operation["status"] == "draft"
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    after = client.get(f"/api/v1/operations/{operation['id']}", headers=auth).json()
    assert after["status"] == "determined"
    assert after["sail"] == "III"
    assert after["oso_gaps"] == 16


def test_a_changed_mitigation_produces_a_new_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    first = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    client.patch(
        f"/api/v1/operations/{operation['id']}/draft",
        json={"mitigations": {"m1_strategic": "medium"}},
        headers=auth,
    )
    second = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    assert second["id"] != first["id"]
    assert second["mission_hash"] != first["mission_hash"]
    assert second["final_grc"] == 3


def test_counterfactuals_are_offered_and_each_lowers_sail(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    res = client.post(f"/api/v1/operations/{operation['id']}/counterfactual", json={"limit": 5}, headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["current_sail"] == "III"
    order = ["I", "II", "III", "IV", "V", "VI", "certified_category"]
    for s in body["suggestions"]:
        assert order.index(s["resulting_sail"]) < order.index("III"), s["title"]
        assert s["changes"]
        assert s["evidence_required"]


def test_applying_a_counterfactual_changes_the_draft_but_not_the_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    """Applying must not silently become a determination — that line is the product."""
    before = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).json()
    suggestions = client.post(
        f"/api/v1/operations/{operation['id']}/counterfactual", json={}, headers=auth
    ).json()["suggestions"]
    assert suggestions

    res = client.post(
        f"/api/v1/operations/{operation['id']}/counterfactual/apply",
        json={"suggestion_id": suggestions[0]["id"]},
        headers=auth,
    )
    assert res.status_code == 200, res.text

    still = client.get(f"/api/v1/operations/{operation['id']}/determination", headers=auth).json()
    assert still["id"] == before["id"], "applying a suggestion must not write a determination"


def test_geo_derivation_produces_volumes_and_says_how(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    res = client.post(f"/api/v1/operations/{operation['id']}/geo/derive", headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["flight_geography_km2"] > 0
    assert body["contingency_volume_km2"] > body["flight_geography_km2"]
    assert body["ground_risk_buffer_km2"] > body["contingency_volume_km2"]
    assert body["adjacent_area_km2"] > body["ground_risk_buffer_km2"]
    assert body["unverified"] is True
    assert len(body["derivations"]) == 2
    for d in body["derivations"]:
        assert d["rule"], "a derived number must say what produced it"


def test_geo_derivation_refuses_a_self_intersecting_outline(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], drone: dict[str, Any]
) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[15.40, 47.10], [15.44, 47.12], [15.44, 47.10], [15.40, 47.12], [15.40, 47.10]]],
    }
    client.patch(
        f"/api/v1/operations/{operation['id']}/draft",
        json={"drone_id": drone["id"], "volume": {"flight_geography": bowtie, "max_altitude_agl_m": 118}},
        headers=auth,
    )
    res = client.post(f"/api/v1/operations/{operation['id']}/geo/derive", headers=auth)
    assert res.status_code == 422
    assert res.json()["code"] == "geometry_invalid"


def test_the_density_sample_is_a_suggestion_not_a_decision(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/geo/density",
        json={"density_per_km2": 84, "adjacent_area_populated": False},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["density_band"] == "under_500"
    assert body["suggested_environment"] == "sparsely_populated"
    assert body["rationale"]
    assert body["is_suggestion_only"] is True
    # The suggestion must NOT have overwritten the operator's own choice.
    draft = client.get(f"/api/v1/operations/{operation['id']}/draft", headers=auth).json()
    assert draft["mission"]["ground_environment"] == "sparsely_populated"


def test_one_operator_cannot_see_another_organisations_operation(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """Org scoping is the authorisation gate, so this is the test that matters most."""
    from uuid import uuid4

    from tests.conftest import make_token

    other = {"Authorization": f"Bearer {make_token(uuid4(), email='other@example.com')}"}
    client.post("/api/v1/auth/session", headers=other)

    assert client.get("/api/v1/operations", headers=other).json() == []
    res = client.get(f"/api/v1/operations/{operation['id']}", headers=other)
    assert res.status_code == 404
    # The message must not reveal that the operation exists elsewhere.
    assert "organisation" in res.json()["detail"]


def test_one_operator_cannot_determine_another_organisations_operation(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    from uuid import uuid4

    from tests.conftest import make_token

    other = {"Authorization": f"Bearer {make_token(uuid4(), email='other@example.com')}"}
    client.post("/api/v1/auth/session", headers=other)
    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=other)
    assert res.status_code == 404


def test_deleting_an_operation_removes_its_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert client.delete(f"/api/v1/operations/{operation['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/operations/{operation['id']}", headers=auth).status_code == 404
