"""Gestor CRM: clientes, visitas, favoritos y seguimiento."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.data.database import Database
from src.models.client import Client, ClientInterest, ClientStatus, VisitRecord, Favorite
from src.models.property import Property


class CRMManager:
    """Motor CRM completo para gestión de clientes inmobiliarios."""

    def __init__(self, db: Database):
        self.db = db

    # --- Gestión de clientes ---

    def create_client(
        self,
        name: str,
        email: str,
        phone: str,
        interest: Optional[ClientInterest] = None,
    ) -> Client:
        client_id = f"CLI-{uuid4().hex[:6].upper()}"
        client = Client(
            id=client_id,
            name=name,
            email=email,
            phone=phone,
            interest=interest or ClientInterest(),
            assigned_agent="Agente Principal",
        )
        self.db.add_client(client)
        return client

    def update_client_status(self, client_id: str, status: ClientStatus) -> Optional[Client]:
        client = self.db.get_client(client_id)
        if client:
            client.status = status
        return client

    def update_client_interest(self, client_id: str, interest: ClientInterest) -> Optional[Client]:
        client = self.db.get_client(client_id)
        if client:
            client.interest = interest
        return client

    def add_client_note(self, client_id: str, note: str) -> Optional[Client]:
        client = self.db.get_client(client_id)
        if client:
            client.notes.append(note)
            client.last_contact = datetime.now()
        return client

    def get_client_summary(self, client_id: str) -> Optional[dict]:
        client = self.db.get_client(client_id)
        if not client:
            return None
        return {
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "phone": client.phone,
            "status": client.status.value,
            "interest": {
                "types": client.interest.property_types,
                "budget": f"{client.interest.min_price:,.0f}€ - {client.interest.max_price:,.0f}€",
                "cities": client.interest.preferred_cities,
                "is_rental": client.interest.is_rental,
            },
            "visits": client.visit_count,
            "favorites": len(client.favorites),
            "notes": client.notes,
        }

    # --- Visitas ---

    def schedule_visit(
        self,
        client_id: str,
        property_id: str,
        visit_date: datetime,
        notes: str = "",
    ) -> Optional[VisitRecord]:
        client = self.db.get_client(client_id)
        prop = self.db.get_property(property_id)
        if not client or not prop:
            return None

        visit = VisitRecord(
            id=f"VIS-{uuid4().hex[:6].upper()}",
            client_id=client_id,
            property_id=property_id,
            visit_date=visit_date,
            notes=notes,
        )
        client.add_visit(visit)
        return visit

    def record_visit_feedback(
        self,
        client_id: str,
        visit_id: str,
        rating: int,
        interested: bool,
        notes: str = "",
        follow_up_date: Optional[datetime] = None,
    ) -> Optional[VisitRecord]:
        client = self.db.get_client(client_id)
        if not client:
            return None
        for visit in client.visits:
            if visit.id == visit_id:
                visit.rating = max(1, min(5, rating))
                visit.interested = interested
                if notes:
                    visit.notes = notes
                visit.follow_up_date = follow_up_date
                return visit
        return None

    def get_client_visits(self, client_id: str) -> list[dict]:
        client = self.db.get_client(client_id)
        if not client:
            return []
        results = []
        for visit in client.visits:
            prop = self.db.get_property(visit.property_id)
            results.append({
                "visit_id": visit.id,
                "property": prop.title if prop else visit.property_id,
                "date": visit.visit_date.strftime("%d/%m/%Y %H:%M"),
                "rating": visit.rating,
                "interested": visit.interested,
                "notes": visit.notes,
            })
        return results

    def get_pending_follow_ups(self) -> list[dict]:
        follow_ups = []
        now = datetime.now()
        for client in self.db.get_all_clients():
            for visit in client.visits:
                if visit.follow_up_date and visit.follow_up_date <= now:
                    prop = self.db.get_property(visit.property_id)
                    follow_ups.append({
                        "client": client.name,
                        "client_id": client.id,
                        "property": prop.title if prop else visit.property_id,
                        "follow_up_date": visit.follow_up_date.strftime("%d/%m/%Y"),
                        "visit_notes": visit.notes,
                    })
        return follow_ups

    # --- Favoritos ---

    def add_favorite(self, client_id: str, property_id: str, notes: str = "") -> Optional[Favorite]:
        client = self.db.get_client(client_id)
        prop = self.db.get_property(property_id)
        if not client or not prop:
            return None
        if property_id in client.favorite_property_ids:
            return None
        return client.add_favorite(property_id, notes)

    def remove_favorite(self, client_id: str, property_id: str) -> bool:
        client = self.db.get_client(client_id)
        if not client:
            return False
        return client.remove_favorite(property_id)

    def get_client_favorites(self, client_id: str) -> list[dict]:
        client = self.db.get_client(client_id)
        if not client:
            return []
        results = []
        for fav in client.favorites:
            prop = self.db.get_property(fav.property_id)
            if prop:
                results.append({
                    "property_id": prop.id,
                    "title": prop.title,
                    "price": prop.price,
                    "city": prop.city,
                    "area_m2": prop.area_m2,
                    "notes": fav.notes,
                    "added": fav.added_date.strftime("%d/%m/%Y"),
                })
        return results

    # --- Matching clientes-propiedades ---

    def find_matching_properties(self, client_id: str) -> list[Property]:
        client = self.db.get_client(client_id)
        if not client:
            return []

        interest = client.interest
        matches = []

        for prop in self.db.get_available_properties():
            if interest.is_rental != prop.is_rental:
                continue

            if interest.property_types:
                if prop.property_type.value not in interest.property_types:
                    continue

            price = prop.monthly_rent if prop.is_rental else prop.price
            if price is None:
                continue
            if not (interest.min_price <= price <= interest.max_price):
                continue

            if interest.min_area > 0 and prop.area_m2 < interest.min_area:
                continue

            if interest.preferred_cities:
                if prop.city.lower() not in [c.lower() for c in interest.preferred_cities]:
                    continue

            if interest.preferred_provinces:
                if prop.province.lower() not in [p.lower() for p in interest.preferred_provinces]:
                    continue

            if interest.min_bedrooms > 0 and hasattr(prop, "bedrooms"):
                if prop.bedrooms < interest.min_bedrooms:
                    continue

            if interest.needs_garage and hasattr(prop, "has_garage"):
                if not prop.has_garage:
                    continue

            matches.append(prop)

        return matches

    def get_all_clients_summary(self) -> list[dict]:
        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status.value,
                "interest_types": c.interest.property_types,
                "budget": f"{c.interest.min_price:,.0f}€ - {c.interest.max_price:,.0f}€",
                "visits": c.visit_count,
                "favorites": len(c.favorites),
            }
            for c in self.db.get_all_clients()
        ]
