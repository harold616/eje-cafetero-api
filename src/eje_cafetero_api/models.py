"""Pydantic v2 models for the coffee entry schema.

These models are the runtime validation layer for the YAML schema documented
in `_docs/schema.md`. Every field here mirrors that doc field-for-field:
same name, same required/optional status, same type, and `Literal` for every
field the doc restricts to a fixed set of values.

Reading a YAML file off disk and calling `Coffee.model_validate(...)` on it
is out of scope here (see issue #6) — this module only defines the shapes
and their validation rules.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Department = Literal["Caldas", "Quindío", "Risaralda", "Tolima", "Valle del Cauca"]
ShadeType = Literal["full_sun", "partial_shade", "full_shade"]
Species = Literal["arabica", "robusta"]
ProcessingMethod = Literal["washed", "natural", "honey", "anaerobic"]
DryingMethod = Literal["sun_dried", "mechanical_dryer", "raised_beds"]
RoastLevel = Literal["light", "medium", "medium-dark", "dark"]
BrewMethod = Literal[
    "espresso", "pour_over", "french_press", "aeropress", "cold_brew", "moka_pot"
]
GrindSize = Literal["fine", "medium-fine", "medium", "medium-coarse", "coarse"]
AcidityLevel = Literal["low", "medium", "high"]
BodyLevel = Literal["light", "medium", "full"]
SweetnessLevel = Literal["low", "medium", "high"]

# The seven factor-section names a CausalLink may point from/to. Deliberately
# excludes "causal_links" itself, per _docs/schema.md's "Causal links" section.
FactorName = Literal[
    "origin", "environment", "variety", "processing", "roasting", "brewing", "flavor"
]


class Origin(BaseModel):
    """Where the coffee was grown."""

    model_config = ConfigDict(extra="forbid")

    department: Department
    municipality: str
    farm_name: str
    producer: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Environment(BaseModel):
    """Growing-environment conditions."""

    model_config = ConfigDict(extra="forbid")

    altitude_meters: int
    shade_type: ShadeType
    avg_temperature_celsius: float | None = None
    annual_rainfall_mm: int | None = None


class Variety(BaseModel):
    """Botanical variety/cultivar of the coffee plant."""

    model_config = ConfigDict(extra="forbid")

    species: Species
    cultivar: str
    rootstock: str


class Processing(BaseModel):
    """Post-harvest processing method."""

    model_config = ConfigDict(extra="forbid")

    method: ProcessingMethod
    fermentation_hours: float | None = None
    drying_method: DryingMethod | None = None


class Roasting(BaseModel):
    """Roast profile applied to the green beans."""

    model_config = ConfigDict(extra="forbid")

    roast_level: RoastLevel
    development_time_percent: float | None = None
    roaster_notes: str | None = None


class Brewing(BaseModel):
    """Recommended brewing parameters."""

    model_config = ConfigDict(extra="forbid")

    recommended_methods: list[BrewMethod] = Field(min_length=1)
    water_temperature_celsius: float | None = None
    grind_size: GrindSize | None = None
    ratio: str | None = None


class Flavor(BaseModel):
    """Sensory/tasting profile of the brewed coffee."""

    model_config = ConfigDict(extra="forbid")

    tasting_notes: list[str] = Field(min_length=1)
    acidity: AcidityLevel
    body: BodyLevel
    sweetness: SweetnessLevel
    aftertaste: str | None = None


class CausalLink(BaseModel):
    """One cause-and-effect relationship between two factor sections."""

    model_config = ConfigDict(extra="forbid")

    from_factor: FactorName
    to_factor: FactorName
    explanation: str


class Coffee(BaseModel):
    """A single coffee entry: the full origin-to-flavor factor chain."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    summary: str
    origin: Origin
    environment: Environment
    variety: Variety
    processing: Processing
    roasting: Roasting
    brewing: Brewing
    flavor: Flavor
    causal_links: list[CausalLink]
