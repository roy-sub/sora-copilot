"""Health endpoints, including the one the uptime monitor and Docker depend on."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_is_ok_without_any_configuration(client: TestClient) -> None:
    """It must answer while Supabase is paused — that is the whole point of it."""
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["rulebase_version"]
    assert "supabase_configured" in body


def test_healthz_is_also_mounted_under_the_api_prefix(client: TestClient) -> None:
    assert client.get("/api/v1/healthz").status_code == 200


def test_deep_health_reports_unconfigured_rather_than_failing(client: TestClient) -> None:
    r = client.get("/healthz/deep")
    assert r.status_code == 200
    assert r.json()["database"] in {"unconfigured", "unreachable", "ok"}


def test_unknown_route_returns_problem_json(client: TestClient) -> None:
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "not_found"
