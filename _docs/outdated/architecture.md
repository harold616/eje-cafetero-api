# Architecture — Phase 1 (Data + API)

Companion to [`plan.md`](./plan.md). Covers the technical approach for the current build phase: an ETL pipeline and API that model coffees from the Eje Cafetero and the causal relationships between origin, environment, variety, processing, roasting, brewing, and flavor. No frontend, accounts, or visualization work happens in this phase — the API is the complete deliverable.

This phase is also being used deliberately as a **DataOps skill-building project**: beyond writing the ETL, it includes orchestration, data quality checks, CI/CD, and observability as first-class parts of the build, not later add-ons.

## Tech stack

### Source data

- **Format**: YAML, one file per coffee (e.g. `data/coffees/finca-el-mirador.yaml`), not CSV. The coffee → origin → environment → variety → processing → roasting → brewing → flavor chain is naturally nested and relational, not tabular — CSV would force it into flat rows or a sprawl of join files, and can't hold comments or multi-line notes the way curated research entries need. YAML keeps one coffee's full chain (including cause-effect notes) in one human-editable, human-reviewable file.
- Source files live in the repo (or a dedicated `data/` repo later) and are the version-controlled "input" the ETL step reads from.

### Orchestration

- **Dagster**, chosen over Airflow/Prefect specifically because its asset-centric model matches the data: each coffee's factor chain (origin, environment, variety, processing, roasting, brewing, flavor) is modeled as a **software-defined asset**, with the `causal_links` between them as asset dependencies. This gives lineage and freshness checks out of the box, rather than bolting them on.
- The ETL steps (parse YAML → validate → load to Postgres) become Dagster ops/assets instead of a single linear script, so each stage is independently observable, retryable, and testable.
- Local dev via `dagster dev` (webserver + daemon), same Docker Compose stack as the API/DB.

### Data quality

- **Pydantic v2** remains the schema/shape validator at parse time (required fields, types).
- **Dagster asset checks** add data-quality validation as a distinct, visible step in the pipeline (e.g., "every coffee has at least one causal link," "altitude is a plausible value for the stated region") — separate from shape validation, so quality rules are explicit and reportable rather than implicit in parsing code.

### Database

- **PostgreSQL 18** (18.6 as of writing; skip 16/17, which are now behind).
- The chain of factors is modeled as related tables (`coffees`, `origins`, `environments`, `varieties`, `processing_methods`, `roast_profiles`, `brew_methods`, `flavor_profiles`), linked by foreign keys.
- Cause-and-effect relationships between steps (e.g. "high altitude → slower cherry development") are stored as rows in a dedicated `causal_links` table (`from_factor`, `to_factor`, `explanation`), not as free-text description fields — so they're queryable and can be walked as a chain, not just displayed.

### API

- **Framework**: FastAPI (`0.141.x`).
- **Server**: Uvicorn (ASGI).
- **Schemas**: Pydantic v2 (`2.13.x`), reusing/adapting the same models used in the ETL validation step where possible.
- **Endpoints (initial)**: list/get coffees, get a coffee's full factor chain, get the causal links for a coffee (or between two factors).
- Auto-generated OpenAPI docs via FastAPI's built-in `/docs`.

### CI/CD

- **GitHub Actions**: on every push/PR, run linting, `pytest`, and a Dagster asset materialization against a throwaway Postgres service container — so a change to source YAML or pipeline code is validated before merge, not just at manual run time.
- Later: a scheduled workflow (or Dagster's own scheduler) to re-run the pipeline when source data changes.

### Observability

- Structured logging from Dagster runs (built-in run/event logs, per-asset).
- Track basic pipeline metadata: last successful load per coffee, row counts, validation failures — surfaced via Dagster's UI rather than a custom dashboard for now.

### Tooling

- **Language/runtime**: Python 3.13.
- **Dependency management**: `uv`, with a lockfile.
- **Testing**: `pytest` (`9.x`), for ETL/asset validation logic and API endpoints.
- **Parsing**: PyYAML (`6.0.x`).
- **ORM / migrations**: SQLAlchemy 2.0 (`2.0.52`; hold off on 2.1 until GA) + Alembic (`1.19.x`).
- **Local dev**: Docker Compose running Postgres + the API service + Dagster webserver/daemon.

## Why this stack

Python end-to-end keeps ETL, orchestration, and API in one language, so the Pydantic models that validate incoming YAML can be reused (or closely mirrored) in the API's response schemas — one source of truth for what a "coffee" looks like. YAML over CSV because the data is inherently a nested chain with narrative cause-effect notes, not flat tabular rows.

Dagster over Airflow/Prefect because the asset-centric model is the closest match to what this data actually is — a chain of related "things" (origin, environment, variety...) rather than a sequence of opaque tasks — and it bakes in lineage, freshness, and data-quality checks as concepts rather than conventions you'd otherwise have to invent. The tradeoff, consciously accepted: Dagster has a smaller install base than Airflow, so it's less directly transferable if a target job specifically wants Airflow experience — but the asset/lineage/quality-check concepts it teaches carry over to any orchestrator.

Postgres with explicit foreign-key relationships (including a dedicated `causal_links` table) is sufficient as long as the chain stays linear/tree-like; if relationship modeling later needs to become more general (many-to-many, weighted, conditional traversal for something like the future Interactive Lab), a graph database is the fallback option to revisit.
