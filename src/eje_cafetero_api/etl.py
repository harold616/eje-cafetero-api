"""ETL parse-and-validate step.

Turns a single coffee YAML file path into a validated, fully-typed `Coffee`
object (see `eje_cafetero_api.models`), and fails loudly - never silently -
on anything malformed or incomplete.

Loading more than one file / scanning a directory of sources is out of
scope here; see issue #8, where per-file materialization gets orchestrated
as Dagster assets. Writing the validated object to Postgres is tracked in
issue #7.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from eje_cafetero_api.models import Coffee

__all__ = ["CoffeeYamlError", "load_coffee"]


class CoffeeYamlError(ValueError):
    """Raised when a coffee source file isn't valid YAML.

    Its message always includes the offending file's path, so a syntax
    error never surfaces as a bare, file-less traceback.
    """


def load_coffee(path: str | Path) -> Coffee:
    """Read one coffee YAML file and validate it into a `Coffee`.

    Args:
        path: path to a single coffee YAML file.

    Returns:
        A fully-populated `Coffee` object.

    Raises:
        CoffeeYamlError: the file isn't valid YAML (syntax error). The
            message includes `path`.
        pydantic.ValidationError: the parsed YAML doesn't satisfy the
            `Coffee` schema - a required field is missing, a field has the
            wrong type, or a `Literal`/enum field has an out-of-set value.
            Never returns `None` or a partially-populated object.
    """
    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise CoffeeYamlError(f"Invalid YAML in {path}: {exc}") from exc

    return Coffee.model_validate(raw)
