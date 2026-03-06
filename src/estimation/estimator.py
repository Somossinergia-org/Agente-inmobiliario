"""Motor de estimación de precios y comparativas de mercado."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.data.database import Database
from src.models.property import Property, ResidentialProperty


@dataclass
class PriceEstimation:
    estimated_price: float
    price_per_m2: float
    comparable_count: int
    min_price: float
    max_price: float
    avg_price: float
    confidence: str  # alta, media, baja
    comparables: list[dict]


@dataclass
class MarketComparative:
    property: Property
    similar_properties: list[dict]
    avg_price_m2_zone: float
    price_position: str  # por_debajo, en_media, por_encima
    price_difference_pct: float
    market_summary: str


class PriceEstimator:
    """Estimador de precios basado en comparativas de mercado."""

    def __init__(self, db: Database):
        self.db = db

    def estimate_price(
        self,
        city: str,
        property_type_value: str,
        area_m2: float,
        bedrooms: int = 0,
        features: Optional[list[str]] = None,
    ) -> PriceEstimation:
        """Estima el precio de una propiedad basándose en comparables."""
        comparables = self._find_comparables(city, property_type_value, area_m2, bedrooms)

        if not comparables:
            comparables = self._find_comparables_broad(property_type_value, area_m2)

        if not comparables:
            return PriceEstimation(
                estimated_price=0, price_per_m2=0, comparable_count=0,
                min_price=0, max_price=0, avg_price=0,
                confidence="baja", comparables=[],
            )

        prices = [p.price for p in comparables]
        prices_m2 = [p.price_per_m2 for p in comparables]

        avg_price_m2 = sum(prices_m2) / len(prices_m2)
        estimated = avg_price_m2 * area_m2

        # Ajustes por características premium
        if features:
            premium_features = {"piscina", "vistas al mar", "terraza", "jardín", "domótica", "garaje"}
            bonus = sum(0.03 for f in features if any(pf in f.lower() for pf in premium_features))
            estimated *= (1 + bonus)

        confidence = "alta" if len(comparables) >= 5 else "media" if len(comparables) >= 3 else "baja"

        comp_list = [
            {
                "id": p.id,
                "title": p.title,
                "price": p.price,
                "area_m2": p.area_m2,
                "price_per_m2": round(p.price_per_m2, 2),
                "city": p.city,
            }
            for p in comparables[:10]
        ]

        return PriceEstimation(
            estimated_price=round(estimated, -3),
            price_per_m2=round(avg_price_m2, 2),
            comparable_count=len(comparables),
            min_price=min(prices),
            max_price=max(prices),
            avg_price=round(sum(prices) / len(prices), 2),
            confidence=confidence,
            comparables=comp_list,
        )

    def get_market_comparative(self, property_id: str) -> Optional[MarketComparative]:
        """Genera informe comparativo de mercado para una propiedad."""
        prop = self.db.get_property(property_id)
        if not prop:
            return None

        similar = self._find_comparables(
            prop.city, prop.property_type.value, prop.area_m2,
            getattr(prop, "bedrooms", 0),
        )
        # Excluir la propia propiedad
        similar = [s for s in similar if s.id != prop.id]

        if not similar:
            similar = self._find_comparables_broad(prop.property_type.value, prop.area_m2)
            similar = [s for s in similar if s.id != prop.id]

        if not similar:
            return MarketComparative(
                property=prop, similar_properties=[], avg_price_m2_zone=0,
                price_position="sin_datos", price_difference_pct=0,
                market_summary="No se encontraron propiedades comparables.",
            )

        avg_price_m2 = sum(s.price_per_m2 for s in similar) / len(similar)
        diff_pct = ((prop.price_per_m2 - avg_price_m2) / avg_price_m2) * 100

        if diff_pct < -10:
            position = "por_debajo"
        elif diff_pct > 10:
            position = "por_encima"
        else:
            position = "en_media"

        position_text = {
            "por_debajo": "por debajo de la media (posible oportunidad)",
            "en_media": "en línea con el mercado",
            "por_encima": "por encima de la media",
        }

        summary = (
            f"La propiedad '{prop.title}' tiene un precio de {prop.price_per_m2:,.0f}€/m² "
            f"frente a la media de {avg_price_m2:,.0f}€/m² en propiedades comparables. "
            f"Esto sitúa el precio {position_text.get(position, position)} "
            f"({diff_pct:+.1f}%). "
            f"Se han analizado {len(similar)} propiedades comparables."
        )

        sim_list = [
            {
                "id": s.id,
                "title": s.title,
                "price": s.price,
                "area_m2": s.area_m2,
                "price_per_m2": round(s.price_per_m2, 2),
                "city": s.city,
                "difference": f"{((s.price_per_m2 - prop.price_per_m2) / prop.price_per_m2) * 100:+.1f}%",
            }
            for s in similar[:10]
        ]

        return MarketComparative(
            property=prop,
            similar_properties=sim_list,
            avg_price_m2_zone=round(avg_price_m2, 2),
            price_position=position,
            price_difference_pct=round(diff_pct, 2),
            market_summary=summary,
        )

    def get_zone_stats(self, city: str) -> dict:
        """Estadísticas de precios por zona/ciudad."""
        props = [p for p in self.db.properties.values() if p.city.lower() == city.lower() and not p.is_rental]

        if not props:
            return {"city": city, "count": 0, "message": "Sin datos para esta zona"}

        prices = [p.price for p in props]
        prices_m2 = [p.price_per_m2 for p in props]

        by_type: dict[str, list[float]] = {}
        for p in props:
            type_name = p.property_type.value
            by_type.setdefault(type_name, []).append(p.price_per_m2)

        type_stats = {
            t: {"avg_price_m2": round(sum(v) / len(v), 2), "count": len(v)}
            for t, v in by_type.items()
        }

        return {
            "city": city,
            "count": len(props),
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price_m2": round(sum(prices_m2) / len(prices_m2), 2),
            "by_type": type_stats,
        }

    def _find_comparables(
        self, city: str, property_type_value: str, area_m2: float, bedrooms: int = 0
    ) -> list[Property]:
        area_range = 0.3
        min_area = area_m2 * (1 - area_range)
        max_area = area_m2 * (1 + area_range)

        results = []
        for prop in self.db.properties.values():
            if prop.is_rental:
                continue
            if prop.city.lower() != city.lower():
                continue
            if prop.property_type.value != property_type_value:
                continue
            if not (min_area <= prop.area_m2 <= max_area):
                continue
            if bedrooms > 0 and hasattr(prop, "bedrooms"):
                if abs(getattr(prop, "bedrooms", 0) - bedrooms) > 1:
                    continue
            results.append(prop)

        return results

    def _find_comparables_broad(self, property_type_value: str, area_m2: float) -> list[Property]:
        area_range = 0.5
        min_area = area_m2 * (1 - area_range)
        max_area = area_m2 * (1 + area_range)

        return [
            p for p in self.db.properties.values()
            if not p.is_rental
            and p.property_type.value == property_type_value
            and min_area <= p.area_m2 <= max_area
        ]
