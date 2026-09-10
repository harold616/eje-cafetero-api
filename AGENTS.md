Commands

- `uv sync` - install dependencies
- `uv run pytest` - the whole suite
- `uv run pytest tests/test_smoke.py` - one test file

Documents

- `_docs/process.md` - how work is organized

Roles

- PM - grooms a task before anyone implements it, follows _docs/team/pm.md

Rules

- Dependencies are added in `pyproject.toml`. Do not add one without
  asking
