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

`GET /coffees` and `GET /coffees/{id}` (#11) are also defined here: a list
and a single-record endpoint over the `coffees` table, both shaped by
`models.CoffeeSummary` (adapted from #4's `models.Coffee` — see that class's
docstring for what's included/excluded and why). The full factor-chain
response and causal links are out of scope for #11 — see #12/#13. Auto-
generated docs are FastAPI's default `/docs`, unconfigured, per the issue's
"out of scope" list.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from eje_cafetero_api.db import get_database_url
from eje_cafetero_api.models import CoffeeSummary
from eje_cafetero_api.orm_models import Coffee

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


def get_session(engine: Engine = Depends(get_engine)) -> Iterator[Session]:
    """Yield a `Session` bound to the process-wide engine.

    A dependency (rather than a bare `with Session(engine) as ...` inline in
    each endpoint) so tests can override it directly — e.g. binding the
    yielded `Session` to a test's own connection/transaction instead of a
    fresh one, the same `app.dependency_overrides` mechanism `get_engine`
    already uses for `/health`.
    """
    with Session(engine) as session:
        yield session


@app.get("/coffees", response_model=list[CoffeeSummary])
def list_coffees(session: Session = Depends(get_session)) -> list[CoffeeSummary]:
    """Return every coffee currently in the database.

    `200` with an empty list on an empty database — not an error — since an
    empty `coffees` table is a valid (if uninteresting) state, not a failure.
    """
    rows = session.execute(select(Coffee)).scalars().all()
    return [CoffeeSummary.model_validate(row) for row in rows]


@app.get("/coffees/{coffee_id}", response_model=CoffeeSummary)
def get_coffee(
    coffee_id: str, session: Session = Depends(get_session)
) -> CoffeeSummary:
    """Return a single coffee by its `id`, or `404` if it doesn't exist.

    `session.get` returns `None` for a missing primary key rather than
    raising; that `None` is turned into an explicit `404` here so a bad id
    never comes back as a `200` with `null` or falls through to an
    unhandled-exception `500`.
    """
    row = session.get(Coffee, coffee_id)
    if row is None:
        raise HTTPException(status_code=404, detail="coffee not found")
    return CoffeeSummary.model_validate(row)
