"""Dagster asset checks for data-quality rules Pydantic's shape validation
can't express (#9).

Pydantic (#4) already enforces *shape*: required fields present, correct
types, values inside a fixed set. These checks enforce *semantic* rules that
are only meaningful once a full `Coffee` object exists:

- every coffee documents at least one causal link
- every coffee's altitude is plausible for coffee cultivation at all

Both checks attach to the `coffee` asset (#8) via `@dagster.asset_check` and
run *after* `coffee` has already materialized (parsed, validated, and
upserted into Postgres by `load_coffee`/`upsert_coffee`). That ordering is
what makes these checks non-blocking by construction: `coffee`'s body has
already committed the row before either check function runs, and neither
check is declared with `blocking=True`. So a coffee that fails one or both
checks still has its full factor chain sitting in Postgres - the check
result is reported as a separate pass/fail entry on the run, distinct from
the asset's own success/failure, exactly as the Dagster UI shows asset
checks. There is no way for one of these checks, as specified, to un-write
data that `coffee` already committed - that would require deleting rows on
check failure, which the issue explicitly says not to do.
"""

from __future__ import annotations

import dagster as dg

from eje_cafetero_api import models
from eje_cafetero_api.assets import coffee

#: Plausible altitude range for coffee cultivation, in meters above sea
#: level (masl).
#:
#: Coffee is grown as two species with very different elevation profiles:
#: - Arabica: roughly 800-2,200 masl (higher elevations produce denser,
#:   more complex beans thanks to slower cherry maturation in cooler air).
#: - Robusta: roughly 200-800 masl (more heat-tolerant, commercially grown
#:   at much lower elevation).
#: Sources: National Coffee Association, "Coffee Regions of the World"
#: (https://www.aboutcoffee.org/origins/coffee-regions-of-the-world/); Fathom
#: Coffee, "Coffee Regions of the World: A Complete Guide"
#: (https://fathomcoffee.com/coffee-regions-guide/) - both cite Arabica at
#: ~800-2,200 masl and Robusta at ~200-800 masl.
#:
#: This schema's `variety.species` field (see `_docs/schema.md`) allows
#: either species per coffee entry, and this check has no per-coffee access
#: to a species-specific bound in a simple range check, so the two ranges
#: above are unioned into one plausible envelope covering both: 200-2,200
#: masl. A coffee outside that envelope is implausible for either species.
MIN_PLAUSIBLE_ALTITUDE_METERS = 200
MAX_PLAUSIBLE_ALTITUDE_METERS = 2200


@dg.asset_check(
    asset=coffee,
    description="Every coffee documents at least one causal_links entry.",
)
def has_causal_links(coffee: models.Coffee) -> dg.AssetCheckResult:
    count = len(coffee.causal_links)
    return dg.AssetCheckResult(
        passed=count > 0,
        metadata={"causal_links_count": count},
    )


@dg.asset_check(
    asset=coffee,
    description=(
        "Coffee's altitude falls within a documented plausible range for "
        "coffee cultivation "
        f"({MIN_PLAUSIBLE_ALTITUDE_METERS}-{MAX_PLAUSIBLE_ALTITUDE_METERS} masl)."
    ),
)
def altitude_is_plausible(coffee: models.Coffee) -> dg.AssetCheckResult:
    altitude = coffee.environment.altitude_meters
    passed = MIN_PLAUSIBLE_ALTITUDE_METERS <= altitude <= MAX_PLAUSIBLE_ALTITUDE_METERS
    return dg.AssetCheckResult(
        passed=passed,
        metadata={
            "altitude_meters": altitude,
            "min_plausible_altitude_meters": MIN_PLAUSIBLE_ALTITUDE_METERS,
            "max_plausible_altitude_meters": MAX_PLAUSIBLE_ALTITUDE_METERS,
        },
    )


all_asset_checks = [has_causal_links, altitude_is_plausible]

__all__ = [
    "MIN_PLAUSIBLE_ALTITUDE_METERS",
    "MAX_PLAUSIBLE_ALTITUDE_METERS",
    "has_causal_links",
    "altitude_is_plausible",
    "all_asset_checks",
]
