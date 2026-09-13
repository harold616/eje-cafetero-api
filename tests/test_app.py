"""Tests for the FastAPI app's `/health` endpoint (#10).

`test_health_returns_200_when_database_is_reachable` hits `GET /health`
against the local Postgres instance from #2's docker-compose stack, the
same "real database" convention `test_orm_models.py`/`test_load.py` use:
skipped (not failed) if that instance isn't reachable, so `uv run pytest`
doesn't hard-require a running database.

`test_health_returns_503_when_database_is_unreachable` simulates the
database being unreachable by overriding the `get_engine` FastAPI
dependency with a stand-in whose `.connect()` raises the same
`sqlalchemy.exc.OperationalError` a real connection failure would raise —
no need to actually take Postgres down to exercise the failure path.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from eje_cafetero_api.app import app, get_engine
from eje_cafetero_api.db import get_database_url


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_engine.cache_clear()


def test_health_returns_200_when_database_is_reachable(client):
    engine = create_engine(get_database_url())
    try:
        connection = engine.connect()
    except OperationalError:
        engine.dispose()
        pytest.skip(
            "local Postgres instance is not reachable; "
            "start it with `docker compose up -d` (see #2)"
        )
    connection.close()
    engine.dispose()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_is_unreachable(client):
    def _get_broken_engine():
        broken_engine = MagicMock()
        broken_engine.connect.side_effect = OperationalError(
            "SELECT 1", {}, Exception("simulated connection failure")
        )
        return broken_engine

    app.dependency_overrides[get_engine] = _get_broken_engine

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] != "ok"
