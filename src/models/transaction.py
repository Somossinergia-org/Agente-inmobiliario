"""Modelos de transacciones."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TransactionType(Enum):
    SALE = "venta"
    RENTAL = "alquiler"


@dataclass
class Transaction:
    id: str
    property_id: str
    client_id: str
    transaction_type: TransactionType
    amount: float
    date: datetime = field(default_factory=datetime.now)
    commission_rate: float = 0.03
    notes: str = ""
    contract_ref: Optional[str] = None

    @property
    def commission(self) -> float:
        return self.amount * self.commission_rate
