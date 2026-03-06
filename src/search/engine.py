"""Motor de búsqueda avanzada de propiedades."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.data.database import Database
from src.models.property import Property, PropertyType, PropertyStatus, ResidentialProperty


@dataclass
class SearchFilters:
    """Filtros de búsqueda de propiedades."""
    property_types: list[str] = field(default_factory=list)
    min_price: float = 0
    max_price: float = float("inf")
    min_area: float = 0
    max_area: float = float("inf")
    cities: list[str] = field(default_factory=list)
    provinces: list[str] = field(default_factory=list)
    min_bedrooms: int = 0
    max_bedrooms: int = 100
    min_bathrooms: int = 0
    has_garage: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_elevator: Optional[bool] = None
    is_rental: Optional[bool] = None
    status: Optional[str] = None
    keyword: str = ""
    energy_ratings: list[str] = field(default_factory=list)
    sort_by: str = "price"  # price, area, price_per_m2, date
    sort_ascending: bool = True


class SearchEngine:
    """Motor de búsqueda con filtros avanzados y ordenación."""

    def __init__(self, db: Database):
        self.db = db

    def search(self, filters: SearchFilters) -> list[Property]:
        results = list(self.db.properties.values())

        # Filtro por estado
        if filters.status:
            results = [p for p in results if p.status.value == filters.status]
        else:
            results = [p for p in results if p.status == PropertyStatus.AVAILABLE]

        # Filtro alquiler/venta
        if filters.is_rental is not None:
            results = [p for p in results if p.is_rental == filters.is_rental]

        # Filtro por tipo
        if filters.property_types:
            type_values = [t.lower() for t in filters.property_types]
            results = [p for p in results if p.property_type.value in type_values]

        # Filtro por precio
        results = [p for p in results if p.matches_budget(filters.min_price, filters.max_price)]

        # Filtro por área
        results = [p for p in results if filters.min_area <= p.area_m2 <= filters.max_area]

        # Filtro por ciudad
        if filters.cities:
            city_lower = [c.lower() for c in filters.cities]
            results = [p for p in results if p.city.lower() in city_lower]

        # Filtro por provincia
        if filters.provinces:
            prov_lower = [pr.lower() for pr in filters.provinces]
            results = [p for p in results if p.province.lower() in prov_lower]

        # Filtros residenciales
        if filters.min_bedrooms > 0 or filters.max_bedrooms < 100:
            results = [
                p for p in results
                if not hasattr(p, "bedrooms")
                or filters.min_bedrooms <= getattr(p, "bedrooms", 0) <= filters.max_bedrooms
            ]

        if filters.min_bathrooms > 0:
            results = [
                p for p in results
                if not hasattr(p, "bathrooms") or getattr(p, "bathrooms", 0) >= filters.min_bathrooms
            ]

        # Filtros booleanos
        for attr, filt_val in [
            ("has_garage", filters.has_garage),
            ("has_pool", filters.has_pool),
            ("has_garden", filters.has_garden),
            ("has_terrace", filters.has_terrace),
            ("has_elevator", filters.has_elevator),
        ]:
            if filt_val is not None:
                results = [
                    p for p in results
                    if getattr(p, attr, False) == filt_val
                ]

        # Filtro por certificación energética
        if filters.energy_ratings:
            ratings = [r.upper() for r in filters.energy_ratings]
            results = [p for p in results if p.energy_rating and p.energy_rating.upper() in ratings]

        # Búsqueda por palabra clave
        if filters.keyword:
            kw = filters.keyword.lower()
            results = [
                p for p in results
                if kw in p.title.lower()
                or kw in p.description.lower()
                or kw in p.location.lower()
                or any(kw in f.lower() for f in p.features)
            ]

        # Ordenación
        sort_key = self._get_sort_key(filters.sort_by)
        results.sort(key=sort_key, reverse=not filters.sort_ascending)

        return results

    def _get_sort_key(self, sort_by: str):
        if sort_by == "area":
            return lambda p: p.area_m2
        if sort_by == "price_per_m2":
            return lambda p: p.price_per_m2
        if sort_by == "date":
            return lambda p: p.date_listed
        return lambda p: p.price

    def quick_search(self, query: str) -> list[Property]:
        """Búsqueda rápida por texto libre."""
        return self.search(SearchFilters(keyword=query, status=None))

    def search_by_budget(self, min_price: float, max_price: float, is_rental: bool = False) -> list[Property]:
        return self.search(SearchFilters(min_price=min_price, max_price=max_price, is_rental=is_rental))

    def search_residential(
        self,
        city: str = "",
        min_bedrooms: int = 0,
        max_price: float = float("inf"),
        is_rental: bool = False,
    ) -> list[Property]:
        types = ["piso", "casa", "chalet", "dúplex", "ático", "estudio"]
        filters = SearchFilters(
            property_types=types,
            min_bedrooms=min_bedrooms,
            max_price=max_price,
            is_rental=is_rental,
        )
        if city:
            filters.cities = [city]
        return self.search(filters)

    def search_commercial(self, city: str = "", max_price: float = float("inf"), is_rental: Optional[bool] = None) -> list[Property]:
        types = ["oficina", "local_comercial", "nave_industrial"]
        filters = SearchFilters(property_types=types, max_price=max_price, is_rental=is_rental)
        if city:
            filters.cities = [city]
        return self.search(filters)

    def search_land(self, province: str = "", max_price: float = float("inf")) -> list[Property]:
        types = ["terreno_urbano", "terreno_rústico"]
        filters = SearchFilters(property_types=types, max_price=max_price)
        if province:
            filters.provinces = [province]
        return self.search(filters)

    def search_rural(self, max_price: float = float("inf")) -> list[Property]:
        types = ["finca_rústica", "casa_rural"]
        return self.search(SearchFilters(property_types=types, max_price=max_price))

    def search_garages(self, city: str = "", max_price: float = float("inf"), is_rental: Optional[bool] = None) -> list[Property]:
        types = ["garaje", "trastero"]
        filters = SearchFilters(property_types=types, max_price=max_price, is_rental=is_rental)
        if city:
            filters.cities = [city]
        return self.search(filters)

    def get_property_count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for prop in self.db.properties.values():
            type_name = prop.property_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def get_property_count_by_city(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for prop in self.db.properties.values():
            counts[prop.city] = counts.get(prop.city, 0) + 1
        return counts
