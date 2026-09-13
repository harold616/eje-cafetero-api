"""FastAPI application skeleton (#10).

Exposes a single `GET /health` endpoint that proves the API can actually
talk to Postgres, not just that the process is up: it opens a connection
through #5's SQLAlchemy engine setup (reusing `db.get_database_url()`, so
the same `POSTGRES_*` env vars from #2's `.env.example` are the only
config surface — no new env vars) and runs `SELECT 1`.

- `200` only when that query actually succeeds.
- `503` (never an unhandled exception) if the database is unreachable.

Run it under Uvicorn:

    uv run uvicorn eje_cafetero_api.app:app --reload

Everything beyond `/health` (the `/coffees` endpoints, etc.) is out of
scope for this task — see #11/#12/#13. Auto-generated docs are FastAPI's
default `/docs`, unconfigured, per the issue's "out of scope" list.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, Response
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from eje_cafetero_api.db import get_database_url

app = FastAPI(title="Eje Cafetero API")


@lru_cache
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine, built on first use.

    A dependency (rather than a module-level constant) so tests can swap it
    out via `app.dependency_overrides` — e.g. to simulate the database being
    unreachable without having to actually take Postgres down.
    """
    return create_engine(get_database_url())


@app.get("/health")
def health(response: Response, engine: Engine = Depends(get_engine)) -> dict:
    """Report service health by actually querying Postgres.

    Returns `200` only after a real `SELECT 1` round-trip succeeds. If the
    database is unreachable, the connection attempt raises
    `sqlalchemy.exc.OperationalError`, which is caught here and turned into
    a `503` response instead of a `200` or an unhandled exception.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        response.status_code = 503
        return {"status": "error", "detail": "database unreachable"}
    return {"status": "ok"}
