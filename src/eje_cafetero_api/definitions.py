"""Dagster entry point for this project (#8).

`dagster dev` discovers `defs` here via the `[tool.dagster]` `module_name`
setting in `pyproject.toml` - running `dagster dev` from the repo root (with
the local Postgres from #2 up) is enough, no `-f`/`-m` flag needed. See the
README's "Dagster" section.
"""

from __future__ import annotations

import dagster as dg

from eje_cafetero_api.assets import DatabaseResource, all_assets

defs = dg.Definitions(
    assets=all_assets,
    resources={"database": DatabaseResource()},
)

__all__ = ["defs"]
