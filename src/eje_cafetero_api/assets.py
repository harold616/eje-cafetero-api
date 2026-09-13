"""Dagster software-defined assets wrapping the ETL pipeline (#8).

One asset per factor in the causal chain (origin, environment, variety,
processing, roasting, brewing, flavor) plus one asset for the coffee itself,
per `_docs/outdated/architecture.md`'s asset-per-factor model. Dependency
edges mirror the factor chain: `coffee` -> `origin` -> `environment` ->
`variety` -> `processing` -> `roasting` -> `brewing` -> `flavor`.

These assets are thin wrappers, not new implementations:

- `coffee` is the only asset that touches disk or the database. It calls
  #6's `eje_cafetero_api.etl.load_coffee` to parse and validate the source
  YAML, then #7's `eje_cafetero_api.load.upsert_coffee` to write the full
  factor chain into Postgres in one transaction.
- The seven factor assets downstream of `coffee` do not re-parse the source
  file or re-touch the database — `upsert_coffee` already wrote every
  table in one shot. They exist so the Dagster UI's asset graph shows the
  factor chain as first-class lineage (per architecture.md), each one
  simply surfacing its slice of the already-validated `Coffee` object for
  observability and for any downstream asset checks (see #9).

Materializing against a malformed source file fails loudly: `load_coffee`
raises `CoffeeYamlError` or `pydantic.ValidationError`, which propagates out
of the `coffee` asset and fails the Dagster run - never a silent no-op.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import dagster as dg
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eje_cafetero_api import models
from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.etl import load_coffee
from eje_cafetero_api.load import upsert_coffee

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: Default source file materialized when no run config overrides it -
#: the reference example checked in at `data/coffees/example.yaml`.
DEFAULT_SOURCE_PATH = "data/coffees/example.yaml"

__all__ = [
    "CoffeeSourceConfig",
    "DatabaseResource",
    "coffee",
    "origin",
    "environment",
    "variety",
    "processing",
    "roasting",
    "brewing",
    "flavor",
    "all_assets",
]


class CoffeeSourceConfig(dg.Config):
    """Run configuration: which source coffee YAML file to materialize.

    `path` may be absolute or relative to the repo root. Defaults to the
    checked-in reference example so `dagster dev` has something sensible to
    materialize with no run config at all.
    """

    path: str = DEFAULT_SOURCE_PATH


class DatabaseResource(dg.ConfigurableResource):
    """Dagster resource providing a transactional session against the local
    Postgres instance (same Docker Compose stack as the API; see #2).

    Not a new database layer - it just gives the `coffee` asset a
    `Session` to hand to #7's `upsert_coffee`, and owns the commit/rollback
    transaction boundary that `upsert_coffee` deliberately leaves to its
    caller (see `load.py`'s module docstring).
    """

    @contextmanager
    def session(self) -> Iterator[Session]:
        engine = create_engine(get_database_url())
        session = Session(bind=engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


@dg.asset(
    description=(
        "Parses and validates one coffee source YAML file (#6) and upserts "
        "it - plus its full factor chain and causal links - into Postgres "
        "(#7). The root of the factor-chain asset graph."
    ),
)
def coffee(config: CoffeeSourceConfig, database: DatabaseResource) -> models.Coffee:
    parsed = load_coffee(_resolve_path(config.path))
    with database.session() as session:
        upsert_coffee(session, parsed)
    return parsed


@dg.asset(description="Where the coffee was grown - first link in the factor chain.")
def origin(coffee: models.Coffee) -> models.Origin:
    return coffee.origin


@dg.asset(description="Growing-environment conditions, caused by origin.")
def environment(coffee: models.Coffee, origin: models.Origin) -> models.Environment:
    return coffee.environment


@dg.asset(description="Botanical variety/cultivar, shaped by environment.")
def variety(coffee: models.Coffee, environment: models.Environment) -> models.Variety:
    return coffee.variety


@dg.asset(description="Post-harvest processing method, chosen for the variety.")
def processing(coffee: models.Coffee, variety: models.Variety) -> models.Processing:
    return coffee.processing


@dg.asset(description="Roast profile applied to the processed green beans.")
def roasting(coffee: models.Coffee, processing: models.Processing) -> models.Roasting:
    return coffee.roasting


@dg.asset(description="Recommended brewing parameters for the roast profile.")
def brewing(coffee: models.Coffee, roasting: models.Roasting) -> models.Brewing:
    return coffee.brewing


@dg.asset(description="Sensory/tasting profile produced by the brew.")
def flavor(coffee: models.Coffee, brewing: models.Brewing) -> models.Flavor:
    return coffee.flavor


all_assets = [coffee, origin, environment, variety, processing, roasting, brewing, flavor]
