"""Orquestador principal del Agente Inmobiliario."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.data.database import Database
from src.crm.manager import CRMManager
from src.search.engine import SearchEngine, SearchFilters
from src.estimation.estimator import PriceEstimator
from src.models.property import Property, PropertyStatus
from src.models.client import ClientInterest, ClientStatus


class RealEstateAgent:
    """Agente inmobiliario inteligente que orquesta todas las operaciones."""

    def __init__(self):
        self.db = Database(load_samples=True)
        self.crm = CRMManager(self.db)
        self.search = SearchEngine(self.db)
        self.estimator = PriceEstimator(self.db)

    # --- Dashboard ---

    def get_dashboard(self) -> dict:
        """Panel de control con estadísticas generales."""
        props = list(self.db.properties.values())
        available = [p for p in props if p.status == PropertyStatus.AVAILABLE]
        sales = [p for p in available if not p.is_rental]
        rentals = [p for p in available if p.is_rental]

        by_type = self.search.get_property_count_by_type()
        by_city = self.search.get_property_count_by_city()

        return {
            "total_properties": len(props),
            "available": len(available),
            "reserved": sum(1 for p in props if p.status == PropertyStatus.RESERVED),
            "sold": sum(1 for p in props if p.status == PropertyStatus.SOLD),
            "for_sale": len(sales),
            "for_rent": len(rentals),
            "total_clients": self.db.total_clients,
            "active_clients": sum(
                1 for c in self.db.get_all_clients() if c.status == ClientStatus.ACTIVE
            ),
            "by_type": by_type,
            "by_city": dict(sorted(by_city.items(), key=lambda x: x[1], reverse=True)[:10]),
            "avg_price_sale": round(
                sum(p.price for p in sales) / len(sales), 2
            ) if sales else 0,
        }

    # --- Búsquedas ---

    def search_properties(self, filters: SearchFilters) -> list[dict]:
        results = self.search.search(filters)
        return [self._format_property_summary(p) for p in results]

    def quick_search(self, query: str) -> list[dict]:
        results = self.search.quick_search(query)
        return [self._format_property_summary(p) for p in results]

    def get_property_detail(self, property_id: str) -> Optional[dict]:
        prop = self.db.get_property(property_id)
        if not prop:
            return None
        return self._format_property_detail(prop)

    # --- CRM ---

    def create_client(self, name: str, email: str, phone: str, interest: Optional[ClientInterest] = None):
        return self.crm.create_client(name, email, phone, interest)

    def get_client_info(self, client_id: str) -> Optional[dict]:
        return self.crm.get_client_summary(client_id)

    def list_clients(self) -> list[dict]:
        return self.crm.get_all_clients_summary()

    def schedule_visit(self, client_id: str, property_id: str, visit_date: datetime, notes: str = ""):
        return self.crm.schedule_visit(client_id, property_id, visit_date, notes)

    def get_client_visits(self, client_id: str) -> list[dict]:
        return self.crm.get_client_visits(client_id)

    def add_favorite(self, client_id: str, property_id: str, notes: str = ""):
        return self.crm.add_favorite(client_id, property_id, notes)

    def get_favorites(self, client_id: str) -> list[dict]:
        return self.crm.get_client_favorites(client_id)

    def find_properties_for_client(self, client_id: str) -> list[dict]:
        matches = self.crm.find_matching_properties(client_id)
        return [self._format_property_summary(p) for p in matches]

    # --- Estimación ---

    def estimate_price(self, city: str, property_type: str, area_m2: float, bedrooms: int = 0, features: Optional[list[str]] = None):
        return self.estimator.estimate_price(city, property_type, area_m2, bedrooms, features)

    def get_comparative(self, property_id: str):
        return self.estimator.get_market_comparative(property_id)

    def get_zone_stats(self, city: str) -> dict:
        return self.estimator.get_zone_stats(city)

    # --- Formateo ---

    def _format_property_summary(self, prop: Property) -> dict:
        summary = {
            "id": prop.id,
            "title": prop.title,
            "type": prop.property_type.value,
            "price": f"{prop.price:,.0f}€" if not prop.is_rental else f"{prop.monthly_rent:,.0f}€/mes",
            "city": prop.city,
            "area": f"{prop.area_m2}m²",
            "price_m2": f"{prop.price_per_m2:,.0f}€/m²",
            "status": prop.status.value,
        }
        if hasattr(prop, "bedrooms") and prop.bedrooms > 0:
            summary["bedrooms"] = prop.bedrooms
        if hasattr(prop, "bathrooms") and prop.bathrooms > 0:
            summary["bathrooms"] = prop.bathrooms
        return summary

    def _format_property_detail(self, prop: Property) -> dict:
        detail = prop.to_dict()
        detail["price_formatted"] = (
            f"{prop.price:,.0f}€" if not prop.is_rental else f"{prop.monthly_rent:,.0f}€/mes"
        )
        detail["price_per_m2_formatted"] = f"{prop.price_per_m2:,.0f}€/m²"

        # Campos extra según tipo
        if hasattr(prop, "bedrooms"):
            detail["bedrooms"] = prop.bedrooms
            detail["bathrooms"] = getattr(prop, "bathrooms", 0)
            detail["floor"] = getattr(prop, "floor", None)
            detail["has_elevator"] = getattr(prop, "has_elevator", False)
            detail["has_terrace"] = getattr(prop, "has_terrace", False)
            detail["has_garage"] = getattr(prop, "has_garage", False)
            detail["has_pool"] = getattr(prop, "has_pool", False)
            detail["has_garden"] = getattr(prop, "has_garden", False)
            detail["orientation"] = getattr(prop, "orientation", None)
            detail["community_fees"] = getattr(prop, "community_fees", None)

        if hasattr(prop, "commercial_type"):
            detail["commercial_type"] = prop.commercial_type
            detail["ceiling_height"] = getattr(prop, "ceiling_height", None)
            detail["has_loading_dock"] = getattr(prop, "has_loading_dock", False)
            detail["parking_spots"] = getattr(prop, "parking_spots", 0)

        if hasattr(prop, "buildable_area_m2"):
            detail["buildable_area_m2"] = prop.buildable_area_m2
            detail["land_classification"] = getattr(prop, "land_classification", "")
            detail["has_utilities"] = getattr(prop, "has_utilities", False)

        if hasattr(prop, "land_area_m2"):
            detail["land_area_m2"] = prop.land_area_m2
            detail["has_farmhouse"] = getattr(prop, "has_farmhouse", False)
            detail["crop_type"] = getattr(prop, "crop_type", None)

        if hasattr(prop, "vehicle_type"):
            detail["vehicle_type"] = prop.vehicle_type
            detail["is_covered"] = getattr(prop, "is_covered", True)
            detail["has_ev_charger"] = getattr(prop, "has_ev_charger", False)

        return detail
