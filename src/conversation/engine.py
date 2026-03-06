"""Motor de conversación híbrido: IA + reglas de negocio."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.models.lead import Lead, LeadStatus, UrgencyLevel


# --- Reglas de negocio para calificación ---

QUALIFICATION_RULES = {
    "greeting": {
        "triggers": ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "hi"],
        "response": (
            "¡Hola! 👋 Soy el asistente inmobiliario. "
            "Estoy aquí para ayudarle a encontrar la propiedad perfecta. "
            "¿Busca comprar o alquilar?"
        ),
        "extracts": None,
        "next_question": "operation_type",
    },
    "buy": {
        "triggers": ["comprar", "compra", "adquirir", "inversión", "invertir"],
        "response": (
            "Perfecto, le ayudo a encontrar la mejor opción para comprar. "
            "¿Qué tipo de propiedad le interesa? (piso, casa, chalet, local, terreno...)"
        ),
        "extracts": {"is_rental": False},
        "next_question": "property_type",
    },
    "rent": {
        "triggers": ["alquilar", "alquiler", "arrendar", "rentar"],
        "response": (
            "Perfecto, le ayudo a encontrar el mejor alquiler. "
            "¿Qué tipo de propiedad busca? (piso, casa, oficina, local...)"
        ),
        "extracts": {"is_rental": True},
        "next_question": "property_type",
    },
    "apartment": {
        "triggers": ["piso", "apartamento", "flat", "estudio", "loft"],
        "response": (
            "¡Genial! Tenemos muchas opciones en pisos. "
            "¿En qué zona o ciudad le gustaría buscar?"
        ),
        "extracts": {"property_types": ["piso", "dúplex", "ático", "estudio"]},
        "next_question": "location",
    },
    "house": {
        "triggers": ["casa", "chalet", "villa", "adosado", "pareado", "unifamiliar"],
        "response": (
            "Tenemos excelentes casas y chalets. "
            "¿En qué zona le gustaría vivir?"
        ),
        "extracts": {"property_types": ["casa", "chalet"]},
        "next_question": "location",
    },
    "commercial": {
        "triggers": ["local", "oficina", "nave", "negocio", "comercial"],
        "response": (
            "Tenemos opciones comerciales interesantes. "
            "¿Cuál es su presupuesto aproximado?"
        ),
        "extracts": {"property_types": ["local_comercial", "oficina", "nave_industrial"]},
        "next_question": "budget",
    },
    "urgent": {
        "triggers": ["urgente", "ya", "inmediato", "cuanto antes", "rápido", "esta semana"],
        "response": (
            "Entendido, lo marcamos como urgente. "
            "Vamos a priorizar su búsqueda. ¿Cuál es su presupuesto?"
        ),
        "extracts": {"urgency": "inmediata"},
        "next_question": "budget",
    },
    "budget_low": {
        "triggers": ["barato", "económico", "low cost", "poco presupuesto", "ajustado"],
        "response": (
            "Entendido, buscaremos las opciones más competitivas. "
            "¿Puede indicarme un rango de precio máximo?"
        ),
        "extracts": None,
        "next_question": "budget",
    },
    "thanks": {
        "triggers": ["gracias", "perfecto", "genial", "vale", "ok", "de acuerdo"],
        "response": None,  # Se determina dinámicamente
        "extracts": None,
        "next_question": None,
    },
    "visit": {
        "triggers": ["visitar", "ver", "visita", "enseñar", "mostrar", "quedar"],
        "response": (
            "¡Genial que quiera visitar! Permítame buscar las mejores opciones "
            "y le propongo fechas. ¿Tiene preferencia de horario?"
        ),
        "extracts": None,
        "next_question": None,
    },
}

# Preguntas de calificación en orden
QUALIFICATION_QUESTIONS = [
    {
        "key": "operation_type",
        "ask": "¿Busca comprar o alquilar?",
    },
    {
        "key": "property_type",
        "ask": "¿Qué tipo de propiedad le interesa? (piso, casa, local, terreno, garaje...)",
    },
    {
        "key": "location",
        "ask": "¿En qué ciudad o zona le gustaría buscar?",
    },
    {
        "key": "budget",
        "ask": "¿Cuál es su presupuesto aproximado?",
    },
    {
        "key": "urgency",
        "ask": "¿En qué plazo necesita la propiedad? (inmediato, 1-3 meses, 3-6 meses, más de 6 meses)",
    },
    {
        "key": "bedrooms",
        "ask": "¿Cuántas habitaciones necesita como mínimo?",
    },
    {
        "key": "requirements",
        "ask": "¿Tiene algún requisito especial? (garaje, piscina, ascensor, vistas...)",
    },
]


@dataclass
class ConversationResponse:
    """Respuesta del motor de conversación."""
    message: str
    extracted_data: dict = field(default_factory=dict)
    suggested_question: str | None = None
    intent: str = "unknown"
    confidence: float = 0.0
    matched_properties_count: int = 0


class ConversationEngine:
    """Motor híbrido de conversación: reglas de negocio + IA."""

    def __init__(self):
        self._rules = QUALIFICATION_RULES
        self._questions = QUALIFICATION_QUESTIONS

    def process_message(
        self,
        message: str,
        lead: Lead,
        matched_properties: list[dict] | None = None,
    ) -> ConversationResponse:
        """Procesa un mensaje del lead y genera respuesta."""
        message_lower = message.lower().strip()

        # 1. Intentar matchear con reglas de negocio
        rule_response = self._match_rules(message_lower, lead)
        if rule_response and rule_response.confidence > 0.3:
            # Aplicar datos extraídos
            if rule_response.extracted_data:
                self._apply_extracted_data(lead, rule_response.extracted_data)

            # Añadir info de propiedades si hay matches
            if matched_properties:
                rule_response.matched_properties_count = len(matched_properties)
                if len(matched_properties) > 0:
                    rule_response.message += self._format_property_suggestions(
                        matched_properties[:3]
                    )

            return rule_response

        # 2. Si no matchea reglas, generar respuesta contextual
        return self._generate_contextual_response(message_lower, lead, matched_properties)

    def _match_rules(self, message: str, lead: Lead) -> ConversationResponse | None:
        """Intenta matchear el mensaje con reglas predefinidas."""
        best_match = None
        best_score = 0.0

        for rule_key, rule in self._rules.items():
            for trigger in rule["triggers"]:
                if trigger in message:
                    # Score basado en longitud del trigger vs mensaje
                    score = len(trigger) / max(len(message), 1)
                    score = min(score * 2, 1.0)  # Boost
                    if score > best_score:
                        best_score = score
                        response_text = rule["response"]

                        # Respuesta dinámica para "gracias/ok"
                        if response_text is None:
                            response_text = self._get_dynamic_thanks_response(lead)

                        best_match = ConversationResponse(
                            message=response_text,
                            extracted_data=rule["extracts"] or {},
                            suggested_question=rule["next_question"],
                            intent=rule_key,
                            confidence=score,
                        )

        return best_match

    def _generate_contextual_response(
        self,
        message: str,
        lead: Lead,
        matched_properties: list[dict] | None = None,
    ) -> ConversationResponse:
        """Genera respuesta contextual basada en el estado del lead."""
        # Encontrar la siguiente pregunta no respondida
        answered_keys = {a.question_key for a in lead.qualification_answers}

        for q in self._questions:
            if q["key"] not in answered_keys:
                # Intentar extraer datos del mensaje libre
                extracted = self._extract_from_free_text(message, q["key"])

                response = q["ask"]
                if matched_properties and len(matched_properties) > 0:
                    response += self._format_property_suggestions(matched_properties[:2])

                return ConversationResponse(
                    message=response,
                    extracted_data=extracted,
                    suggested_question=q["key"],
                    intent="qualification",
                    confidence=0.3,
                    matched_properties_count=len(matched_properties or []),
                )

        # Si ya está todo respondido
        if matched_properties and len(matched_properties) > 0:
            msg = (
                f"¡Excelente! Basándome en sus preferencias, he encontrado "
                f"{len(matched_properties)} propiedades que podrían interesarle."
            )
            msg += self._format_property_suggestions(matched_properties[:5])
            msg += "\n\n¿Le gustaría programar una visita a alguna de ellas?"
        else:
            msg = (
                "Gracias por la información. Ahora mismo no tenemos propiedades "
                "que encajen exactamente, pero le avisaremos en cuanto tengamos algo. "
                "¿Hay algo más que pueda ajustar en su búsqueda?"
            )

        return ConversationResponse(
            message=msg,
            intent="complete",
            confidence=0.5,
            matched_properties_count=len(matched_properties or []),
        )

    def _extract_from_free_text(self, message: str, expected_key: str) -> dict:
        """Intenta extraer datos del texto libre según el contexto esperado."""
        extracted = {}
        msg_lower = message.lower()

        # Extraer ciudades comunes
        spanish_cities = [
            "madrid", "barcelona", "valencia", "sevilla", "bilbao",
            "málaga", "zaragoza", "alicante", "marbella", "granada",
        ]
        found_cities = [c.title() for c in spanish_cities if c in msg_lower]
        if found_cities:
            extracted["preferred_cities"] = found_cities

        # Extraer números como posible presupuesto
        import re
        numbers = re.findall(r"(\d+[\.,]?\d*)", message.replace(".", ""))
        if numbers and expected_key == "budget":
            try:
                amount = float(numbers[0].replace(",", "."))
                if amount < 10000:
                    amount *= 1000  # Asumimos miles
                extracted["max_price"] = amount
            except ValueError:
                pass

        # Detectar alquiler/compra
        if "alquil" in msg_lower:
            extracted["is_rental"] = True
        elif "compr" in msg_lower:
            extracted["is_rental"] = False

        return extracted

    def _apply_extracted_data(self, lead: Lead, data: dict) -> None:
        """Aplica datos extraídos al perfil del lead."""
        interest = lead.interest

        if "is_rental" in data:
            interest.is_rental = data["is_rental"]
        if "property_types" in data:
            interest.property_types = data["property_types"]
        if "preferred_cities" in data:
            interest.preferred_cities = data["preferred_cities"]
        if "max_price" in data:
            interest.max_price = data["max_price"]
        if "urgency" in data:
            try:
                interest.urgency = UrgencyLevel(data["urgency"])
            except ValueError:
                pass

    def _format_property_suggestions(self, properties: list[dict]) -> str:
        """Formatea sugerencias de propiedades para el mensaje."""
        if not properties:
            return ""

        text = "\n\n📋 **Propiedades recomendadas:**\n"
        for i, p in enumerate(properties, 1):
            bedrooms = f", {p.get('bedrooms')} hab" if p.get("bedrooms") else ""
            text += f"{i}. **{p['title']}** - {p['price']} ({p['area']}{bedrooms})\n"

        return text

    def _get_dynamic_thanks_response(self, lead: Lead) -> str:
        """Genera respuesta dinámica cuando el lead dice gracias/ok."""
        answered_keys = {a.question_key for a in lead.qualification_answers}

        for q in self._questions:
            if q["key"] not in answered_keys:
                return f"De nada. Para seguir ayudándole: {q['ask']}"

        if lead.matched_properties:
            return (
                "¡Perfecto! Tiene propiedades que le pueden interesar. "
                "¿Le gustaría programar una visita?"
            )

        return (
            "¡Encantado de ayudarle! Si necesita cualquier cosa, "
            "no dude en escribirme."
        )

    def get_welcome_message(self, lead: Lead) -> str:
        """Genera mensaje de bienvenida personalizado según la fuente."""
        source_messages = {
            "whatsapp": (
                f"¡Hola {lead.name}! 👋 Gracias por contactarnos por WhatsApp. "
                "Soy su asistente inmobiliario y estoy aquí para ayudarle a encontrar "
                "la propiedad perfecta. ¿Busca comprar o alquilar?"
            ),
            "formulario_web": (
                f"¡Hola {lead.name}! Gracias por rellenar nuestro formulario. "
                "He recibido su consulta y voy a ayudarle personalmente. "
                "¿Podría indicarme qué tipo de propiedad busca?"
            ),
            "idealista": (
                f"¡Hola {lead.name}! He visto que está interesado en una de nuestras "
                "propiedades en Idealista. ¿Le gustaría más información o programar una visita?"
            ),
            "fotocasa": (
                f"¡Hola {lead.name}! Gracias por su interés en nuestras propiedades "
                "en Fotocasa. ¿En qué puedo ayudarle?"
            ),
            "redes_sociales": (
                f"¡Hola {lead.name}! 👋 Gracias por contactarnos a través de redes sociales. "
                "¿En qué puedo ayudarle hoy?"
            ),
        }
        return source_messages.get(
            lead.source.value,
            f"¡Hola {lead.name}! Bienvenido. ¿En qué puedo ayudarle? "
            "¿Busca comprar o alquilar una propiedad?",
        )
