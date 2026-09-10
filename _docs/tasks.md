# Backlog — Phase 1 (Data + API)

Tasks for the current build phase, described in [`plan.md`](./plan.md) and [`architecture.md`](./architecture.md). Each task is scoped to be finishable in one session and independently understandable — pick one up without needing to have read the others.

## 1. Project scaffolding with a passing test
Goal: Get an empty, runnable Python project in place.
Description: Initialize a Python 3.13 project managed with `uv`, including a `pyproject.toml` and lockfile. Set up `pytest` and add a single trivial test that passes, so CI/local test running is proven to work before any real code exists.

## 2. Local dev environment via Docker Compose
Goal: Make Postgres runnable locally with one command.
Description: Add a `docker-compose.yml` that runs PostgreSQL 18 locally, with connection settings (host, port, credentials, db name) exposed via environment variables in a `.env.example` file. Document in the README how to start/stop it and confirm connectivity (e.g. `psql` or a one-line connection check).

## 3. Define and document the YAML source schema for a coffee entry
Goal: Specify the shape of a single coffee's source data file.
Description: Write a schema reference document (and one fully-filled example YAML file) describing the fields for a coffee entry: origin, environment, variety, processing, roasting, brewing, flavor, and a list of causal links between factors (e.g. "high altitude → slower cherry development"). This is a data-modeling task, not code — it's the contract that validation and the database schema will both be built against.

## 4. Pydantic validation models for the coffee schema
Goal: Turn the YAML schema into enforced, typed Python models.
Description: Write Pydantic v2 models (`Coffee`, `Origin`, `Environment`, `Variety`, `Processing`, `Roasting`, `Brewing`, `Flavor`, `CausalLink`) matching the schema from task 3. Include tests that confirm a valid example file parses correctly and that missing/malformed fields raise validation errors.

## 5. Database schema: SQLAlchemy models + Alembic migration
Goal: Create the Postgres tables that will store coffee data.
Description: Define SQLAlchemy 2.0 models for `coffees`, `origins`, `environments`, `varieties`, `processing_methods`, `roast_profiles`, `brew_methods`, `flavor_profiles`, and `causal_links`, linked by foreign keys per the relationships described in `architecture.md`. Generate and check in the initial Alembic migration, and confirm it applies cleanly to a fresh database.

## 6. ETL parse-and-validate step
Goal: Turn a YAML source file into a validated in-memory object.
Description: Write a function that reads one coffee's YAML file, parses it with PyYAML, and validates it against the Pydantic models. It should fail loudly (raise, not silently skip) on a malformed or incomplete entry. Cover it with tests using both a valid and an intentionally broken example file.

## 7. ETL load step: validated data into Postgres
Goal: Persist a validated coffee record into the database.
Description: Write an idempotent load function that takes a validated coffee object and upserts it (and its related rows, including causal links) into Postgres via SQLAlchemy. Running it twice on the same input should leave the database in the same state, not create duplicates. Test against a throwaway/test database.

## 8. Wrap the ETL pipeline as Dagster assets
Goal: Turn the parse/validate/load steps into an observable, asset-based pipeline.
Description: Convert the functions from tasks 6 and 7 into Dagster software-defined assets, modeling each factor (origin, environment, variety, etc.) and the coffee itself as assets with dependencies matching the factor chain. Confirm the pipeline materializes successfully via `dagster dev` against a local source file.

## 9. Add Dagster asset checks for data quality
Goal: Make data-quality rules explicit and visible in the pipeline, not just implicit in parsing.
Description: Add Dagster asset checks that validate things Pydantic's shape-checking doesn't cover — e.g., every coffee has at least one causal link, altitude values are plausible for the stated region. Checks should show up as pass/fail in the Dagster UI when the pipeline runs.

## 10. FastAPI app skeleton with a health-check endpoint
Goal: Get a running API service with one working endpoint.
Description: Set up a FastAPI app with Uvicorn, a database connection (reusing the SQLAlchemy models from task 5), and a `GET /health` endpoint that confirms the app can reach Postgres. Include a test that hits the endpoint and asserts a 200 response.

## 11. API endpoint: list and get coffees
Goal: Expose the curated coffee collection over the API.
Description: Add `GET /coffees` (list) and `GET /coffees/{id}` (single record) endpoints, returning data shaped by Pydantic response schemas. Include tests covering an existing id, a nonexistent id (404), and the list endpoint returning multiple entries.

## 12. API endpoint: a coffee's full factor chain
Goal: Expose one coffee's entire origin-to-flavor chain in a single response.
Description: Add `GET /coffees/{id}/chain`, returning the coffee's origin, environment, variety, processing, roasting, brewing, and flavor data assembled into one nested response. Test that the response includes all expected sections for a seeded example coffee.

## 13. API endpoint: causal links
Goal: Expose the cause-and-effect relationships between factors.
Description: Add `GET /coffees/{id}/causal-links`, returning the ordered list of causal links for that coffee (e.g. altitude → cherry development → processing choice). Include a test asserting the links come back in a sensible order and include their explanation text.

## 14. CI pipeline via GitHub Actions
Goal: Automatically validate every change before merge.
Description: Add a GitHub Actions workflow that runs linting and `pytest` on every push/PR, using a Postgres service container for any tests that need a database. Confirm it fails on a broken test and passes on the current main branch.

## 15. Curate the initial seed dataset
Goal: Populate the collection with real, research-backed coffee entries.
Description: Author 3–5 complete YAML coffee entries (per the schema from task 3) based on real Eje Cafetero coffees, including plausible cause-and-effect notes at each step of the chain. This is a content/research task — no code — that gives the pipeline and API real data to run against instead of placeholder examples.
