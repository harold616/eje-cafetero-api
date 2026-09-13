"""Database connection configuration.

Builds the Postgres connection URL from the same environment variables the
Docker Compose stack uses (see `.env.example` / `docker-compose.yml`):
`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`.

Docker Compose auto-loads a `.env` file in the repo root; this module isn't
run by Compose, so it loads the same file itself with a tiny hand-rolled
parser (no `python-dotenv` dependency added just for this — `.env` is a
plain `KEY=VALUE` file). Values already present in the process environment
take precedence over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_POSTGRES_USER = "eje_cafetero"
DEFAULT_POSTGRES_PASSWORD = "changeme"
DEFAULT_POSTGRES_DB = "eje_cafetero"
DEFAULT_POSTGRES_PORT = "5432"
DEFAULT_POSTGRES_HOST = "localhost"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(REPO_ROOT / ".env")


def get_database_url() -> str:
    """Build the SQLAlchemy connection URL for the local Postgres instance."""
    user = os.environ.get("POSTGRES_USER", DEFAULT_POSTGRES_USER)
    password = os.environ.get("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)
    db = os.environ.get("POSTGRES_DB", DEFAULT_POSTGRES_DB)
    port = os.environ.get("POSTGRES_PORT", DEFAULT_POSTGRES_PORT)
    host = os.environ.get("POSTGRES_HOST", DEFAULT_POSTGRES_HOST)
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
