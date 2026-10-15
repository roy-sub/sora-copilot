"""Members, invitations and the seat limit.

The Team plan sells five seats, so there has to be a way to use them — and a way for the
limit to bite. The thing worth being careful about is the *order* of the two: a pending
invitation holds a seat, because otherwise two people accepting at the same moment put a
five-seat organisation at six and nothing would have refused it.

Invitations are claimed by the email in a **verified** JWT rather than by a secret link,
so these tests are mostly about who can claim what.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.services.plans import PLANS
from tests.conftest import make_token

COLLEAGUE = "m.steiner@example.at"


def auth_for(user_id: UUID, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id, email=email)}"}


def seats(client: TestClient, auth: dict[str, str]) -> dict[str, Any]:
    res = client.get("/api/v1/orgs/me/seats", headers=auth)
    assert res.status_code == 200, res.text
    return dict(res.json())


def set_plan(client: TestClient, auth: dict[str, str], plan: str) -> None:
    from app.db import get_repo

    org_id = client.get("/api/v1/orgs/me", headers=auth).json()["id"]
    get_repo().update_org(org_id, {"plan": plan})


# ------------------------------------------------------------------ the default


def test_a_new_organisation_has_one_member_and_one_seat(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    body = seats(client, auth)
    assert body["seats_used"] == 1
    assert body["seats_limit"] == PLANS["free"].seats == 1
    assert body["members"][0]["role"] == "owner"
    assert body["members"][0]["is_you"] is True
    assert body["members"][0]["email"] == "k.leitner@example.at"
    assert body["invites"] == []
    assert body["can_invite"] is False, "a one-seat plan has nobody to invite"


# ------------------------------------------------------------------ the seat limit


def test_the_free_plan_cannot_invite_anybody(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    res = client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    assert res.status_code == 402
    body = res.json()
    assert body["code"] == "plan_limit"
    assert body["feature"] == "seats"
    assert body["upgrade_to"] == "team"


def test_a_team_plan_can_invite_up_to_its_seats_and_then_stops(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    limit = PLANS["team"].seats
    assert limit == 5

    # One seat is already taken by the owner, so four invitations fit.
    for i in range(limit - 1):
        res = client.post(
            "/api/v1/orgs/me/invites", json={"email": f"colleague{i}@example.at"}, headers=auth
        )
        assert res.status_code == 201, res.text

    full = seats(client, auth)
    assert full["seats_committed"] == limit
    assert full["can_invite"] is False

    refused = client.post(
        "/api/v1/orgs/me/invites", json={"email": "one.too.many@example.at"}, headers=auth
    )
    assert refused.status_code == 402
    assert refused.json()["feature"] == "seats"


def test_a_pending_invitation_holds_a_seat(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """Otherwise two people accepting at once put the organisation over its plan."""
    set_plan(client, auth, "team")
    before = seats(client, auth)
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    after = seats(client, auth)
    assert after["seats_used"] == before["seats_used"], "nobody has joined yet"
    assert after["seats_committed"] == before["seats_committed"] + 1


def test_withdrawing_an_invitation_returns_the_seat(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    created = client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    invite_id = created.json()["invites"][0]["id"]

    res = client.delete(f"/api/v1/orgs/me/invites/{invite_id}", headers=auth)
    assert res.status_code == 200, res.text
    assert res.json()["invites"] == []
    assert res.json()["seats_committed"] == 1


def test_re_inviting_the_same_address_does_not_take_a_second_seat(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    again = client.post(
        "/api/v1/orgs/me/invites", json={"email": COLLEAGUE, "role": "admin"}, headers=auth
    )
    assert again.status_code == 201, again.text
    body = again.json()
    assert len(body["invites"]) == 1
    assert body["invites"][0]["role"] == "admin", "re-inviting updates the role"
    assert body["seats_committed"] == 2


def test_the_address_is_normalised_so_case_cannot_buy_a_second_seat(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    again = client.post(
        "/api/v1/orgs/me/invites", json={"email": COLLEAGUE.upper()}, headers=auth
    )
    assert again.status_code == 201
    assert len(again.json()["invites"]) == 1


def test_an_invalid_address_is_refused(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    res = client.post("/api/v1/orgs/me/invites", json={"email": "not-an-address"}, headers=auth)
    assert res.status_code == 422
    assert res.json()["code"] == "validation_failed"


def test_an_invitation_can_never_grant_ownership(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """Transferring an organisation is a different act, and it is not built."""
    set_plan(client, auth, "team")
    res = client.post(
        "/api/v1/orgs/me/invites", json={"email": COLLEAGUE, "role": "owner"}, headers=auth
    )
    assert res.status_code == 422


# ------------------------------------------------------------------ claiming


def test_the_invited_address_joins_the_organisation_on_first_sign_in(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post(
        "/api/v1/orgs/me/invites", json={"email": COLLEAGUE, "role": "admin"}, headers=auth
    )

    colleague = auth_for(uuid4(), COLLEAGUE)
    joined = client.post("/api/v1/auth/session", headers=colleague)
    assert joined.status_code == 200, joined.text
    assert joined.json()["id"] == signed_in["id"], "they got their own organisation instead"
    assert joined.json()["role"] == "admin"

    after = seats(client, auth)
    assert after["seats_used"] == 2
    assert after["seats_committed"] == 2, "the invitation stopped holding a separate seat"
    assert after["invites"][0]["status"] == "accepted"
    assert {m["email"] for m in after["members"]} == {"k.leitner@example.at", COLLEAGUE}


def test_an_uninvited_address_gets_its_own_organisation(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)

    stranger = auth_for(uuid4(), "someone.else@example.at")
    joined = client.post("/api/v1/auth/session", headers=stranger)
    assert joined.status_code == 200
    assert joined.json()["id"] != signed_in["id"]
    assert joined.json()["role"] == "owner"
    assert seats(client, auth)["seats_used"] == 1


def test_an_invitation_is_claimed_once(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """A second person with the same address cannot ride in on a spent invitation."""
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)

    first = client.post("/api/v1/auth/session", headers=auth_for(uuid4(), COLLEAGUE))
    assert first.json()["id"] == signed_in["id"]

    second = client.post("/api/v1/auth/session", headers=auth_for(uuid4(), COLLEAGUE))
    assert second.json()["id"] != signed_in["id"], "the invitation was claimed twice"


def test_an_expired_invitation_is_not_claimable(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.db import get_repo

    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    repo = get_repo()
    for invite in repo.invites.values():  # type: ignore[attr-defined]
        invite["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    joined = client.post("/api/v1/auth/session", headers=auth_for(uuid4(), COLLEAGUE))
    assert joined.json()["id"] != signed_in["id"]
    assert seats(client, auth)["invites"][0]["status"] == "expired"


def test_a_withdrawn_invitation_cannot_be_claimed(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    created = client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    client.delete(f"/api/v1/orgs/me/invites/{created.json()['invites'][0]['id']}", headers=auth)

    joined = client.post("/api/v1/auth/session", headers=auth_for(uuid4(), COLLEAGUE))
    assert joined.json()["id"] != signed_in["id"]


def test_an_invitation_does_not_leak_across_organisations(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    """Another organisation's invitation list is not visible, and not deletable."""
    set_plan(client, auth, "team")
    created = client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    invite_id = created.json()["invites"][0]["id"]

    stranger = auth_for(uuid4(), "stranger@example.at")
    client.post("/api/v1/auth/session", headers=stranger)
    assert seats(client, stranger)["invites"] == []

    res = client.delete(f"/api/v1/orgs/me/invites/{invite_id}", headers=stranger)
    assert res.status_code == 404
    assert len(seats(client, auth)["invites"]) == 1


# ------------------------------------------------------------------ membership changes


def test_a_member_cannot_invite_or_remove(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    colleague = auth_for(uuid4(), COLLEAGUE)
    client.post("/api/v1/auth/session", headers=colleague)

    refused = client.post(
        "/api/v1/orgs/me/invites", json={"email": "third@example.at"}, headers=colleague
    )
    assert refused.status_code == 403
    assert refused.json()["code"] == "forbidden"


def test_an_admin_can_remove_a_member_and_the_seat_comes_back(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    colleague_id = uuid4()
    client.post("/api/v1/auth/session", headers=auth_for(colleague_id, COLLEAGUE))
    assert seats(client, auth)["seats_used"] == 2

    res = client.delete(f"/api/v1/orgs/me/members/{colleague_id}", headers=auth)
    assert res.status_code == 200, res.text
    assert res.json()["seats_used"] == 1


def test_removing_a_member_leaves_their_work_with_the_organisation(
    client: TestClient,
    auth: dict[str, str],
    signed_in: dict[str, Any],
    drone: dict[str, Any],
) -> None:
    """A compliance record outlives the employment that produced it."""
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}, headers=auth)
    colleague_id = uuid4()
    colleague = auth_for(colleague_id, COLLEAGUE)
    client.post("/api/v1/auth/session", headers=colleague)

    made = client.post(
        "/api/v1/operations", json={"name": "Theirs, then ours"}, headers=colleague
    )
    assert made.status_code == 201, made.text

    client.delete(f"/api/v1/orgs/me/members/{colleague_id}", headers=auth)
    still_there = client.get(f"/api/v1/operations/{made.json()['id']}", headers=auth)
    assert still_there.status_code == 200
    assert still_there.json()["name"] == "Theirs, then ours"


def test_you_cannot_remove_yourself(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], user_id: UUID
) -> None:
    res = client.delete(f"/api/v1/orgs/me/members/{user_id}", headers=auth)
    assert res.status_code == 409
    assert res.json()["code"] == "cannot_remove_yourself"


def test_the_last_owner_cannot_be_demoted_or_removed(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], user_id: UUID
) -> None:
    """An organisation without an owner cannot be managed by anybody."""
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE, "role": "admin"}, headers=auth)
    colleague_id = uuid4()
    colleague = auth_for(colleague_id, COLLEAGUE)
    client.post("/api/v1/auth/session", headers=colleague)

    demote = client.patch(
        f"/api/v1/orgs/me/members/{user_id}", json={"role": "member"}, headers=colleague
    )
    assert demote.status_code == 409
    assert demote.json()["code"] == "last_owner"

    remove = client.delete(f"/api/v1/orgs/me/members/{user_id}", headers=colleague)
    assert remove.status_code == 409
    assert remove.json()["code"] == "last_owner"


def test_a_second_owner_makes_the_first_removable(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any], user_id: UUID
) -> None:
    set_plan(client, auth, "team")
    client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE, "role": "admin"}, headers=auth)
    colleague_id = uuid4()
    colleague = auth_for(colleague_id, COLLEAGUE)
    client.post("/api/v1/auth/session", headers=colleague)

    promoted = client.patch(
        f"/api/v1/orgs/me/members/{colleague_id}", json={"role": "owner"}, headers=auth
    )
    assert promoted.status_code == 200, promoted.text

    removed = client.delete(f"/api/v1/orgs/me/members/{user_id}", headers=colleague)
    assert removed.status_code == 200, removed.text
    assert removed.json()["seats_used"] == 1


def test_a_member_who_is_not_in_the_organisation_is_a_404(
    client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]
) -> None:
    res = client.delete(f"/api/v1/orgs/me/members/{uuid4()}", headers=auth)
    assert res.status_code == 404


def test_seats_need_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/orgs/me/seats").status_code == 401
    assert client.post("/api/v1/orgs/me/invites", json={"email": COLLEAGUE}).status_code == 401
