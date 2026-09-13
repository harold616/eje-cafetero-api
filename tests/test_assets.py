"""Tests for the Dagster software-defined assets wrapping the ETL pipeline
(#8): `eje_cafetero_api.assets` and `eje_cafetero_api.definitions`.

Structural tests (asset graph shape) need no database. The materialization
tests run against the local Postgres instance from #2's docker-compose
stack, same convention as `test_load.py`/`test_orm_models.py`: skipped
rather than failing the whole suite if that instance isn't reachable.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api.assets import (
    DatabaseResource,
    all_assets,
    brewing,
    coffee,
    environment,
    flavor,
    origin,
    processing,
    roasting,
    variety,
)
from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.definitions import defs
from eje_cafetero_api.etl import CoffeeYamlError
from eje_cafetero_api.orm_models import CausalLink, Coffee

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_COFFEE_PATH = FIXTURES_DIR / "valid_coffee.yaml"
SYNTAX_ERROR_PATH = FIXTURES_DIR / "syntax_error.yaml"

# The seven per-factor asset names, in factor-chain order.
FACTOR_ASSET_NAMES = [
    "origin",
    "environment",
    "variety",
    "processing",
    "roasting",
    "brewing",
    "flavor",
]


def _asset_deps(assets_def: dg.AssetsDefinition) -> list[str]:
    (key,) = assets_def.keys
    return sorted(dep.to_user_string() for dep in assets_def.asset_deps[key])


# --- Structural tests (no database needed) ----------------------------------


def test_one_asset_exists_for_each_factor_and_for_the_coffee_itself():
    asset_names = {next(iter(a.keys)).to_user_string() for a in all_assets}
    assert asset_names == {"coffee"} | set(FACTOR_ASSET_NAMES)


def test_coffee_asset_has_no_upstream_dependencies():
    assert _asset_deps(coffee) == []


@pytest.mark.parametrize(
    ("asset_def", "expected_deps"),
    [
        (origin, ["coffee"]),
        (environment, ["coffee", "origin"]),
        (variety, ["coffee", "environment"]),
        (processing, ["coffee", "variety"]),
        (roasting, ["coffee", "processing"]),
        (brewing, ["coffee", "roasting"]),
        (flavor, ["coffee", "brewing"]),
    ],
)
def test_factor_asset_depends_on_coffee_and_the_previous_factor(
    asset_def, expected_deps
):
    """Dependency edges mirror the factor chain: each factor asset depends
    on `coffee` (the root that parses/loads) and, except for `origin`, on
    the factor immediately before it in origin -> ... -> flavor."""
    assert _asset_deps(asset_def) == sorted(expected_deps)


def test_definitions_object_exposes_every_asset_for_dagster_dev_to_discover():
    """`dagster dev` (per the README) discovers `defs` in this module -
    every asset the issue names must actually be registered on it."""
    discovered = {
        key.to_user_string() for key in defs.resolve_asset_graph().get_all_asset_keys()
    }
    assert discovered == {"coffee"} | set(FACTOR_ASSET_NAMES)


# --- Materialization tests against a live local Postgres --------------------


@pytest.fixture()
def live_database_url() -> str:
    url = get_database_url()
    engine = create_engine(url)
    try:
        engine.connect().close()
    except OperationalError:
        pytest.skip(
            "local Postgres instance is not reachable; "
            "start it with `docker compose up -d` (see #2)"
        )
    finally:
        engine.dispose()
    return url


def _row_counts(coffee_id: str, database_url: str) -> dict[str, int]:
    engine = create_engine(database_url)
    try:
        with Session(bind=engine) as session:
            counts = {
                "coffees": session.scalar(
                    select(func.count())
                    .select_from(Coffee)
                    .where(Coffee.id == coffee_id)
                ),
                "causal_links": session.scalar(
                    select(func.count())
                    .select_from(CausalLink)
                    .where(CausalLink.coffee_id == coffee_id)
                ),
            }
    finally:
        engine.dispose()
    return counts


def test_materializing_the_full_graph_against_a_valid_file_succeeds_and_loads_postgres(
    live_database_url,
):
    result = dg.materialize(
        all_assets,
        resources={"database": DatabaseResource()},
        run_config={"ops": {"coffee": {"config": {"path": str(VALID_COFFEE_PATH)}}}},
    )

    assert result.success
    # All eight assets actually ran, not just the root.
    materialized = {
        event.event_specific_data.materialization.asset_key.to_user_string()
        for event in result.get_asset_materialization_events()
    }
    assert materialized == {"coffee"} | set(FACTOR_ASSET_NAMES)

    counts = _row_counts("finca-el-ocaso-caturra-washed", live_database_url)
    assert counts["coffees"] == 1
    assert counts["causal_links"] == 6


def test_materializing_against_a_malformed_file_fails_loudly_not_silently(
    live_database_url,
):
    """A syntax-broken source file must surface as a failed Dagster run -
    `load_coffee` (#6) raises `CoffeeYamlError`, which must propagate out of
    the `coffee` asset rather than being swallowed into a quiet no-op."""
    with pytest.raises(CoffeeYamlError):
        dg.materialize(
            all_assets,
            resources={"database": DatabaseResource()},
            run_config={
                "ops": {"coffee": {"config": {"path": str(SYNTAX_ERROR_PATH)}}}
            },
        )

    # A separate, non-raising run confirms the failure is recorded as a
    # failed run (visible in the Dagster UI), not just a raised exception in
    # this test process.
    result = dg.materialize(
        all_assets,
        resources={"database": DatabaseResource()},
        run_config={"ops": {"coffee": {"config": {"path": str(SYNTAX_ERROR_PATH)}}}},
        raise_on_error=False,
    )
    assert result.success is False
    failure_events = [
        event
        for event in result.all_events
        if event.event_type_value in ("STEP_FAILURE", "RUN_FAILURE")
    ]
    assert failure_events, "expected the failed run to record a failure event"
