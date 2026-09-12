# Coffee entry — YAML source schema

This is the contract for one coffee source file under `data/coffees/` (one YAML
file per coffee, per `architecture.md`). It defines every field a coffee entry
has: name, type, required/optional status, and — for any field restricted to a
fixed set of values — the exact allowed values.

This doc is the source of truth for #4 (Pydantic models), #5 (SQLAlchemy
tables), #6 (the loader), and #15 (seed data). If a field isn't listed here, it
isn't part of the schema.

A fully-filled reference example lives at
[`data/coffees/example.yaml`](../data/coffees/example.yaml). Every field
documented here appears in that file with a real value — nothing documented is
missing from the example, and nothing in the example is undocumented.

## Conventions used below

- **Required** means the key must be present in the YAML file. A required
  field is never left implicit — if a field isn't marked required below, it is
  optional and may be omitted from a coffee entry.
- **Fixed set** means the value must be exactly one of the listed strings
  (case-sensitive, lowercase, `snake_case` where the value is multi-word).
  These are the fields #4 must implement with `Literal`/`Enum` rather than a
  free `str`.
- Section names (`origin`, `environment`, `variety`, `processing`, `roasting`,
  `brewing`, `flavor`, `causal_links`) match `architecture.md` and are not
  renamed here.

## Top-level coffee entry

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string | required | Unique kebab-case identifier for the coffee (e.g. `finca-el-ocaso-caturra-washed`); by convention matches the YAML filename stem |
| `name` | string | required | Human-readable display name of the coffee |
| `summary` | string | required | One-paragraph overview of what makes this coffee distinct |
| `origin` | `Origin` object | required | Where the coffee was grown — see [Origin](#origin) |
| `environment` | `Environment` object | required | Growing-environment conditions — see [Environment](#environment) |
| `variety` | `Variety` object | required | Botanical variety/cultivar of the coffee plant — see [Variety](#variety) |
| `processing` | `Processing` object | required | Post-harvest processing method — see [Processing](#processing) |
| `roasting` | `Roasting` object | required | Roast profile applied to the green beans — see [Roasting](#roasting) |
| `brewing` | `Brewing` object | required | Recommended brewing parameters — see [Brewing](#brewing) |
| `flavor` | `Flavor` object | required | Sensory/tasting profile of the brewed coffee — see [Flavor](#flavor) |
| `causal_links` | list of `CausalLink` objects | required | Cause-and-effect relationships connecting the factors above — see [Causal links](#causal-links). The key must always be present, but the list **may be empty** (`causal_links: []`) — not every coffee entry is required to document a causal link. |

## Origin

| Field | Type | Required | Meaning |
|---|---|---|---|
| `department` | string, fixed set | required | Colombian department where the farm is located. Allowed values: `Caldas`, `Quindío`, `Risaralda`, `Tolima`, `Valle del Cauca` |
| `municipality` | string | required | Municipality/town nearest the farm |
| `farm_name` | string | required | Name of the specific farm (finca) |
| `producer` | string | optional | Name of the grower, producing family, or cooperative, when known |
| `latitude` | float | optional | Farm latitude in decimal degrees (WGS84) |
| `longitude` | float | optional | Farm longitude in decimal degrees (WGS84) |

## Environment

| Field | Type | Required | Meaning |
|---|---|---|---|
| `altitude_meters` | integer | required | Farm elevation in meters above sea level (masl) |
| `shade_type` | string, fixed set | required | Canopy/shade management under which the coffee is grown. Allowed values: `full_sun`, `partial_shade`, `full_shade` |
| `avg_temperature_celsius` | float | optional | Average ambient growing temperature, in Celsius |
| `annual_rainfall_mm` | integer | optional | Average annual rainfall, in millimeters |

## Variety

| Field | Type | Required | Meaning |
|---|---|---|---|
| `species` | string, fixed set | required | Coffee species. Allowed values: `arabica`, `robusta` |
| `cultivar` | string | required | Specific cultivar name (e.g. Caturra, Castillo, Bourbon, Typica, Geisha). Free text, not a fixed set — new cultivars are registered regularly and an exhaustive enum would go stale |
| `rootstock` | string | required | Rootstock the plant is grown on, e.g. a named grafting rootstock, or `own-rooted` if the plant is not grafted |

## Processing

| Field | Type | Required | Meaning |
|---|---|---|---|
| `method` | string, fixed set | required | Post-harvest processing method applied to the cherries. Allowed values: `washed`, `natural`, `honey`, `anaerobic` |
| `fermentation_hours` | float | optional | Hours the coffee was fermented (during washing or as part of the method) |
| `drying_method` | string, fixed set | optional | How the parchment/coffee was dried. Allowed values: `sun_dried`, `mechanical_dryer`, `raised_beds` |

## Roasting

| Field | Type | Required | Meaning |
|---|---|---|---|
| `roast_level` | string, fixed set | required | Overall roast degree. Allowed values: `light`, `medium`, `medium-dark`, `dark` |
| `development_time_percent` | float | optional | Percent of total roast time spent after first crack |
| `roaster_notes` | string | optional | Free-text notes about the roast profile/curve |

## Brewing

| Field | Type | Required | Meaning |
|---|---|---|---|
| `recommended_methods` | list of string, fixed set | required (at least one entry) | Brew methods recommended for this coffee. Allowed values per entry: `espresso`, `pour_over`, `french_press`, `aeropress`, `cold_brew`, `moka_pot` |
| `water_temperature_celsius` | float | optional | Recommended brew water temperature, in Celsius |
| `grind_size` | string, fixed set | optional | Recommended grind size. Allowed values: `fine`, `medium-fine`, `medium`, `medium-coarse`, `coarse` |
| `ratio` | string | optional | Recommended coffee-to-water ratio, e.g. `"1:16"` |

## Flavor

| Field | Type | Required | Meaning |
|---|---|---|---|
| `tasting_notes` | list of string | required (at least one entry) | Descriptive flavor/aroma notes, free text per entry (e.g. `jasmine`, `red apple`) |
| `acidity` | string, fixed set | required | Perceived acidity level. Allowed values: `low`, `medium`, `high` |
| `body` | string, fixed set | required | Perceived mouthfeel/body. Allowed values: `light`, `medium`, `full` |
| `sweetness` | string, fixed set | required | Perceived sweetness level. Allowed values: `low`, `medium`, `high` |
| `aftertaste` | string | optional | Free-text description of the finish/aftertaste |

## Causal links

`causal_links` is a list of entries (see [Top-level coffee entry](#top-level-coffee-entry)
for its required/optional status and empty-list rule). Each entry is a
`CausalLink` object:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `from_factor` | string, fixed set | required | The upstream factor section this link originates from |
| `to_factor` | string, fixed set | required | The downstream factor section this link leads to |
| `explanation` | string | required | Free-text explanation of the cause-and-effect mechanism (e.g. "high altitude slows cherry development, concentrating sugars") |

`from_factor` and `to_factor` must each be one of the seven **factor section
names** — the top-level sections that represent a stage in the chain,
excluding `causal_links` itself (since `causal_links` is the list of
relationships *between* factors, not a factor):

`origin`, `environment`, `variety`, `processing`, `roasting`, `brewing`, `flavor`

These are not free text. A value outside this set (including `causal_links`)
is invalid. This schema does not require `from_factor`/`to_factor` to follow
chain order (e.g. a link could go `roasting` → `brewing` or, unusually,
`flavor` → `processing` as a documented observation) — enforcing a specific
ordering or "plausibility" of a link is a data-quality rule, out of scope here
per #9.
