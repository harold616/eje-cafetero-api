# Eje Cafetero API

A data pipeline and API modeling coffees from Colombia's Eje Cafetero — and, critically, the causal chain behind why each coffee tastes the way it does: **origin → environment → variety → processing → roasting → brewing → flavor**.

This is Phase 1 of a larger product vision (see [`_docs/plan.md`](./_docs/plan.md)): an immersive visual experience for home coffee enthusiasts to explore that causal chain. Phase 1 is backend-first — an ETL pipeline and API — with the visual frontend deferred to a later phase.

Cause-and-effect relationships (e.g. "high altitude → slower cherry development → processing choices → flavor") are modeled as first-class, queryable data, not free text.

This phase also doubles as a DataOps skill-building project: orchestration, data quality checks, CI/CD, and observability are treated as core parts of the build. See [`_docs/architecture.md`](./_docs/architecture.md) for the full tech stack and rationale, and [`_docs/tasks.md`](./_docs/tasks.md) for the current task backlog.

## Stack

Python · Dagster · PostgreSQL · FastAPI · Pydantic v2 · SQLAlchemy 2.0 + Alembic · uv · pytest · GitHub Actions

## Local development

A local, persistent PostgreSQL instance runs via Docker Compose.

1. Copy `.env.example` to `.env` and adjust values if needed:

   ```sh
   cp .env.example .env
   ```

2. Start Postgres:

   ```sh
   docker compose up -d
   ```

3. Confirm connectivity (runs `psql` inside the running container, so no local `psql` client is required — it uses the same `POSTGRES_USER`/`POSTGRES_DB` values from `.env` that the container was started with):

   ```sh
   docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\conninfo"'
   ```

4. Stop Postgres (data persists in a named volume):

   ```sh
   docker compose down
   ```

   To also wipe the data volume: `docker compose down -v`.
