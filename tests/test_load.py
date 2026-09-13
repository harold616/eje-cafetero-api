"""Tests for the ETL load step (#7): `upsert_coffee`.

These run against the local Postgres instance from #2's docker-compose stack
(`docker compose up -d`) — no mocks, per the issue's constraints, since this
task is specifically about write behavior (idempotency, transactions) a mock
can't verify. If that instance isn't reachable, the tests are skipped rather
than failing the whole suite, matching the convention already established in
`test_orm_models.py`.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api import models
from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.load import upsert_coffee
from eje_cafetero_api.orm_models import (
    BrewMethod,
    CausalLink,
    Coffee,
    Environment,
    FlavorProfile,
    Origin,
    ProcessingMethod,
    RoastProfile,
    Variety,
)

FACTOR_TABLES = [
    Origin,
    Environment,
    Variety,
    ProcessingMethod,
    RoastProfile,
    BrewMethod,
    FlavorProfile,
]


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


def _build_coffee(
    coffee_id: str = "test-upsert-coffee",
    *,
    department: models.Department = "Quindío",
    causal_links: list[tuple[str, str, str]] | None = None,
) -> models.Coffee:
    if causal_links is None:
        causal_links = [("origin", "environment", "High altitude, cooler nights.")]

    return models.Coffee(
        id=coffee_id,
        name="Test Coffee",
        summary="A test fixture coffee.",
        origin=models.Origin(
            department=department, municipality="Salento", farm_name="Finca Test"
        ),
        environment=models.Environment(
            altitude_meters=1800, shade_type="partial_shade"
        ),
        variety=models.Variety(
            species="arabica", cultivar="Caturra", rootstock="own-rooted"
        ),
        processing=models.Processing(method="washed"),
        roasting=models.Roasting(roast_level="medium"),
        brewing=models.Brewing(recommended_methods=["pour_over", "aeropress"]),
        flavor=models.Flavor(
            tasting_notes=["citrus", "caramel"],
            acidity="high",
            body="light",
            sweetness="medium",
        ),
        causal_links=[
            models.CausalLink(from_factor=f, to_factor=t, explanation=e)
            for f, t, e in causal_links
        ],
    )


def _row_counts(session, coffee_id: str) -> dict[str, int]:
    counts = {
        "coffees": session.scalar(
            select(func.count()).select_from(Coffee).where(Coffee.id == coffee_id)
        )
    }
    for model in FACTOR_TABLES:
        counts[model.__tablename__] = session.scalar(
            select(func.count()).select_from(model).where(model.coffee_id == coffee_id)
        )
    counts["causal_links"] = session.scalar(
        select(func.count())
        .select_from(CausalLink)
        .where(CausalLink.coffee_id == coffee_id)
    )
    return counts


def test_first_load_creates_one_row_per_table(db_session):
    coffee = _build_coffee("test-first-load")

    upsert_coffee(db_session, coffee)
    db_session.flush()
    db_session.expire_all()

    fetched = db_session.get(Coffee, "test-first-load")
    assert fetched is not None
    assert fetched.name == "Test Coffee"
    assert fetched.origin.department == "Quindío"
    assert fetched.environment.altitude_meters == 1800
    assert fetched.variety.cultivar == "Caturra"
    assert fetched.processing_method.method == "washed"
    assert fetched.roast_profile.roast_level == "medium"
    assert fetched.brew_method.recommended_methods == ["pour_over", "aeropress"]
    assert fetched.flavor_profile.acidity == "high"
    assert len(fetched.causal_links) == 1

    counts = _row_counts(db_session, "test-first-load")
    assert all(count == 1 for count in counts.values())


def test_unchanged_reload_produces_no_duplicates(db_session):
    coffee = _build_coffee("test-unchanged-reload")

    upsert_coffee(db_session, coffee)
    db_session.flush()

    # Re-run with an identical (but separately constructed) Coffee object.
    upsert_coffee(db_session, _build_coffee("test-unchanged-reload"))
    db_session.flush()
    db_session.expire_all()

    counts = _row_counts(db_session, "test-unchanged-reload")
    assert all(count == 1 for count in counts.values()), counts


def test_changed_fields_update_existing_rows_in_place(db_session):
    coffee_id = "test-changed-fields"
    upsert_coffee(db_session, _build_coffee(coffee_id, department="Quindío"))
    db_session.flush()

    upsert_coffee(db_session, _build_coffee(coffee_id, department="Caldas"))
    db_session.flush()
    db_session.expire_all()

    fetched = db_session.get(Coffee, coffee_id)
    assert fetched.origin.department == "Caldas"

    counts = _row_counts(db_session, coffee_id)
    assert all(count == 1 for count in counts.values()), counts


def test_reload_with_different_causal_links_replaces_not_accumulates(db_session):
    coffee_id = "test-replace-links"
    first_links = [
        ("origin", "environment", "link a"),
        ("environment", "variety", "link b"),
    ]
    second_links = [("roasting", "brewing", "a completely different link")]

    upsert_coffee(db_session, _build_coffee(coffee_id, causal_links=first_links))
    db_session.flush()

    upsert_coffee(db_session, _build_coffee(coffee_id, causal_links=second_links))
    db_session.flush()
    db_session.expire_all()

    fetched = db_session.get(Coffee, coffee_id)
    assert len(fetched.causal_links) == 1
    assert fetched.causal_links[0].from_factor == "roasting"
    assert fetched.causal_links[0].to_factor == "brewing"
    assert fetched.causal_links[0].explanation == "a completely different link"


def test_reload_with_empty_causal_links_clears_old_ones(db_session):
    coffee_id = "test-clear-links"
    upsert_coffee(
        db_session,
        _build_coffee(coffee_id, causal_links=[("origin", "flavor", "some link")]),
    )
    db_session.flush()

    upsert_coffee(db_session, _build_coffee(coffee_id, causal_links=[]))
    db_session.flush()
    db_session.expire_all()

    fetched = db_session.get(Coffee, coffee_id)
    assert fetched.causal_links == []


def test_failure_partway_through_leaves_no_partial_write(db_session, monkeypatch):
    """A failure partway through the write must not leave partial rows once
    the caller rolls back — the whole upsert happens in one transaction.

    `upsert_coffee` never commits (the caller owns the transaction boundary,
    same convention as the rest of this codebase), and SQLAlchemy's
    autoflush means the `coffees` row and every factor row are already
    flushed to Postgres by the time `_replace_causal_links` (the final
    step) runs. Forcing that final step to fail and then rolling back must
    undo everything flushed earlier in the same call, proving there is no
    way to observe a partially-written coffee.
    """
    import eje_cafetero_api.load as load_module

    coffee_id = "test-partial-write"

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure during causal_links replacement")

    monkeypatch.setattr(load_module, "_replace_causal_links", _boom)

    with pytest.raises(RuntimeError, match="simulated failure"):
        upsert_coffee(db_session, _build_coffee(coffee_id))

    db_session.rollback()

    assert db_session.get(Coffee, coffee_id) is None
    counts = _row_counts(db_session, coffee_id)
    assert all(count == 0 for count in counts.values()), counts
