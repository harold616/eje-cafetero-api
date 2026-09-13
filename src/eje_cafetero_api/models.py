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
    """Where the coffee was grown.

    `from_attributes=True` (alongside YAML-dict validation via `extra`)
    lets this same class also validate directly off an `orm_models.Origin`
    row — see `CoffeeChain` (#12), which reuses it that way.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    department: Department
    municipality: str
    farm_name: str
    producer: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Environment(BaseModel):
    """Growing-environment conditions.

    `from_attributes=True` — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    altitude_meters: int
    shade_type: ShadeType
    avg_temperature_celsius: float | None = None
    annual_rainfall_mm: int | None = None


class Variety(BaseModel):
    """Botanical variety/cultivar of the coffee plant.

    `from_attributes=True` — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    species: Species
    cultivar: str
    rootstock: str


class Processing(BaseModel):
    """Post-harvest processing method.

    `from_attributes=True` lets this validate directly off an
    `orm_models.ProcessingMethod` row — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    method: ProcessingMethod
    fermentation_hours: float | None = None
    drying_method: DryingMethod | None = None


class Roasting(BaseModel):
    """Roast profile applied to the green beans.

    `from_attributes=True` lets this validate directly off an
    `orm_models.RoastProfile` row — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    roast_level: RoastLevel
    development_time_percent: float | None = None
    roaster_notes: str | None = None


class Brewing(BaseModel):
    """Recommended brewing parameters.

    `from_attributes=True` lets this validate directly off an
    `orm_models.BrewMethod` row — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    recommended_methods: list[BrewMethod] = Field(min_length=1)
    water_temperature_celsius: float | None = None
    grind_size: GrindSize | None = None
    ratio: str | None = None


class Flavor(BaseModel):
    """Sensory/tasting profile of the brewed coffee.

    `from_attributes=True` lets this validate directly off an
    `orm_models.FlavorProfile` row — see `Origin`'s docstring above.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

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


class CoffeeSummary(BaseModel):
    """API response shape for `GET /coffees` and `GET /coffees/{id}` (#11).

    Adapted from `Coffee` above rather than redefined from scratch: `id`,
    `name`, and `summary` are exactly the fields `orm_models.Coffee` stores
    on the `coffees` table itself (see `_docs/schema.md`). The rest of
    `Coffee`'s fields — the full factor chain (`origin` through `flavor`)
    and `causal_links` — are intentionally left out of this response, not an
    oversight: assembling that chain is out of scope for #11 and tracked
    separately (#12 for `/coffees/{id}/chain`, #13 for causal links). There
    is no internal-only field to hide here — `orm_models.Coffee.id` is the
    schema's own kebab-case business key (see `load.py`), not a surrogate DB
    primary key, so it is exposed as-is.

    `from_attributes=True` lets this be built directly off an
    `orm_models.Coffee` row via `CoffeeSummary.model_validate(row)`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    summary: str


class CoffeeChain(BaseModel):
    """API response shape for `GET /coffees/{id}/chain` (#12).

    Adapted from `Coffee` above, minus `causal_links`: that section is out
    of scope for this endpoint and tracked separately in #13. The seven
    nested sections reuse the exact same `Origin`/`Environment`/`Variety`/
    `Processing`/`Roasting`/`Brewing`/`Flavor` classes `Coffee` uses for
    YAML validation — each of those now also sets `from_attributes=True` so
    they can validate directly off an `orm_models` row instead of a dict,
    with no ORM-only duplicate schema needed.

    `from_attributes=True` on this class itself lets `id`/`name`/`summary`
    be read straight off the root `orm_models.Coffee` row. The seven
    sections are *not* filled in by a single top-level
    `CoffeeChain.model_validate(row)`, though: `orm_models.Coffee`'s
    relationship attribute names (`processing_method`, `roast_profile`,
    `brew_method`, `flavor_profile`) don't match this schema's field names
    (`processing`, `roasting`, `brewing`, `flavor`), so `app.py` validates
    each section individually off its corresponding relationship and passes
    the results in by keyword.
    """

    model_config = ConfigDict(from_attributes=True)

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
