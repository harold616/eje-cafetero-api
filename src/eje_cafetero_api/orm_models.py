"""SQLAlchemy 2.0 declarative models for the coffee factor chain.

These are the Postgres table definitions for the schema documented in
`_docs/schema.md`: `coffees` plus one table per factor in the chain
(`origins`, `environments`, `varieties`, `processing_methods`,
`roast_profiles`, `brew_methods`, `flavor_profiles`), and `causal_links` for
the cause-and-effect relationships between factors.

Every column mirrors `_docs/schema.md` field-for-field: same name, same
required/optional status (reflected as NOT NULL / nullable), and the closest
matching Postgres column type. Fixed-set fields (e.g. `department`,
`shade_type`) are stored as `String` rather than a DB-level enum/CHECK
constraint — shape/value validation is Pydantic's job (`models.py`, #4);
this layer only defines the storage shape (see the issue's "out of scope"
list — no read/write application code here).

Each factor table has a `coffee_id` foreign key back to `coffees.id`, marked
`unique=True` to enforce the one-coffee-to-one-of-each-factor relationship
described in architecture.md. `causal_links` also foreign-keys back to
`coffees.id`, but without a uniqueness constraint, since a coffee can have
many causal links.
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for every table in this module."""


class Coffee(Base):
    """A single coffee entry — the root of the factor chain."""

    __tablename__ = "coffees"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    origin: Mapped[Origin] = relationship(back_populates="coffee", uselist=False)
    environment: Mapped[Environment] = relationship(
        back_populates="coffee", uselist=False
    )
    variety: Mapped[Variety] = relationship(back_populates="coffee", uselist=False)
    processing_method: Mapped[ProcessingMethod] = relationship(
        back_populates="coffee", uselist=False
    )
    roast_profile: Mapped[RoastProfile] = relationship(
        back_populates="coffee", uselist=False
    )
    brew_method: Mapped[BrewMethod] = relationship(
        back_populates="coffee", uselist=False
    )
    flavor_profile: Mapped[FlavorProfile] = relationship(
        back_populates="coffee", uselist=False
    )
    causal_links: Mapped[list[CausalLink]] = relationship(back_populates="coffee")


class Origin(Base):
    """Where the coffee was grown. One row per coffee."""

    __tablename__ = "origins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    department: Mapped[str] = mapped_column(String, nullable=False)
    municipality: Mapped[str] = mapped_column(String, nullable=False)
    farm_name: Mapped[str] = mapped_column(String, nullable=False)
    producer: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="origin")


class Environment(Base):
    """Growing-environment conditions. One row per coffee."""

    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    altitude_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    shade_type: Mapped[str] = mapped_column(String, nullable=False)
    avg_temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_rainfall_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="environment")


class Variety(Base):
    """Botanical variety/cultivar of the coffee plant. One row per coffee."""

    __tablename__ = "varieties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    species: Mapped[str] = mapped_column(String, nullable=False)
    cultivar: Mapped[str] = mapped_column(String, nullable=False)
    rootstock: Mapped[str] = mapped_column(String, nullable=False)

    coffee: Mapped[Coffee] = relationship(back_populates="variety")


class ProcessingMethod(Base):
    """Post-harvest processing method. One row per coffee."""

    __tablename__ = "processing_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    method: Mapped[str] = mapped_column(String, nullable=False)
    fermentation_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    drying_method: Mapped[str | None] = mapped_column(String, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="processing_method")


class RoastProfile(Base):
    """Roast profile applied to the green beans. One row per coffee."""

    __tablename__ = "roast_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    roast_level: Mapped[str] = mapped_column(String, nullable=False)
    development_time_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    roaster_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="roast_profile")


class BrewMethod(Base):
    """Recommended brewing parameters. One row per coffee."""

    __tablename__ = "brew_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    recommended_methods: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    water_temperature_celsius: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    grind_size: Mapped[str | None] = mapped_column(String, nullable=True)
    ratio: Mapped[str | None] = mapped_column(String, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="brew_method")


class FlavorProfile(Base):
    """Sensory/tasting profile of the brewed coffee. One row per coffee."""

    __tablename__ = "flavor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(
        ForeignKey("coffees.id"), nullable=False, unique=True
    )
    tasting_notes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    acidity: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    sweetness: Mapped[str] = mapped_column(String, nullable=False)
    aftertaste: Mapped[str | None] = mapped_column(Text, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="flavor_profile")


class CausalLink(Base):
    """One cause-and-effect relationship between two factor sections.

    Unlike the factor tables above, a coffee can have many causal links, so
    `coffee_id` is a plain (non-unique) foreign key.
    """

    __tablename__ = "causal_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coffee_id: Mapped[str] = mapped_column(ForeignKey("coffees.id"), nullable=False)
    from_factor: Mapped[str] = mapped_column(String, nullable=False)
    to_factor: Mapped[str] = mapped_column(String, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    coffee: Mapped[Coffee] = relationship(back_populates="causal_links")
