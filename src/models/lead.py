"""Modelos de leads con scoring y calificación progresiva."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LeadSource(Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEB_FORM = "formulario_web"
    IDEALISTA = "idealista"
    FOTOCASA = "fotocasa"
    SOCIAL_MEDIA = "redes_sociales"
    PHONE = "telefono"
    REFERRAL = "referido"
    WALK_IN = "presencial"
    OTHER = "otro"


class LeadStatus(Enum):
    NEW = "nuevo"
    CONTACTED = "contactado"
    QUALIFYING = "calificando"
    QUALIFIED = "calificado"
    VISIT_SCHEDULED = "visita_programada"
    VISITED = "visitado"
    NEGOTIATING = "negociando"
    CONVERTED = "convertido"
    LOST = "perdido"
    INACTIVE = "inactivo"


class LeadTemperature(Enum):
    HOT = "caliente"
    WARM = "tibio"
    COLD = "frio"


class UrgencyLevel(Enum):
    IMMEDIATE = "inmediata"      # < 1 mes
    SHORT_TERM = "corto_plazo"   # 1-3 meses
    MEDIUM_TERM = "medio_plazo"  # 3-6 meses
    LONG_TERM = "largo_plazo"    # > 6 meses
    UNKNOWN = "desconocida"


@dataclass
class LeadScoring:
    """Scoring automático del lead de 0 a 100."""
    total: int = 0
    budget_score: int = 0       # 0-25: tiene presupuesto definido y aprobado
    urgency_score: int = 0      # 0-25: urgencia de compra/alquiler
    engagement_score: int = 0   # 0-25: responde, visita, interactúa
    fit_score: int = 0          # 0-25: hay propiedades que encajan

    def recalculate(self) -> int:
        self.total = (
            self.budget_score
            + self.urgency_score
            + self.engagement_score
            + self.fit_score
        )
        return self.total

    @property
    def temperature(self) -> LeadTemperature:
        if self.total >= 70:
            return LeadTemperature.HOT
        if self.total >= 40:
            return LeadTemperature.WARM
        return LeadTemperature.COLD


@dataclass
class QualificationAnswer:
    """Respuesta a una pregunta de calificación."""
    question_key: str
    question_text: str
    answer: str
    answered_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationMessage:
    """Mensaje en la conversación con el lead."""
    role: str  # "lead" o "agent"
    content: str
    channel: str  # whatsapp, email, web, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class LeadInterest:
    """Intereses extraídos de la conversación con el lead."""
    property_types: list[str] = field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    preferred_cities: list[str] = field(default_factory=list)
    preferred_zones: list[str] = field(default_factory=list)
    min_bedrooms: Optional[int] = None
    needs_garage: Optional[bool] = None
    needs_elevator: Optional[bool] = None
    is_rental: Optional[bool] = None
    urgency: UrgencyLevel = UrgencyLevel.UNKNOWN
    specific_requirements: list[str] = field(default_factory=list)


@dataclass
class Lead:
    """Lead inmobiliario con scoring y calificación progresiva."""
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    source: LeadSource = LeadSource.OTHER
    status: LeadStatus = LeadStatus.NEW
    scoring: LeadScoring = field(default_factory=LeadScoring)
    interest: LeadInterest = field(default_factory=LeadInterest)
    qualification_answers: list[QualificationAnswer] = field(default_factory=list)
    conversation: list[ConversationMessage] = field(default_factory=list)
    matched_properties: list[str] = field(default_factory=list)
    assigned_agent: str = ""
    notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_contact: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    converted_client_id: Optional[str] = None

    @property
    def temperature(self) -> LeadTemperature:
        return self.scoring.temperature

    @property
    def is_qualified(self) -> bool:
        return self.status in (
            LeadStatus.QUALIFIED,
            LeadStatus.VISIT_SCHEDULED,
            LeadStatus.VISITED,
            LeadStatus.NEGOTIATING,
            LeadStatus.CONVERTED,
        )

    @property
    def qualification_progress(self) -> float:
        """Porcentaje de preguntas clave respondidas (0-100)."""
        key_fields = [
            self.interest.max_price is not None,
            self.interest.is_rental is not None,
            len(self.interest.preferred_cities) > 0,
            len(self.interest.property_types) > 0,
            self.interest.urgency != UrgencyLevel.UNKNOWN,
        ]
        answered = sum(1 for f in key_fields if f)
        return round((answered / len(key_fields)) * 100, 1)

    def add_message(self, role: str, content: str, channel: str, metadata: dict | None = None) -> ConversationMessage:
        msg = ConversationMessage(
            role=role, content=content, channel=channel,
            metadata=metadata or {},
        )
        self.conversation.append(msg)
        self.last_contact = msg.timestamp
        return msg

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "source": self.source.value,
            "status": self.status.value,
            "score": self.scoring.total,
            "temperature": self.temperature.value,
            "qualification_progress": self.qualification_progress,
            "interest": {
                "property_types": self.interest.property_types,
                "budget": f"{self.interest.min_price or 0:,.0f}€ - {self.interest.max_price or 0:,.0f}€"
                if self.interest.max_price else "Sin definir",
                "cities": self.interest.preferred_cities,
                "is_rental": self.interest.is_rental,
                "urgency": self.interest.urgency.value,
            },
            "matched_properties": len(self.matched_properties),
            "assigned_agent": self.assigned_agent,
            "messages": len(self.conversation),
            "created_at": self.created_at.isoformat(),
            "last_contact": self.last_contact.isoformat() if self.last_contact else None,
            "tags": self.tags,
        }
