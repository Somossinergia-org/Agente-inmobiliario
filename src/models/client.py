"""Modelos de clientes y seguimiento."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ClientStatus(Enum):
    ACTIVE = "activo"
    INACTIVE = "inactivo"
    PROSPECT = "prospecto"
    CLOSED = "cerrado"


@dataclass
class ClientInterest:
    property_types: list[str] = field(default_factory=list)
    min_price: float = 0
    max_price: float = float("inf")
    min_area: float = 0
    max_area: float = float("inf")
    preferred_cities: list[str] = field(default_factory=list)
    preferred_provinces: list[str] = field(default_factory=list)
    min_bedrooms: int = 0
    needs_garage: bool = False
    needs_elevator: bool = False
    other_requirements: list[str] = field(default_factory=list)
    is_rental: bool = False


@dataclass
class VisitRecord:
    id: str
    client_id: str
    property_id: str
    visit_date: datetime
    notes: str = ""
    rating: Optional[int] = None  # 1-5
    interested: bool = False
    follow_up_date: Optional[datetime] = None


@dataclass
class Favorite:
    client_id: str
    property_id: str
    added_date: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class Client:
    id: str
    name: str
    email: str
    phone: str
    status: ClientStatus = ClientStatus.PROSPECT
    interest: ClientInterest = field(default_factory=ClientInterest)
    visits: list[VisitRecord] = field(default_factory=list)
    favorites: list[Favorite] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_contact: Optional[datetime] = None
    budget_approved: bool = False
    assigned_agent: str = ""

    def add_visit(self, visit: VisitRecord) -> None:
        self.visits.append(visit)
        self.last_contact = visit.visit_date

    def add_favorite(self, property_id: str, notes: str = "") -> Favorite:
        fav = Favorite(client_id=self.id, property_id=property_id, notes=notes)
        self.favorites.append(fav)
        return fav

    def remove_favorite(self, property_id: str) -> bool:
        for i, fav in enumerate(self.favorites):
            if fav.property_id == property_id:
                self.favorites.pop(i)
                return True
        return False

    @property
    def favorite_property_ids(self) -> list[str]:
        return [f.property_id for f in self.favorites]

    @property
    def visit_count(self) -> int:
        return len(self.visits)
