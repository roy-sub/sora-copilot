"""Test fixtures. Nothing here needs a Supabase project or an Anthropic key."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENV", "test")


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
