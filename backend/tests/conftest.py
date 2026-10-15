"""Test fixtures. Nothing here needs Supabase, an Anthropic key, or a network."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENV", "test")
# 32+ bytes: PyJWT warns below the SHA-256 recommendation, and a warning in the suite
# trains people to ignore warnings.
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-not-a-real-key-padded-to-32-bytes-plus")

JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


def make_token(user_id: UUID, email: str = "k.leitner@example.at", expires_in: int = 3600) -> str:
    """A Supabase-shaped access token, signed with the test secret."""
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "aud": "authenticated",
            "role": "authenticated",
            "exp": datetime.now(UTC) + timedelta(seconds=expires_in),
            "iat": datetime.now(UTC),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.config import get_settings
    from app.db import reset_repo
    from app.main import create_app

    get_settings.cache_clear()
    reset_repo()
    from app.services.storage import reset_storage

    reset_storage()
    with TestClient(create_app()) as c:
        yield c
    reset_repo()
    from app.services.storage import reset_storage

    reset_storage()


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def auth(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture
def signed_in(client: TestClient, auth: dict[str, str]) -> dict[str, Any]:
    """A signed-in operator with an organisation, as the app creates one on first use."""
    res = client.post("/api/v1/auth/session", headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture
def pro(signed_in: dict[str, Any]) -> dict[str, Any]:
    """The organisation on the Pro plan, as a paying customer would be.

    Written straight through the repository because no API endpoint may change a plan —
    only a verified Stripe webhook does. A test that needs a paid feature asks for this
    fixture; a test that does not gets the free plan, which is what a new sign-up gets.
    """
    from app.db import get_repo

    get_repo().update_org(signed_in["id"], {"plan": "pro"})
    return signed_in


SQUARE = {
    "type": "Polygon",
    "coordinates": [[[15.40, 47.10], [15.44, 47.10], [15.44, 47.12], [15.40, 47.12], [15.40, 47.10]]],
}

ALTA_X = {
    "name": "Freefly Alta X",
    "registration": "ALTA-X-01",
    "max_dimension_m": 1.32,
    "mtom_kg": 15.9,
    "cruise_speed_ms": 18,
    "max_speed_ms": 22,
    "fitted_mitigations": ["parachute", "fts"],
}


@pytest.fixture
def drone(client: TestClient, auth: dict[str, str], signed_in: dict[str, Any]) -> dict[str, Any]:
    res = client.post("/api/v1/drones", json=ALTA_X, headers=auth)
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def operation(client: TestClient, auth: dict[str, str], drone: dict[str, Any]) -> dict[str, Any]:
    res = client.post(
        "/api/v1/operations",
        json={"name": "Powerline corridor — Mur valley", "site": "Graz Süd, AT", "drone_id": drone["id"]},
        headers=auth,
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def complete_draft(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], drone: dict[str, Any]
) -> dict[str, Any]:
    """A draft with every required field, as the wizard would leave it."""
    res = client.patch(
        f"/api/v1/operations/{operation['id']}/draft",
        json={
            "drone_id": drone["id"],
            "operation_type": "bvlos",
            "volume": {"flight_geography": SQUARE, "max_altitude_agl_m": 118},
            "ground_environment": "sparsely_populated",
            "population_density_per_km2": 84,
            "airspace_class": "g",
            "near_aerodrome": True,
            "controlled_airspace": False,
            "atypical_airspace": False,
            "mitigations": {"m1_strategic": "low", "strategic_air": "low"},
            "country": "AT",
        },
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()
