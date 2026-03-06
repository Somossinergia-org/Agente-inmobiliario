"""Modelos de propiedades inmobiliarias."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class PropertyType(Enum):
    APARTMENT = "piso"
    HOUSE = "casa"
    VILLA = "chalet"
    DUPLEX = "dúplex"
    PENTHOUSE = "ático"
    STUDIO = "estudio"
    COMMERCIAL_OFFICE = "oficina"
    COMMERCIAL_RETAIL = "local_comercial"
    COMMERCIAL_WAREHOUSE = "nave_industrial"
    LAND_URBAN = "terreno_urbano"
    LAND_RUSTIC = "terreno_rústico"
    RURAL_ESTATE = "finca_rústica"
    RURAL_COUNTRY_HOUSE = "casa_rural"
    GARAGE = "garaje"
    STORAGE = "trastero"


class PropertyStatus(Enum):
    AVAILABLE = "disponible"
    RESERVED = "reservado"
    SOLD = "vendido"
    RENTED = "alquilado"


@dataclass
class Property:
    id: str
    title: str
    property_type: PropertyType
    status: PropertyStatus
    price: float
    location: str
    city: str
    province: str
    area_m2: float
    description: str
    features: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    year_built: Optional[int] = None
    last_renovation: Optional[int] = None
    energy_rating: Optional[str] = None
    date_listed: date = field(default_factory=date.today)
    is_rental: bool = False
    monthly_rent: Optional[float] = None

    @property
    def price_per_m2(self) -> float:
        if self.area_m2 > 0:
            return self.price / self.area_m2
        return 0.0

    def matches_budget(self, min_price: float = 0, max_price: float = float("inf")) -> bool:
        return min_price <= self.price <= max_price

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.property_type.value,
            "status": self.status.value,
            "price": self.price,
            "location": self.location,
            "city": self.city,
            "province": self.province,
            "area_m2": self.area_m2,
            "price_per_m2": round(self.price_per_m2, 2),
            "description": self.description,
            "features": self.features,
            "energy_rating": self.energy_rating,
            "is_rental": self.is_rental,
        }


@dataclass
class ResidentialProperty(Property):
    bedrooms: int = 0
    bathrooms: int = 0
    floor: Optional[int] = None
    has_elevator: bool = False
    has_terrace: bool = False
    has_balcony: bool = False
    has_garage: bool = False
    has_pool: bool = False
    has_garden: bool = False
    orientation: Optional[str] = None
    community_fees: Optional[float] = None


@dataclass
class CommercialProperty(Property):
    commercial_type: str = ""
    floor_load_capacity: Optional[float] = None
    ceiling_height: Optional[float] = None
    has_loading_dock: bool = False
    has_office_space: bool = False
    parking_spots: int = 0
    is_corner: bool = False
    facade_length: Optional[float] = None


@dataclass
class LandProperty(Property):
    buildable_area_m2: Optional[float] = None
    land_classification: str = ""
    has_utilities: bool = False
    has_road_access: bool = True
    max_building_height: Optional[float] = None
    allowed_uses: list[str] = field(default_factory=list)
    topography: str = "llano"


@dataclass
class RuralProperty(Property):
    land_area_m2: float = 0
    has_water_well: bool = False
    has_electricity: bool = False
    crop_type: Optional[str] = None
    has_farmhouse: bool = False
    animal_facilities: bool = False
    irrigation_type: Optional[str] = None


@dataclass
class GarageProperty(Property):
    vehicle_type: str = "coche"
    is_covered: bool = True
    has_automatic_door: bool = False
    floor_level: int = 0
    has_security: bool = False
    has_ev_charger: bool = False
