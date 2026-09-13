"""ETL load step: write a validated `Coffee` into Postgres, idempotently.

Takes the `eje_cafetero_api.models.Coffee` object produced by #6's
`load_coffee` and writes it — plus its seven one-per-coffee factor rows and
its list of `causal_links` — into the Postgres tables defined by #5's
`orm_models`.

Upsert key
----------
The upsert key is `Coffee.id` (the schema's `id` field, e.g.
`finca-el-ocaso-caturra-washed`; see `_docs/schema.md`). `#3`/`#4` already
define `id` as a required, unique, kebab-case identifier that by convention
matches the source YAML filename stem, and `orm_models.Coffee.id` is that
table's primary key. There is no need to derive a separate slug — `id` *is*
the natural key, so `upsert_coffee` keys every write off it directly.

Idempotency strategy
---------------------
For the root `coffees` row and each one-per-coffee factor row (`origins`,
`environments`, `varieties`, `processing_methods`, `roast_profiles`,
`brew_methods`, `flavor_profiles`), `upsert_coffee` looks up the existing row
by `coffee_id` (or `id` for `coffees` itself) and updates its columns in
place if found, or inserts a new row if not. This means:

- Running the function twice with unchanged input updates the same rows
  in place both times -> exactly one row per table, no duplicates.
- Changed field values on a re-run overwrite the existing row's columns.

For `causal_links` — the one section that is a list rather than a single
row — re-running with a different list must *replace* the old set, not
merge into it (an update-in-place strategy doesn't make sense for a list
whose membership itself changes). `upsert_coffee` deletes every existing
`causal_links` row for this `coffee_id` and inserts the new list, inside the
same transaction as everything else.

Transaction
-----------
All of the above happens using the caller's `Session` without an
intermediate commit: every delete/insert/update is flushed together and the
caller commits (or rolls back) once. If any statement fails (e.g. a
`Literal`-violating value that slips past Pydantic but violates a DB
constraint), nothing flushed so far is visible to other transactions and a
`session.rollback()` by the caller — or a context-managed `Session.begin()`
— leaves the database exactly as it was before the call.
"""

from __future__ import annotations

from eje_cafetero_api import models
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

__all__ = ["upsert_coffee"]


def _set_fields(row, **fields) -> None:
    """Assign every keyword as an attribute on `row`."""
    for key, value in fields.items():
        setattr(row, key, value)


def upsert_coffee(session, coffee: models.Coffee) -> Coffee:
    """Write a validated `Coffee` and its factor chain into Postgres.

    Idempotent on `coffee.id` (see module docstring for the upsert key and
    per-table strategy). Does not commit — the caller controls the
    transaction boundary, so a failure partway through can be rolled back
    leaving the database unchanged.

    Args:
        session: an open SQLAlchemy `Session`.
        coffee: a validated `Coffee` object (see `eje_cafetero_api.models`,
            typically produced by `eje_cafetero_api.etl.load_coffee`).

    Returns:
        The persisted `orm_models.Coffee` row (pending flush/commit).
    """
    row = session.get(Coffee, coffee.id)
    if row is None:
        row = Coffee(id=coffee.id)
        session.add(row)
    _set_fields(row, name=coffee.name, summary=coffee.summary)

    _upsert_one_to_one(
        session,
        Origin,
        coffee.id,
        department=coffee.origin.department,
        municipality=coffee.origin.municipality,
        farm_name=coffee.origin.farm_name,
        producer=coffee.origin.producer,
        latitude=coffee.origin.latitude,
        longitude=coffee.origin.longitude,
    )
    _upsert_one_to_one(
        session,
        Environment,
        coffee.id,
        altitude_meters=coffee.environment.altitude_meters,
        shade_type=coffee.environment.shade_type,
        avg_temperature_celsius=coffee.environment.avg_temperature_celsius,
        annual_rainfall_mm=coffee.environment.annual_rainfall_mm,
    )
    _upsert_one_to_one(
        session,
        Variety,
        coffee.id,
        species=coffee.variety.species,
        cultivar=coffee.variety.cultivar,
        rootstock=coffee.variety.rootstock,
    )
    _upsert_one_to_one(
        session,
        ProcessingMethod,
        coffee.id,
        method=coffee.processing.method,
        fermentation_hours=coffee.processing.fermentation_hours,
        drying_method=coffee.processing.drying_method,
    )
    _upsert_one_to_one(
        session,
        RoastProfile,
        coffee.id,
        roast_level=coffee.roasting.roast_level,
        development_time_percent=coffee.roasting.development_time_percent,
        roaster_notes=coffee.roasting.roaster_notes,
    )
    _upsert_one_to_one(
        session,
        BrewMethod,
        coffee.id,
        recommended_methods=list(coffee.brewing.recommended_methods),
        water_temperature_celsius=coffee.brewing.water_temperature_celsius,
        grind_size=coffee.brewing.grind_size,
        ratio=coffee.brewing.ratio,
    )
    _upsert_one_to_one(
        session,
        FlavorProfile,
        coffee.id,
        tasting_notes=list(coffee.flavor.tasting_notes),
        acidity=coffee.flavor.acidity,
        body=coffee.flavor.body,
        sweetness=coffee.flavor.sweetness,
        aftertaste=coffee.flavor.aftertaste,
    )

    _replace_causal_links(session, coffee.id, coffee.causal_links)

    return row


def _upsert_one_to_one(session, model, coffee_id: str, **fields) -> None:
    """Update-in-place-or-insert the single row `model` has for `coffee_id`."""
    row = session.query(model).filter_by(coffee_id=coffee_id).one_or_none()
    if row is None:
        row = model(coffee_id=coffee_id)
        session.add(row)
    _set_fields(row, **fields)


def _replace_causal_links(
    session, coffee_id: str, causal_links: list[models.CausalLink]
) -> None:
    """Delete every existing `causal_links` row for `coffee_id` and insert
    the new set, so a re-run replaces links rather than accumulating them."""
    session.query(CausalLink).filter_by(coffee_id=coffee_id).delete()
    for link in causal_links:
        session.add(
            CausalLink(
                coffee_id=coffee_id,
                from_factor=link.from_factor,
                to_factor=link.to_factor,
                explanation=link.explanation,
            )
        )
