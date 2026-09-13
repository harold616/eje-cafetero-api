"""Tests for the SQLAlchemy 2.0 declarative models in `orm_models.py` (#5).

The structural tests (table/column/constraint shape) run against
`Base.metadata` directly and need no database.

The behavioural tests exercise the models against the local Postgres
instance from #2's docker-compose stack (`docker compose up -d`). If that
instance isn't reachable, those tests are skipped rather than failing the
whole suite — the CI-less, `uv run pytest`-from-anywhere workflow this repo
otherwise relies on for #2/#4 shouldn't hard-require a running database.
"""

from __future__ import annotations

import pytest
from sqlalchemy import UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.orm_models import (
    Base,
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

EXPECTED_TABLES = {
    "coffees",
    "origins",
    "environments",
    "varieties",
    "processing_methods",
    "roast_profiles",
    "brew_methods",
    "flavor_profiles",
    "causal_links",
}

FACTOR_TABLES = EXPECTED_TABLES - {"coffees", "causal_links"}


def _has_unique_constraint(table, column_name: str) -> bool:
    return any(
        isinstance(constraint, UniqueConstraint)
        and {c.name for c in constraint.columns} == {column_name}
        for constraint in table.constraints
    )


# --- Structural tests (no database needed) ---------------------------------


def test_metadata_declares_every_table_the_issue_names():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.parametrize("table_name", sorted(FACTOR_TABLES))
def test_factor_table_has_a_unique_not_null_foreign_key_to_coffees(table_name):
    """Each factor table's coffee_id is a NOT NULL, UNIQUE FK to coffees.id,
    enforcing the one-coffee-to-one-of-each-factor relationship."""
    table = Base.metadata.tables[table_name]
    column = table.c["coffee_id"]

    assert column.nullable is False
    assert len(column.foreign_keys) == 1
    assert next(iter(column.foreign_keys)).target_fullname == "coffees.id"
    assert _has_unique_constraint(table, "coffee_id")


def test_causal_links_foreign_key_to_coffees_is_not_unique():
    """A coffee can have many causal links, so coffee_id must NOT be unique
    on causal_links, unlike every factor table above."""
    table = Base.metadata.tables["causal_links"]
    column = table.c["coffee_id"]

    assert column.nullable is False
    assert len(column.foreign_keys) == 1
    assert next(iter(column.foreign_keys)).target_fullname == "coffees.id"
    assert not _has_unique_constraint(table, "coffee_id")


def test_causal_links_stores_distinct_columns_not_a_free_text_blob():
    table = Base.metadata.tables["causal_links"]
    for column_name in ("from_factor", "to_factor", "explanation"):
        assert column_name in table.c
        assert table.c[column_name].nullable is False


def test_coffees_primary_key_is_the_schema_id_field():
    table = Base.metadata.tables["coffees"]
    assert [c.name for c in table.primary_key.columns] == ["id"]
    assert table.c["name"].nullable is False
    assert table.c["summary"].nullable is False


# --- Behavioural tests against a live local Postgres ------------------------


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
        # A failed flush (e.g. the IntegrityError test) already rolls the
        # transaction back internally; only roll back here if it's still
        # active, to avoid a "transaction already deassociated" warning.
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


def _build_full_chain_coffee(coffee_id: str) -> Coffee:
    coffee = Coffee(id=coffee_id, name="Test Coffee", summary="A test fixture coffee.")
    coffee.origin = Origin(
        department="Quindío", municipality="Salento", farm_name="Finca Test"
    )
    coffee.environment = Environment(altitude_meters=1800, shade_type="partial_shade")
    coffee.variety = Variety(
        species="arabica", cultivar="Caturra", rootstock="own-rooted"
    )
    coffee.processing_method = ProcessingMethod(method="washed")
    coffee.roast_profile = RoastProfile(roast_level="medium")
    coffee.brew_method = BrewMethod(recommended_methods=["pour_over", "aeropress"])
    coffee.flavor_profile = FlavorProfile(
        tasting_notes=["citrus", "caramel"],
        acidity="high",
        body="light",
        sweetness="medium",
    )
    return coffee


def test_can_insert_and_fetch_a_full_factor_chain(db_session):
    coffee = _build_full_chain_coffee("test-full-chain")
    coffee.causal_links.append(
        CausalLink(
            from_factor="origin",
            to_factor="environment",
            explanation="High altitude farms cluster in this municipality.",
        )
    )
    coffee.causal_links.append(
        CausalLink(
            from_factor="processing",
            to_factor="flavor",
            explanation="Washed processing yields a cleaner, brighter cup.",
        )
    )

    db_session.add(coffee)
    db_session.flush()
    db_session.expire_all()

    fetched = db_session.get(Coffee, "test-full-chain")
    assert fetched is not None
    assert fetched.origin.department == "Quindío"
    assert fetched.environment.altitude_meters == 1800
    assert fetched.variety.cultivar == "Caturra"
    assert fetched.processing_method.method == "washed"
    assert fetched.roast_profile.roast_level == "medium"
    assert fetched.brew_method.recommended_methods == ["pour_over", "aeropress"]
    assert fetched.flavor_profile.acidity == "high"
    assert len(fetched.causal_links) == 2


def test_second_origin_for_same_coffee_violates_unique_constraint(db_session):
    coffee = Coffee(id="test-one-to-one", name="Test", summary="Test.")
    db_session.add(coffee)
    db_session.flush()

    db_session.add(
        Origin(
            coffee_id="test-one-to-one",
            department="Caldas",
            municipality="Manizales",
            farm_name="Farm A",
        )
    )
    db_session.flush()

    db_session.add(
        Origin(
            coffee_id="test-one-to-one",
            department="Caldas",
            municipality="Manizales",
            farm_name="Farm B",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_a_coffee_can_have_many_causal_links(db_session):
    coffee = Coffee(id="test-many-links", name="Test", summary="Test.")
    db_session.add(coffee)
    db_session.flush()

    db_session.add_all(
        [
            CausalLink(
                coffee_id="test-many-links",
                from_factor="origin",
                to_factor="environment",
                explanation="a",
            ),
            CausalLink(
                coffee_id="test-many-links",
                from_factor="environment",
                to_factor="variety",
                explanation="b",
            ),
            CausalLink(
                coffee_id="test-many-links",
                from_factor="roasting",
                to_factor="brewing",
                explanation="c",
            ),
        ]
    )
    db_session.flush()

    count = (
        db_session.query(CausalLink)
        .filter_by(coffee_id="test-many-links")
        .count()
    )
    assert count == 3
