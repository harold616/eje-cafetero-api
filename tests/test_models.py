from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from eje_cafetero_api.models import Coffee

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_valid_example_file_parses_into_a_coffee():
    """#3's reference example (data/coffees/example.yaml, mirrored here as a
    fixture) parses cleanly into a Coffee, exercising every documented
    field, including the fermentation_hours int-to-float coercion."""
    data = _load("valid_coffee.yaml")

    coffee = Coffee.model_validate(data)

    assert coffee.id == "finca-el-ocaso-caturra-washed"
    assert coffee.origin.department == "Quindío"
    assert coffee.environment.altitude_meters == 1850
    assert coffee.variety.species == "arabica"
    assert coffee.processing.method == "washed"
    # fermentation_hours is documented as float; the example YAML has it as
    # a bare int literal (18) — Pydantic coerces it to 18.0.
    assert coffee.processing.fermentation_hours == 18.0
    assert isinstance(coffee.processing.fermentation_hours, float)
    assert coffee.roasting.roast_level == "medium"
    assert coffee.brewing.recommended_methods == ["pour_over", "aeropress"]
    assert coffee.flavor.acidity == "high"
    assert len(coffee.causal_links) == 6
    assert coffee.causal_links[0].from_factor == "origin"
    assert coffee.causal_links[0].to_factor == "environment"


def test_empty_causal_links_list_is_valid():
    """Not every coffee needs a documented causal link — causal_links: []
    must still be a valid Coffee."""
    data = _load("valid_coffee_no_causal_links.yaml")

    coffee = Coffee.model_validate(data)

    assert coffee.causal_links == []


def test_missing_required_top_level_field_raises_validation_error():
    """Dropping the required top-level `origin` field must raise."""
    data = _load("missing_top_level_field.yaml")

    with pytest.raises(ValidationError, match="origin"):
        Coffee.model_validate(data)


def test_missing_required_nested_field_raises_validation_error():
    """Dropping a required field on a nested model (environment.shade_type)
    must surface as a ValidationError, not get swallowed."""
    data = _load("missing_nested_field.yaml")

    with pytest.raises(ValidationError, match="shade_type"):
        Coffee.model_validate(data)


def test_invalid_enum_value_raises_validation_error():
    """An out-of-set value for a Literal-constrained field (roast_level)
    must raise."""
    data = _load("invalid_enum_field.yaml")

    with pytest.raises(ValidationError, match="roast_level"):
        Coffee.model_validate(data)


def test_wrong_type_field_raises_validation_error():
    """A field of the wrong type (altitude_meters as a non-numeric string)
    must raise."""
    data = _load("wrong_type_field.yaml")

    with pytest.raises(ValidationError, match="altitude_meters"):
        Coffee.model_validate(data)


def test_unexpected_field_is_rejected():
    """model_config = ConfigDict(extra='forbid') means a typo'd or
    unexpected field fails validation instead of being silently dropped."""
    data = _load("valid_coffee.yaml")
    data["unexpected_field"] = "should not be allowed"

    with pytest.raises(ValidationError, match="unexpected_field"):
        Coffee.model_validate(data)
