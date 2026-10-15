"""Conversational intake, and the gate it sits behind.

The product's claim is that a language model never decides anything. These tests check
the shape of that claim at the HTTP boundary: a proposal arrives pending, carries the
operator's own words, cannot name a field that does not exist, and blocks the
determination until a human acts on it.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

PROSE = (
    "Alta X along the 110 kV line south of Gratkorn, about 14 km, BVLOS below 120 metres, "
    "farmland and a few scattered houses. Class G, near LOWG. Parachute fitted, NOTAM filed."
)


def _chat(client: TestClient, auth: dict[str, str], op_id: str, text: str = PROSE) -> dict[str, Any]:
    res = client.post(f"/api/v1/operations/{op_id}/intake/chat", json={"text": text}, headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


def test_extraction_proposes_facts_without_a_key_configured(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"])
    assert body["extractor"] == "deterministic"
    fields = {f["field"] for f in body["facts"]}
    assert "volume.max_altitude_agl_m" in fields
    assert "operation_type" in fields
    assert "ground_environment" in fields
    assert "airspace_class" in fields


def test_every_proposal_arrives_pending(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"])
    assert body["facts"]
    assert all(f["status"] == "pending" for f in body["facts"])


def test_every_proposal_quotes_the_operators_own_words(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """A proposal with no span is a guess, and extraction may not guess."""
    body = _chat(client, auth, operation["id"])
    for fact in body["facts"]:
        assert fact["source_span"], fact["field"]
        assert 0 <= fact["confidence"] <= 1


def test_the_reply_states_that_nothing_has_reached_the_engine(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"])
    assert "engine" in body["reply"].lower()


def test_extraction_proposes_an_aircraft_only_from_the_operators_fleet(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], drone: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"])
    aircraft = [f for f in body["facts"] if f["field"] == "drone_id"]
    assert aircraft, "the fleet contains an Alta X and the prose names one"
    assert aircraft[0]["value"] == drone["id"]


def test_extraction_proposes_nothing_for_an_aircraft_not_in_the_fleet(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"], "Flying a Wingcopter 198 over farmland at 90 m.")
    assert not [f for f in body["facts"] if f["field"] == "drone_id"]


def test_a_pending_proposal_blocks_the_determination(
    client: TestClient,
    auth: dict[str, str],
    operation: dict[str, Any],
    complete_draft: dict[str, Any],
) -> None:
    """The gate. A complete draft plus one pending fact must still refuse to run."""
    _chat(client, auth, operation["id"])
    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert res.status_code == 409
    body = res.json()
    assert body["code"] == "unconfirmed_facts"
    assert body["unconfirmed_fields"], "the refusal must name what is waiting"
    assert "confirm" in body["detail"].lower()


def test_confirming_every_proposal_unblocks_the_determination(
    client: TestClient,
    auth: dict[str, str],
    operation: dict[str, Any],
    complete_draft: dict[str, Any],
) -> None:
    facts = _chat(client, auth, operation["id"])["facts"]
    for fact in facts:
        res = client.post(
            f"/api/v1/operations/{operation['id']}/facts/{fact['id']}/confirm", headers=auth
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "confirmed"

    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert res.status_code == 200, res.text


def test_rejecting_a_proposal_also_unblocks_it(
    client: TestClient,
    auth: dict[str, str],
    operation: dict[str, Any],
    complete_draft: dict[str, Any],
) -> None:
    """Rejection is a decision too, and it must not leave the operator stuck."""
    facts = _chat(client, auth, operation["id"])["facts"]
    for fact in facts:
        client.post(f"/api/v1/operations/{operation['id']}/facts/{fact['id']}/reject", headers=auth)
    assert client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth).status_code == 200


def test_a_confirmed_proposal_lands_in_the_draft(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], drone: dict[str, Any]
) -> None:
    facts = _chat(client, auth, operation["id"])["facts"]
    altitude = next(f for f in facts if f["field"] == "volume.max_altitude_agl_m")
    client.post(f"/api/v1/operations/{operation['id']}/facts/{altitude['id']}/confirm", headers=auth)
    draft = client.get(f"/api/v1/operations/{operation['id']}/draft", headers=auth).json()
    assert draft["mission"]["volume"]["max_altitude_agl_m"] == altitude["value"]


def test_a_rejected_proposal_never_lands_in_the_draft(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], drone: dict[str, Any]
) -> None:
    facts = _chat(client, auth, operation["id"])["facts"]
    ground = next(f for f in facts if f["field"] == "ground_environment")
    client.post(f"/api/v1/operations/{operation['id']}/facts/{ground['id']}/reject", headers=auth)
    draft = client.get(f"/api/v1/operations/{operation['id']}/draft", headers=auth).json()
    assert "ground_environment" not in draft["mission"]


def test_each_proposal_names_the_step_a_rejection_returns_to(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    body = _chat(client, auth, operation["id"])
    steps = {f["owning_step"] for f in body["facts"]}
    assert steps <= {"aircraft", "operation", "map", "ground", "airspace", "mitigations", "review"}
    altitude = next(f for f in body["facts"] if f["field"] == "volume.max_altitude_agl_m")
    assert altitude["owning_step"] == "operation"


def test_extraction_returns_nothing_rather_than_inventing(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """Text with no facts in it must produce no facts, not a plausible mission."""
    body = _chat(client, auth, operation["id"], "Good morning, hope the weather holds.")
    assert body["facts"] == []
    assert "nothing" in body["reply"].lower()


def test_no_proposal_can_carry_a_risk_value(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """The decisive property: extraction has no field in which to put a conclusion."""
    body = _chat(
        client,
        auth,
        operation["id"],
        "This is SAIL II with iGRC 3 and ARC b, GRC 2, containment is basic, OSO#05 at low.",
    )
    fields = {f["field"] for f in body["facts"]}
    for forbidden in ("sail", "igrc", "grc", "arc", "oso", "containment", "tmpr"):
        assert not any(forbidden in f for f in fields), f"{forbidden} reached a proposable field"


def test_extraction_for_another_organisation_is_refused(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    from uuid import uuid4

    from tests.conftest import make_token

    other = {"Authorization": f"Bearer {make_token(uuid4(), email='other@example.com')}"}
    client.post("/api/v1/auth/session", headers=other)
    res = client.post(
        f"/api/v1/operations/{operation['id']}/intake/chat", json={"text": PROSE}, headers=other
    )
    assert res.status_code == 404
