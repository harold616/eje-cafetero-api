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
    Environment,
    FlavorProfile,
    Origin,
    ProcessingMethod,
    RoastProfile,
    Variety,
)
from eje_cafetero_api.orm_models import (
    Coffee as CoffeeRow,
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
        environment=models.Environment(
            altitude_meters=1800, shade_type="partial_shade"
        ),
        variety=models.Variety(
            species="arabica", cultivar="Caturra", rootstock="own-rooted"
        ),
        processing=models.Processing(method="washed"),
        roasting=models.Roasting(roast_level="medium"),
        brewing=models.Brewing(recommended_methods=["pour_over"]),
        flavor=models.Flavor(
            tasting_notes=["citrus"], acidity="high", body="light", sweetness="medium"
        ),
        causal_links=[],
    )


def _build_full_coffee(coffee_id: str) -> models.Coffee:
    """A `models.Coffee` fixture with every optional field filled in too.

    Mirrors `tests/fixtures/valid_coffee.yaml` (#3/#4's reference example)
    field-for-field, so the #12 chain-endpoint tests below exercise a
    genuinely fully-seeded coffee, not just the minimal `_build_coffee`
    fixture above.
    """
    return models.Coffee(
        id=coffee_id,
        name="Finca El Ocaso Washed Caturra",
        summary="A washed Caturra from Finca El Ocaso, Salento, Quindío.",
        origin=models.Origin(
            department="Quindío",
            municipality="Salento",
            farm_name="Finca El Ocaso",
            producer="Familia Rosillo",
            latitude=4.6389,
            longitude=-75.5747,
        ),
        environment=models.Environment(
            altitude_meters=1850,
            shade_type="partial_shade",
            avg_temperature_celsius=19.5,
            annual_rainfall_mm=2100,
        ),
        variety=models.Variety(
            species="arabica", cultivar="Caturra", rootstock="own-rooted"
        ),
        processing=models.Processing(
            method="washed", fermentation_hours=18.0, drying_method="raised_beds"
        ),
        roasting=models.Roasting(
            roast_level="medium",
            development_time_percent=22.0,
            roaster_notes="Roasted to first crack plus a short development.",
        ),
        brewing=models.Brewing(
            recommended_methods=["pour_over", "aeropress"],
            water_temperature_celsius=94.0,
            grind_size="medium",
            ratio="1:16",
        ),
        flavor=models.Flavor(
            tasting_notes=["jasmine", "red apple", "brown sugar", "citrus"],
            acidity="high",
            body="medium",
            sweetness="medium",
            aftertaste="Clean, lingering citrus and floral finish.",
        ),
        causal_links=[
            models.CausalLink(
                from_factor="origin",
                to_factor="environment",
                explanation="Salento's location gives the farm high elevation.",
            )
        ],
    )


def test_list_coffees_returns_multiple_seeded_entries(client, db_session):
    upsert_coffee(
        db_session, _build_coffee("coffee-one", "Coffee One", "First summary.")
    )
    upsert_coffee(
        db_session, _build_coffee("coffee-two", "Coffee Two", "Second summary.")
    )
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


def test_get_coffee_chain_returns_all_seven_sections_for_a_full_coffee(
    client, db_session
):
    """#12: `GET /coffees/{id}/chain` on a fully-seeded coffee returns all
    seven factor sections, each asserted individually (not just "non-empty"),
    with representative fields from each."""
    upsert_coffee(db_session, _build_full_coffee("coffee-full-chain"))
    db_session.flush()

    response = client.get("/coffees/coffee-full-chain/chain")

    assert response.status_code == 200
    body = response.json()

    assert body["id"] == "coffee-full-chain"
    assert body["name"] == "Finca El Ocaso Washed Caturra"

    assert body["origin"] == {
        "department": "Quindío",
        "municipality": "Salento",
        "farm_name": "Finca El Ocaso",
        "producer": "Familia Rosillo",
        "latitude": 4.6389,
        "longitude": -75.5747,
    }
    assert body["environment"] == {
        "altitude_meters": 1850,
        "shade_type": "partial_shade",
        "avg_temperature_celsius": 19.5,
        "annual_rainfall_mm": 2100,
    }
    assert body["variety"] == {
        "species": "arabica",
        "cultivar": "Caturra",
        "rootstock": "own-rooted",
    }
    assert body["processing"] == {
        "method": "washed",
        "fermentation_hours": 18.0,
        "drying_method": "raised_beds",
    }
    assert body["roasting"] == {
        "roast_level": "medium",
        "development_time_percent": 22.0,
        "roaster_notes": "Roasted to first crack plus a short development.",
    }
    assert body["brewing"] == {
        "recommended_methods": ["pour_over", "aeropress"],
        "water_temperature_celsius": 94.0,
        "grind_size": "medium",
        "ratio": "1:16",
    }
    assert body["flavor"] == {
        "tasting_notes": ["jasmine", "red apple", "brown sugar", "citrus"],
        "acidity": "high",
        "body": "medium",
        "sweetness": "medium",
        "aftertaste": "Clean, lingering citrus and floral finish.",
    }

    # causal_links is explicitly out of scope for this endpoint (tracked in
    # #13), so it must not appear in the response at all.
    assert "causal_links" not in body


def test_get_coffee_chain_returns_404_for_nonexistent_id(client):
    response = client.get("/coffees/does-not-exist/chain")

    assert response.status_code == 404
    assert response.json()["detail"] is not None


def _build_coffee_with_causal_links(
    coffee_id: str, causal_links: list[models.CausalLink]
) -> models.Coffee:
    """`_build_coffee` fixture but with a caller-supplied `causal_links` list."""
    coffee = _build_coffee(coffee_id, "Coffee With Links", "Has causal links.")
    return coffee.model_copy(update={"causal_links": causal_links})


def test_get_coffee_causal_links_returns_links_in_factor_chain_order(
    client, db_session
):
    """#13: links must come back in factor-chain order (origin ->
    environment -> variety -> processing -> roasting -> brewing -> flavor),
    keyed on each link's `from_factor` -- not insertion order or DB id
    order.

    Seeded deliberately *out* of chain order: `roasting` (chain position 4)
    is inserted first, `origin` (position 0) second, `variety` (position 2)
    third. `upsert_coffee`/`_replace_causal_links` inserts rows in list
    order, so the autoincrement `causal_links.id` order -- and therefore any
    plain `row.causal_links`/insertion-order passthrough -- would come back
    as [roasting, origin, variety]. Only an implementation that actually
    sorts by chain position produces the expected [origin, variety,
    roasting].
    """
    coffee = _build_coffee_with_causal_links(
        "coffee-links-out-of-order",
        causal_links=[
            models.CausalLink(
                from_factor="roasting",
                to_factor="brewing",
                explanation="Roast development time affects extraction during brewing.",
            ),
            models.CausalLink(
                from_factor="origin",
                to_factor="environment",
                explanation="Farm elevation determines the growing environment's climate.",
            ),
            models.CausalLink(
                from_factor="variety",
                to_factor="processing",
                explanation="Caturra's thinner skin suits washed processing.",
            ),
        ],
    )
    upsert_coffee(db_session, coffee)
    db_session.flush()

    response = client.get("/coffees/coffee-links-out-of-order/causal-links")

    assert response.status_code == 200
    body = response.json()
    assert [link["from_factor"] for link in body] == ["origin", "variety", "roasting"]
    assert body == [
        {
            "from_factor": "origin",
            "to_factor": "environment",
            "explanation": "Farm elevation determines the growing environment's climate.",
        },
        {
            "from_factor": "variety",
            "to_factor": "processing",
            "explanation": "Caturra's thinner skin suits washed processing.",
        },
        {
            "from_factor": "roasting",
            "to_factor": "brewing",
            "explanation": "Roast development time affects extraction during brewing.",
        },
    ]


def test_get_coffee_causal_links_returns_404_for_nonexistent_id(client):
    response = client.get("/coffees/does-not-exist/causal-links")

    assert response.status_code == 404
    assert response.json()["detail"] is not None


def test_get_coffee_causal_links_returns_empty_list_for_coffee_without_links(
    client, db_session
):
    """A coffee with zero causal links is a real, reachable state (#9's
    asset check flags it as a data-quality issue but doesn't block the row
    from being written), so this must be `200` with `[]`, not an error."""
    upsert_coffee(
        db_session,
        _build_coffee("coffee-no-links", "No Links Coffee", "No causal links."),
    )
    db_session.flush()

    response = client.get("/coffees/coffee-no-links/causal-links")

    assert response.status_code == 200
    assert response.json() == []
