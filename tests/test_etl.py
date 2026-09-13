import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from eje_cafetero_api.etl import CoffeeYamlError, load_coffee
from eje_cafetero_api.models import Coffee

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_valid_file_loads_into_a_fully_populated_coffee():
    """#4's reference example parses cleanly into a fully-typed Coffee with
    no errors."""
    coffee = load_coffee(FIXTURES_DIR / "valid_coffee.yaml")

    assert isinstance(coffee, Coffee)
    assert coffee.id == "finca-el-ocaso-caturra-washed"
    assert coffee.origin.department == "Quindío"
    assert coffee.environment.altitude_meters == 1850
    assert coffee.roasting.roast_level == "medium"
    assert len(coffee.causal_links) == 6


def test_missing_required_field_raises_validation_error():
    """Dropping the required top-level `origin` field must raise
    pydantic.ValidationError, never return None or a partial object."""
    with pytest.raises(ValidationError, match="origin"):
        load_coffee(FIXTURES_DIR / "missing_top_level_field.yaml")


def test_malformed_field_raises_validation_error():
    """An out-of-set Literal value (roast_level) must raise
    pydantic.ValidationError."""
    with pytest.raises(ValidationError, match="roast_level"):
        load_coffee(FIXTURES_DIR / "invalid_enum_field.yaml")


def test_wrong_type_field_raises_validation_error():
    """A field of the wrong type (altitude_meters as a non-numeric string)
    must raise pydantic.ValidationError."""
    with pytest.raises(ValidationError, match="altitude_meters"):
        load_coffee(FIXTURES_DIR / "wrong_type_field.yaml")


def test_yaml_syntax_error_raises_error_naming_the_file():
    """A file that isn't valid YAML at all must raise an error whose
    message includes the file path - no bare, file-less traceback."""
    path = FIXTURES_DIR / "syntax_error.yaml"

    with pytest.raises(CoffeeYamlError, match=re.escape(str(path))):
        load_coffee(path)


def test_load_coffee_accepts_a_string_path():
    """`path` may be a plain string, not just a `Path`."""
    coffee = load_coffee(str(FIXTURES_DIR / "valid_coffee.yaml"))

    assert coffee.id == "finca-el-ocaso-caturra-washed"
