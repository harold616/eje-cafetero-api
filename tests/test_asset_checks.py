"""Tests for the Dagster asset checks (#9) attached to the `coffee` asset
(#8): `eje_cafetero_api.asset_checks`.

These run against the local Postgres instance from #2's docker-compose
stack, same convention as `test_assets.py`: skipped rather than failing the
whole suite if that instance isn't reachable.

`dagster.materialize` (used by `test_assets.py`) does not accept
`AssetChecksDefinition`s in this Dagster version (1.13) - it type-checks its
`assets` argument to `(AssetsDefinition, AssetSpec, SourceAsset)` and never
threads an `asset_checks` list into the ephemeral job it builds. To exercise
assets *and* their checks together in one run (so we can assert on
`AssetCheckEvaluation` events), tests here build a small `Definitions`
object directly and execute its implicit global asset job in-process
instead - the same execution path `dagster dev`/`dagster asset materialize`
use, just invoked without the CLI.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api.asset_checks import (
    MAX_PLAUSIBLE_ALTITUDE_METERS,
    MIN_PLAUSIBLE_ALTITUDE_METERS,
    all_asset_checks,
)
from eje_cafetero_api.assets import DatabaseResource, all_assets
from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.orm_models import CausalLink, Coffee

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_COFFEE_PATH = FIXTURES_DIR / "valid_coffee.yaml"
NO_CAUSAL_LINKS_PATH = FIXTURES_DIR / "valid_coffee_no_causal_links.yaml"
ALTITUDE_OUT_OF_RANGE_PATH = FIXTURES_DIR / "valid_coffee_altitude_out_of_range.yaml"

COFFEE_ID = "finca-el-ocaso-caturra-washed"


# --- Structural tests (no database needed) ----------------------------------


def test_both_checks_are_registered_against_the_coffee_asset():
    specs = [spec for check in all_asset_checks for spec in check.check_specs]
    assert {spec.name for spec in specs} == {
        "has_causal_links",
        "altitude_is_plausible",
    }
    for spec in specs:
        assert spec.asset_key.to_user_string() == "coffee"


def test_neither_check_is_declared_blocking():
    """A coffee failing a check must still have its data materialized. The
    `coffee` asset already commits its Postgres write inside its own body,
    before either check runs, so checks are non-blocking by construction -
    but pin `blocking=False` explicitly too, since a `blocking=True` check
    would additionally stop *downstream* factor assets (not `coffee` itself)
    on failure, which the issue doesn't ask for."""
    for check in all_asset_checks:
        (spec,) = check.check_specs
        assert spec.blocking is False


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


def _materialize_with_checks(source_path: Path) -> dg.ExecuteInProcessResult:
    """Materialize the full asset graph *and* run its asset checks in one
    in-process run, mirroring what `dagster asset materialize` does against
    `definitions.py`'s `defs` object."""
    defs = dg.Definitions(
        assets=all_assets,
        asset_checks=all_asset_checks,
        resources={"database": DatabaseResource()},
    )
    job = defs.resolve_implicit_global_asset_job_def()
    return job.execute_in_process(
        run_config={"ops": {"coffee": {"config": {"path": str(source_path)}}}},
        raise_on_error=False,
    )


def _check_results(result: dg.ExecuteInProcessResult) -> dict[str, bool]:
    return {
        evaluation.asset_check_key.name: evaluation.passed
        for evaluation in result.get_asset_check_evaluations()
    }


def _coffee_row_count(coffee_id: str, database_url: str) -> int:
    engine = create_engine(database_url)
    try:
        with Session(bind=engine) as session:
            return session.scalar(
                select(func.count()).select_from(Coffee).where(Coffee.id == coffee_id)
            )
    finally:
        engine.dispose()


def _causal_link_count(coffee_id: str, database_url: str) -> int:
    engine = create_engine(database_url)
    try:
        with Session(bind=engine) as session:
            return session.scalar(
                select(func.count())
                .select_from(CausalLink)
                .where(CausalLink.coffee_id == coffee_id)
            )
    finally:
        engine.dispose()


def test_coffee_passing_both_checks_reports_both_as_passed_and_materializes(
    live_database_url,
):
    result = _materialize_with_checks(VALID_COFFEE_PATH)

    assert result.success
    checks = _check_results(result)
    assert checks == {"has_causal_links": True, "altitude_is_plausible": True}
    assert _coffee_row_count(COFFEE_ID, live_database_url) == 1
    assert _causal_link_count(COFFEE_ID, live_database_url) == 6


def test_coffee_with_no_causal_links_fails_only_that_check_but_still_materializes(
    live_database_url,
):
    result = _materialize_with_checks(NO_CAUSAL_LINKS_PATH)

    # The overall run still "succeeds" - a non-blocking check failure does
    # not fail the run or the asset, only the check itself is reported as
    # failed, distinct from the asset's own (successful) materialization.
    assert result.success
    checks = _check_results(result)
    assert checks == {"has_causal_links": False, "altitude_is_plausible": True}

    materialized = {
        event.event_specific_data.materialization.asset_key.to_user_string()
        for event in result.get_asset_materialization_events()
    }
    assert "coffee" in materialized
    assert _coffee_row_count(COFFEE_ID, live_database_url) == 1
    assert _causal_link_count(COFFEE_ID, live_database_url) == 0


def test_coffee_with_altitude_out_of_range_fails_only_that_check_but_still_materializes(
    live_database_url,
):
    result = _materialize_with_checks(ALTITUDE_OUT_OF_RANGE_PATH)

    assert result.success
    checks = _check_results(result)
    assert checks == {"has_causal_links": True, "altitude_is_plausible": False}

    materialized = {
        event.event_specific_data.materialization.asset_key.to_user_string()
        for event in result.get_asset_materialization_events()
    }
    assert "coffee" in materialized
    assert _coffee_row_count(COFFEE_ID, live_database_url) == 1
    assert _causal_link_count(COFFEE_ID, live_database_url) == 1


# --- Unit tests for the check functions themselves --------------------------


def test_altitude_bound_matches_documented_constants():
    assert MIN_PLAUSIBLE_ALTITUDE_METERS == 200
    assert MAX_PLAUSIBLE_ALTITUDE_METERS == 2200
