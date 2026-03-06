"""Base de datos en memoria para el agente inmobiliario."""

from __future__ import annotations

from typing import Optional

from src.models.property import Property, PropertyStatus
from src.models.client import Client, VisitRecord, Favorite
from src.models.transaction import Transaction
from src.data.properties import get_all_properties, get_sample_clients


class Database:
    """Almacén central en memoria de propiedades, clientes y transacciones."""

    def __init__(self, load_samples: bool = True):
        self.properties: dict[str, Property] = {}
        self.clients: dict[str, Client] = {}
        self.transactions: dict[str, Transaction] = {}

        if load_samples:
            for prop in get_all_properties():
                self.properties[prop.id] = prop
            for client in get_sample_clients():
                self.clients[client.id] = client

    # --- Propiedades ---
    def get_property(self, property_id: str) -> Optional[Property]:
        return self.properties.get(property_id)

    def add_property(self, prop: Property) -> None:
        self.properties[prop.id] = prop

    def remove_property(self, property_id: str) -> bool:
        return self.properties.pop(property_id, None) is not None

    def get_available_properties(self) -> list[Property]:
        return [p for p in self.properties.values() if p.status == PropertyStatus.AVAILABLE]

    def get_properties_by_type(self, property_type_value: str) -> list[Property]:
        return [p for p in self.properties.values() if p.property_type.value == property_type_value]

    def get_properties_by_city(self, city: str) -> list[Property]:
        return [p for p in self.properties.values() if p.city.lower() == city.lower()]

    # --- Clientes ---
    def get_client(self, client_id: str) -> Optional[Client]:
        return self.clients.get(client_id)

    def add_client(self, client: Client) -> None:
        self.clients[client.id] = client

    def get_all_clients(self) -> list[Client]:
        return list(self.clients.values())

    # --- Transacciones ---
    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions[transaction.id] = transaction
        prop = self.get_property(transaction.property_id)
        if prop:
            prop.status = PropertyStatus.SOLD

    def get_transactions(self) -> list[Transaction]:
        return list(self.transactions.values())

    # --- Estadísticas ---
    @property
    def total_properties(self) -> int:
        return len(self.properties)

    @property
    def total_available(self) -> int:
        return len(self.get_available_properties())

    @property
    def total_clients(self) -> int:
        return len(self.clients)
