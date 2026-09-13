"""Tests for the `GET /coffees` and `GET /coffees/{id}` endpoints (#11).

Like `test_load.py`, these run against the local Postgres instance from #2's
docker-compose stack (`docker compose up -d`) and are skipped (not failed)
if it isn't reachable.

#15 (seed data) isn't done yet, so fixture coffees are inserted directly via
#7's `upsert_coffee` inside each test's own connection/transaction — the
`get_session` FastAPI dependency is overridden to hand the app the exact
same `Session`, so the endpoints see the uncommitted fixture rows without an
intermediate commit. Every test rolls its transaction back on teardown, so
no fixture data is ever actually persisted.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api import models
from eje_cafetero_api.app import app, get_session
from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.load import upsert_coffee
from eje_cafetero_api.orm_models import (
    BrewMethod,
    CausalLink,
    Coffee as CoffeeRow,
    Environment,
    FlavorProfile,
    Origin,
    ProcessingMethod,
    RoastProfile,
    Variety,
)


@pytest.fixture()
def db_session():
    engine = create_engine(get_database_url())
    try:
        connection = engine.connect()
    except OperationalError:
        engine.dispose()
        pytest.skip(
            "local Postgres instance is not reachable; "
            "start it with `docker compose up -d` (see #2)"
        )

    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = _get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _build_coffee(coffee_id: str, name: str, summary: str) -> models.Coffee:
    """A minimal but fully valid `models.Coffee` fixture (#15 stand-in)."""
    return models.Coffee(
        id=coffee_id,
        name=name,
        summary=summary,
        origin=models.Origin(
            department="Quindío", municipality="Salento", farm_name="Finca Test"
        ),
        environment=models.Environment(altitude_meters=1800, shade_type="partial_shade"),
        variety=models.Variety(species="arabica", cultivar="Caturra", rootstock="own-rooted"),
        processing=models.Processing(method="washed"),
        roasting=models.Roasting(roast_level="medium"),
        brewing=models.Brewing(recommended_methods=["pour_over"]),
        flavor=models.Flavor(
            tasting_notes=["citrus"], acidity="high", body="light", sweetness="medium"
        ),
        causal_links=[],
    )


def test_list_coffees_returns_multiple_seeded_entries(client, db_session):
    upsert_coffee(db_session, _build_coffee("coffee-one", "Coffee One", "First summary."))
    upsert_coffee(db_session, _build_coffee("coffee-two", "Coffee Two", "Second summary."))
    db_session.flush()

    response = client.get("/coffees")

    assert response.status_code == 200
    body = response.json()
    ids = {entry["id"] for entry in body}
    assert {"coffee-one", "coffee-two"} <= ids
    by_id = {entry["id"]: entry for entry in body}
    assert by_id["coffee-one"] == {
        "id": "coffee-one",
        "name": "Coffee One",
        "summary": "First summary.",
    }
    assert by_id["coffee-two"] == {
        "id": "coffee-two",
        "name": "Coffee Two",
        "summary": "Second summary.",
    }


def _clear_all_coffees(session) -> None:
    """Delete every row in `coffees` and its factor/link tables.

    Only within the caller's own (later-rolled-back) transaction, so this
    never touches actually-committed data — it just gives this one test a
    genuinely empty table to assert against, on a dev database that may
    already have rows left over from other work (e.g. #7/#15 fixtures).
    Children are deleted before `coffees` since no `ON DELETE CASCADE` is
    configured on the factor tables' foreign keys (see `orm_models.py`).
    """
    for model in (
        CausalLink,
        Origin,
        Environment,
        Variety,
        ProcessingMethod,
        RoastProfile,
        BrewMethod,
        FlavorProfile,
    ):
        session.query(model).delete()
    session.query(CoffeeRow).delete()
    session.flush()


def test_list_coffees_on_empty_database_returns_empty_list(client, db_session):
    _clear_all_coffees(db_session)

    response = client.get("/coffees")

    assert response.status_code == 200
    assert response.json() == []


def test_get_coffee_returns_existing_coffee(client, db_session):
    upsert_coffee(
        db_session, _build_coffee("coffee-exists", "Existing Coffee", "A summary.")
    )
    db_session.flush()

    response = client.get("/coffees/coffee-exists")

    assert response.status_code == 200
    assert response.json() == {
        "id": "coffee-exists",
        "name": "Existing Coffee",
        "summary": "A summary.",
    }


def test_get_coffee_returns_404_for_nonexistent_id(client):
    response = client.get("/coffees/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] is not None
