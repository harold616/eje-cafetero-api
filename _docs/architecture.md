# Architecture — Phase 1 (Data + API)

Companion to [`plan.md`](./plan.md). Covers the technical approach for the current build phase: an ETL pipeline and API that model coffees from the Eje Cafetero and the causal relationships between origin, environment, variety, processing, roasting, brewing, and flavor. No frontend, accounts, or visualization work happens in this phase — the API is the complete deliverable.

## Tech stack

### Source data

- **Format**: YAML, one file per coffee (e.g. `data/coffees/finca-el-mirador.yaml`), not CSV. The coffee → origin → environment → variety → processing → roasting → brewing → flavor chain is naturally nested and relational, not tabular — CSV would force it into flat rows or a sprawl of join files, and can't hold comments or multi-line notes the way curated research entries need. YAML keeps one coffee's full chain (including cause-effect notes) in one human-editable, human-reviewable file.
- Source files live in the repo (or a dedicated `data/` repo later) and are the version-controlled "input" the ETL step reads from.

### ETL

- **Language/runtime**: Python 3.13.
- **Parsing**: PyYAML to load each source file into a dict.
- **Validation**: Pydantic v2 models mirroring the source schema (`Coffee`, `Origin`, `Environment`, `Variety`, `Processing`, `Roasting`, `Brewing`, `Flavor`, plus a `CausalLink` model for the relationships between steps). Parsing fails loudly on malformed or incomplete entries rather than loading partial data.
- **Load**: SQLAlchemy 2.0 (ORM + Core) to upsert validated records into Postgres, run as an idempotent script (`etl/load.py`) so re-running it after editing a source file is safe.
- **Schema migrations**: Alembic, versioned alongside the SQLAlchemy models.

### Database

- **Postgres 16.**
- The chain of factors is modeled as related tables (`coffees`, `origins`, `environments`, `varieties`, `processing_methods`, `roast_profiles`, `brew_methods`, `flavor_profiles`), linked by foreign keys.
- Cause-and-effect relationships between steps (e.g. "high altitude → slower cherry development") are stored as rows in a dedicated `causal_links` table (`from_factor`, `to_factor`, `explanation`), not as free-text description fields — so they're queryable and can be walked as a chain, not just displayed.

### API

- **Framework**: FastAPI.
- **Server**: Uvicorn (ASGI).
- **Schemas**: Pydantic v2, reusing/adapting the same models used in the ETL validation step where possible.
- **Endpoints (initial)**: list/get coffees, get a coffee's full factor chain, get the causal links for a coffee (or between two factors).
- Auto-generated OpenAPI docs via FastAPI's built-in `/docs`.

### Tooling

- **Dependency management**: `uv` (or Poetry) with a lockfile.
- **Testing**: pytest, for both ETL validation logic and API endpoints.
- **Local dev**: Docker Compose running Postgres + the API service.

## Why this stack

Python end-to-end keeps ETL and API in one language, so the Pydantic models that validate incoming YAML can be reused (or closely mirrored) in the API's response schemas — one source of truth for what a "coffee" looks like. YAML over CSV because the data is inherently a nested chain with narrative cause-effect notes, not flat tabular rows. Postgres with explicit foreign-key relationships (including a dedicated `causal_links` table) is sufficient as long as the chain stays linear/tree-like; if relationship modeling later needs to become more general (many-to-many, weighted, conditional traversal for something like the future Interactive Lab), a graph database is the fallback option to revisit.
