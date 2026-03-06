"""Gestor de leads con scoring automático y calificación progresiva."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from src.data.database import Database
from src.models.lead import (
    Lead, LeadInterest, LeadScoring, LeadSource, LeadStatus,
    LeadTemperature, QualificationAnswer, UrgencyLevel,
)
from src.models.client import Client, ClientInterest, ClientStatus
from src.models.property import PropertyStatus


class LeadManager:
    """Motor de gestión de leads con scoring automático."""

    def __init__(self, db: Database):
        self.db = db
        self.leads: dict[str, Lead] = {}

    # --- CRUD ---

    def create_lead(
        self,
        name: str,
        source: str = "otro",
        phone: str | None = None,
        email: str | None = None,
        initial_message: str = "",
        channel: str = "web",
    ) -> Lead:
        lead_id = f"LEAD-{uuid4().hex[:6].upper()}"
        try:
            lead_source = LeadSource(source)
        except ValueError:
            lead_source = LeadSource.OTHER

        lead = Lead(
            id=lead_id,
            name=name,
            phone=phone,
            email=email,
            source=lead_source,
        )

        if initial_message:
            lead.add_message("lead", initial_message, channel)

        self.leads[lead_id] = lead
        self._auto_score(lead)
        return lead

    def get_lead(self, lead_id: str) -> Lead | None:
        return self.leads.get(lead_id)

    def get_all_leads(self) -> list[Lead]:
        return list(self.leads.values())

    def update_lead_status(self, lead_id: str, status: str) -> Lead | None:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        try:
            lead.status = LeadStatus(status)
        except ValueError:
            return None
        return lead

    # --- SCORING AUTOMÁTICO ---

    def _auto_score(self, lead: Lead) -> None:
        """Recalcula el scoring del lead automáticamente."""
        interest = lead.interest

        # Budget score (0-25)
        if interest.max_price is not None and interest.max_price > 0:
            lead.scoring.budget_score = 15
            if interest.min_price is not None:
                lead.scoring.budget_score = 25
        else:
            lead.scoring.budget_score = 0

        # Urgency score (0-25)
        urgency_map = {
            UrgencyLevel.IMMEDIATE: 25,
            UrgencyLevel.SHORT_TERM: 20,
            UrgencyLevel.MEDIUM_TERM: 12,
            UrgencyLevel.LONG_TERM: 5,
            UrgencyLevel.UNKNOWN: 0,
        }
        lead.scoring.urgency_score = urgency_map.get(interest.urgency, 0)

        # Engagement score (0-25)
        msg_count = len(lead.conversation)
        if msg_count >= 10:
            lead.scoring.engagement_score = 25
        elif msg_count >= 5:
            lead.scoring.engagement_score = 18
        elif msg_count >= 2:
            lead.scoring.engagement_score = 10
        elif msg_count >= 1:
            lead.scoring.engagement_score = 5
        else:
            lead.scoring.engagement_score = 0

        # Fit score (0-25): hay propiedades que encajan
        matches = self._find_matching_properties(lead)
        lead.matched_properties = [p.id for p in matches]
        if len(matches) >= 5:
            lead.scoring.fit_score = 25
        elif len(matches) >= 3:
            lead.scoring.fit_score = 20
        elif len(matches) >= 1:
            lead.scoring.fit_score = 12
        else:
            lead.scoring.fit_score = 0

        lead.scoring.recalculate()

        # Auto-qualify si score alto y tiene suficiente info
        if lead.scoring.total >= 60 and lead.qualification_progress >= 60:
            if lead.status in (LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFYING):
                lead.status = LeadStatus.QUALIFIED

    def score_lead(self, lead_id: str) -> dict | None:
        """Re-score un lead y devuelve el resultado."""
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        self._auto_score(lead)
        return {
            "lead_id": lead.id,
            "total_score": lead.scoring.total,
            "temperature": lead.temperature.value,
            "breakdown": {
                "budget": lead.scoring.budget_score,
                "urgency": lead.scoring.urgency_score,
                "engagement": lead.scoring.engagement_score,
                "fit": lead.scoring.fit_score,
            },
            "qualification_progress": lead.qualification_progress,
            "matched_properties": len(lead.matched_properties),
            "status": lead.status.value,
        }

    # --- CALIFICACIÓN PROGRESIVA ---

    def get_next_questions(self, lead_id: str) -> list[dict]:
        """Devuelve las siguientes preguntas para calificar al lead."""
        lead = self.leads.get(lead_id)
        if not lead:
            return []

        answered_keys = {a.question_key for a in lead.qualification_answers}
        questions = []

        qualification_flow = [
            {
                "key": "operation_type",
                "text": "¿Busca comprar o alquilar?",
                "options": ["Comprar", "Alquilar"],
            },
            {
                "key": "property_type",
                "text": "¿Qué tipo de propiedad le interesa?",
                "options": ["Piso", "Casa/Chalet", "Local comercial", "Oficina", "Terreno", "Garaje", "Otro"],
            },
            {
                "key": "budget",
                "text": "¿Cuál es su presupuesto aproximado?",
                "options": ["< 150.000€", "150.000€ - 300.000€", "300.000€ - 500.000€", "500.000€ - 1.000.000€", "> 1.000.000€"],
            },
            {
                "key": "location",
                "text": "¿En qué zona o ciudad busca?",
                "options": [],
            },
            {
                "key": "urgency",
                "text": "¿En qué plazo necesita la propiedad?",
                "options": ["Inmediato (< 1 mes)", "1-3 meses", "3-6 meses", "Más de 6 meses"],
            },
            {
                "key": "bedrooms",
                "text": "¿Cuántas habitaciones necesita como mínimo?",
                "options": ["1", "2", "3", "4+"],
            },
            {
                "key": "requirements",
                "text": "¿Tiene algún requisito especial? (garaje, piscina, ascensor...)",
                "options": [],
            },
        ]

        for q in qualification_flow:
            if q["key"] not in answered_keys:
                questions.append(q)

        return questions

    def answer_question(
        self, lead_id: str, question_key: str, answer: str
    ) -> dict | None:
        """Registra la respuesta a una pregunta y actualiza el perfil del lead."""
        lead = self.leads.get(lead_id)
        if not lead:
            return None

        # Buscar la pregunta
        all_questions = self.get_next_questions(lead_id)
        question_text = ""
        for q in all_questions:
            if q["key"] == question_key:
                question_text = q["text"]
                break

        if not question_text:
            # Ya respondida o no existe
            question_text = question_key

        qa = QualificationAnswer(
            question_key=question_key,
            question_text=question_text,
            answer=answer,
        )
        lead.qualification_answers.append(qa)

        # Actualizar intereses según la respuesta
        self._update_interest_from_answer(lead, question_key, answer)

        # Re-score
        self._auto_score(lead)

        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.QUALIFYING

        return {
            "lead_id": lead.id,
            "question": question_key,
            "answer": answer,
            "new_score": lead.scoring.total,
            "qualification_progress": lead.qualification_progress,
            "status": lead.status.value,
        }

    def _update_interest_from_answer(self, lead: Lead, key: str, answer: str) -> None:
        """Actualiza el perfil de interés según la respuesta."""
        interest = lead.interest
        answer_lower = answer.lower().strip()

        if key == "operation_type":
            interest.is_rental = "alquil" in answer_lower

        elif key == "property_type":
            type_map = {
                "piso": ["piso", "dúplex", "ático", "estudio"],
                "casa": ["casa", "chalet"],
                "local": ["local_comercial"],
                "oficina": ["oficina"],
                "terreno": ["terreno_urbano", "terreno_rústico"],
                "garaje": ["garaje"],
            }
            for keyword, types in type_map.items():
                if keyword in answer_lower:
                    interest.property_types = types
                    break

        elif key == "budget":
            budget_ranges = {
                "< 150": (0, 150000),
                "150": (150000, 300000),
                "300": (300000, 500000),
                "500": (500000, 1000000),
                "> 1": (1000000, 10000000),
            }
            for prefix, (min_p, max_p) in budget_ranges.items():
                if prefix in answer_lower.replace(".", ""):
                    interest.min_price = min_p
                    interest.max_price = max_p
                    break

        elif key == "location":
            cities = [c.strip() for c in answer.split(",") if c.strip()]
            interest.preferred_cities = cities

        elif key == "urgency":
            if "inmediato" in answer_lower or "< 1" in answer_lower:
                interest.urgency = UrgencyLevel.IMMEDIATE
            elif "1-3" in answer_lower:
                interest.urgency = UrgencyLevel.SHORT_TERM
            elif "3-6" in answer_lower:
                interest.urgency = UrgencyLevel.MEDIUM_TERM
            elif "6" in answer_lower or "más" in answer_lower:
                interest.urgency = UrgencyLevel.LONG_TERM

        elif key == "bedrooms":
            try:
                num = int(answer.replace("+", ""))
                interest.min_bedrooms = num
            except ValueError:
                pass

        elif key == "requirements":
            reqs = [r.strip() for r in answer.split(",") if r.strip()]
            interest.specific_requirements = reqs
            for req in reqs:
                req_lower = req.lower()
                if "garaje" in req_lower or "parking" in req_lower:
                    interest.needs_garage = True
                if "ascensor" in req_lower:
                    interest.needs_elevator = True

    # --- MATCHING ---

    def _find_matching_properties(self, lead: Lead) -> list:
        """Encuentra propiedades que encajan con los intereses del lead."""
        interest = lead.interest
        matches = []

        for prop in self.db.get_available_properties():
            # Filtro alquiler/venta
            if interest.is_rental is not None and interest.is_rental != prop.is_rental:
                continue

            # Filtro tipo
            if interest.property_types:
                if prop.property_type.value not in interest.property_types:
                    continue

            # Filtro precio
            price = prop.monthly_rent if prop.is_rental else prop.price
            if price is None:
                continue
            if interest.min_price is not None and price < interest.min_price:
                continue
            if interest.max_price is not None and price > interest.max_price:
                continue

            # Filtro área
            if interest.min_area is not None and prop.area_m2 < interest.min_area:
                continue

            # Filtro ciudad
            if interest.preferred_cities:
                if prop.city.lower() not in [c.lower() for c in interest.preferred_cities]:
                    continue

            # Filtro habitaciones
            if interest.min_bedrooms is not None and hasattr(prop, "bedrooms"):
                if prop.bedrooms < interest.min_bedrooms:
                    continue

            # Filtro garaje
            if interest.needs_garage and hasattr(prop, "has_garage"):
                if not prop.has_garage:
                    continue

            matches.append(prop)

        return matches

    def get_matching_properties(self, lead_id: str) -> list[dict]:
        """Devuelve propiedades que encajan con el lead, formateadas."""
        lead = self.leads.get(lead_id)
        if not lead:
            return []

        matches = self._find_matching_properties(lead)
        return [
            {
                "id": p.id,
                "title": p.title,
                "type": p.property_type.value,
                "price": f"{p.price:,.0f}€" if not p.is_rental else f"{p.monthly_rent:,.0f}€/mes",
                "city": p.city,
                "area": f"{p.area_m2}m²",
                "bedrooms": getattr(p, "bedrooms", None),
            }
            for p in matches
        ]

    # --- CONVERSIÓN LEAD → CLIENTE ---

    def convert_to_client(self, lead_id: str) -> Client | None:
        """Convierte un lead calificado en cliente del CRM."""
        lead = self.leads.get(lead_id)
        if not lead:
            return None

        client_id = f"CLI-{uuid4().hex[:6].upper()}"
        interest = ClientInterest(
            property_types=lead.interest.property_types,
            min_price=lead.interest.min_price or 0,
            max_price=lead.interest.max_price or float("inf"),
            min_area=lead.interest.min_area or 0,
            preferred_cities=lead.interest.preferred_cities,
            min_bedrooms=lead.interest.min_bedrooms or 0,
            needs_garage=lead.interest.needs_garage or False,
            needs_elevator=lead.interest.needs_elevator or False,
            is_rental=lead.interest.is_rental or False,
            other_requirements=lead.interest.specific_requirements,
        )

        client = Client(
            id=client_id,
            name=lead.name,
            email=lead.email or "",
            phone=lead.phone or "",
            status=ClientStatus.ACTIVE,
            interest=interest,
            notes=[f"Convertido desde lead {lead.id}"]
            + [f"[{a.question_key}] {a.answer}" for a in lead.qualification_answers],
            assigned_agent=lead.assigned_agent,
        )

        self.db.add_client(client)
        lead.status = LeadStatus.CONVERTED
        lead.converted_client_id = client_id

        return client

    # --- ASIGNACIÓN DE AGENTES ---

    def assign_agent(self, lead_id: str, agent_name: str) -> Lead | None:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        lead.assigned_agent = agent_name
        return lead

    def auto_assign(self, lead_id: str, agents: list[dict]) -> Lead | None:
        """Asigna automáticamente según zona y carga de trabajo."""
        lead = self.leads.get(lead_id)
        if not lead or not agents:
            return None

        cities = lead.interest.preferred_cities
        best_agent = None
        best_score = -1

        for agent in agents:
            score = 0
            # Match por zona
            agent_zones = [z.lower() for z in agent.get("zones", [])]
            if cities and any(c.lower() in agent_zones for c in cities):
                score += 10
            # Menor carga = mejor
            active_leads = agent.get("active_leads", 0)
            score += max(0, 20 - active_leads)

            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent:
            lead.assigned_agent = best_agent["name"]

        return lead

    # --- ANALYTICS ---

    def get_lead_summary(self, lead_id: str) -> dict | None:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        return lead.to_dict()

    def get_pipeline(self) -> dict:
        """Dashboard del pipeline de leads."""
        all_leads = self.get_all_leads()
        by_status: dict[str, int] = {}
        by_source: dict[str, int] = {}
        by_temp: dict[str, int] = {}
        total_score = 0

        for lead in all_leads:
            by_status[lead.status.value] = by_status.get(lead.status.value, 0) + 1
            by_source[lead.source.value] = by_source.get(lead.source.value, 0) + 1
            by_temp[lead.temperature.value] = by_temp.get(lead.temperature.value, 0) + 1
            total_score += lead.scoring.total

        return {
            "total_leads": len(all_leads),
            "avg_score": round(total_score / len(all_leads), 1) if all_leads else 0,
            "by_status": by_status,
            "by_source": by_source,
            "by_temperature": by_temp,
            "hot_leads": [l.to_dict() for l in all_leads if l.temperature == LeadTemperature.HOT],
            "pending_follow_ups": [
                l.to_dict() for l in all_leads
                if l.next_follow_up and l.next_follow_up <= datetime.now()
            ],
        }

    def get_leads_by_temperature(self, temperature: str) -> list[dict]:
        try:
            temp = LeadTemperature(temperature)
        except ValueError:
            return []
        return [l.to_dict() for l in self.leads.values() if l.temperature == temp]

    def get_leads_by_status(self, status: str) -> list[dict]:
        try:
            s = LeadStatus(status)
        except ValueError:
            return []
        return [l.to_dict() for l in self.leads.values() if l.status == s]
