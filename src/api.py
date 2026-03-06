"""API REST del Agente Inmobiliario Inteligente.

Endpoints para gestión de leads, propiedades, CRM, estimaciones y webhooks.
Documentación interactiva en /docs (Swagger UI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent.orchestrator import RealEstateAgent
from src.leads.manager import LeadManager
from src.conversation.engine import ConversationEngine
from src.webhooks.manager import WebhookManager

# --- App ---

app = FastAPI(
    title="Agente Inmobiliario Inteligente API",
    description=(
        "API para gestión inteligente de leads inmobiliarios con scoring automático, "
        "calificación progresiva, matching de propiedades, CRM y estimación de precios. "
        "Diseñada para inmobiliarias que quieren automatizar la captación y calificación de leads."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Servicios compartidos ---

agent = RealEstateAgent()
lead_manager = LeadManager(agent.db)
conversation_engine = ConversationEngine()
webhook_manager = WebhookManager()


# ==========================================
# SCHEMAS (Pydantic)
# ==========================================

class LeadCreate(BaseModel):
    name: str = Field(..., description="Nombre del lead", examples=["Juan Pérez"])
    phone: str | None = Field(None, description="Teléfono", examples=["+34 612 345 678"])
    email: str | None = Field(None, description="Email", examples=["juan@email.com"])
    source: str = Field("otro", description="Canal de origen", examples=["whatsapp", "idealista", "formulario_web"])
    initial_message: str = Field("", description="Primer mensaje del lead")
    channel: str = Field("web", description="Canal de comunicación")


class MessageSend(BaseModel):
    message: str = Field(..., description="Mensaje del lead", examples=["Hola, busco un piso en Madrid"])
    channel: str = Field("web", description="Canal", examples=["whatsapp", "web", "email"])


class QuestionAnswer(BaseModel):
    question_key: str = Field(..., description="Clave de la pregunta", examples=["budget"])
    answer: str = Field(..., description="Respuesta del lead", examples=["300.000€ - 500.000€"])


class LeadStatusUpdate(BaseModel):
    status: str = Field(..., description="Nuevo estado", examples=["calificado", "visita_programada"])


class AgentAssign(BaseModel):
    agent_name: str = Field(..., description="Nombre del agente", examples=["Ana López"])


class AutoAssignRequest(BaseModel):
    agents: list[dict] = Field(..., description="Lista de agentes disponibles")


class SearchFiltersRequest(BaseModel):
    property_types: list[str] = Field(default_factory=list)
    min_price: float = 0
    max_price: float = Field(default=float("inf"))
    cities: list[str] = Field(default_factory=list)
    min_bedrooms: int = 0
    is_rental: bool | None = None
    keyword: str = ""
    sort_by: str = "price"


class ClientCreate(BaseModel):
    name: str
    email: str
    phone: str
    property_types: list[str] = Field(default_factory=list)
    min_price: float = 0
    max_price: float = Field(default=float("inf"))
    preferred_cities: list[str] = Field(default_factory=list)
    min_bedrooms: int = 0
    is_rental: bool = False


class VisitSchedule(BaseModel):
    client_id: str
    property_id: str
    visit_date: str = Field(..., examples=["2026-03-15 10:00"])
    notes: str = ""


class FavoriteAdd(BaseModel):
    client_id: str
    property_id: str
    notes: str = ""


class PriceEstimateRequest(BaseModel):
    city: str = Field(..., examples=["Madrid"])
    property_type: str = Field(..., examples=["piso"])
    area_m2: float = Field(..., examples=[90])
    bedrooms: int = 0
    features: list[str] = Field(default_factory=list)


class WebhookRegister(BaseModel):
    url: str = Field(..., examples=["https://mi-inmobiliaria.com/webhooks"])
    events: list[str] = Field(..., examples=[["lead.created", "lead.qualified", "lead.hot"]])
    secret: str = ""
    description: str = ""


# ==========================================
# ENDPOINTS: LEADS (el core del producto)
# ==========================================

@app.post("/api/v1/leads", tags=["Leads"], summary="Crear nuevo lead")
def create_lead(data: LeadCreate):
    """Crea un nuevo lead y dispara scoring automático + webhook."""
    lead = lead_manager.create_lead(
        name=data.name,
        source=data.source,
        phone=data.phone,
        email=data.email,
        initial_message=data.initial_message,
        channel=data.channel,
    )

    # Mensaje de bienvenida automático
    welcome = conversation_engine.get_welcome_message(lead)
    lead.add_message("agent", welcome, data.channel)

    # Webhook
    webhook_manager.trigger_sync("lead.created", lead.to_dict())

    return {
        "lead": lead.to_dict(),
        "welcome_message": welcome,
    }


@app.get("/api/v1/leads", tags=["Leads"], summary="Listar todos los leads")
def list_leads(
    status: str | None = Query(None, description="Filtrar por estado"),
    temperature: str | None = Query(None, description="Filtrar por temperatura (caliente, tibio, frio)"),
    source: str | None = Query(None, description="Filtrar por fuente"),
):
    """Lista leads con filtros opcionales."""
    if status:
        return lead_manager.get_leads_by_status(status)
    if temperature:
        return lead_manager.get_leads_by_temperature(temperature)
    return [l.to_dict() for l in lead_manager.get_all_leads()]


@app.get("/api/v1/leads/pipeline", tags=["Leads"], summary="Pipeline de leads")
def get_pipeline():
    """Dashboard del pipeline: estadísticas, leads calientes, seguimientos pendientes."""
    return lead_manager.get_pipeline()


@app.get("/api/v1/leads/{lead_id}", tags=["Leads"], summary="Detalle de un lead")
def get_lead(lead_id: str):
    result = lead_manager.get_lead_summary(lead_id)
    if not result:
        raise HTTPException(404, "Lead no encontrado")
    return result


@app.get("/api/v1/leads/{lead_id}/score", tags=["Leads"], summary="Scoring del lead")
def get_lead_score(lead_id: str):
    """Obtiene el scoring detallado del lead con breakdown."""
    result = lead_manager.score_lead(lead_id)
    if not result:
        raise HTTPException(404, "Lead no encontrado")
    return result


@app.put("/api/v1/leads/{lead_id}/status", tags=["Leads"], summary="Cambiar estado del lead")
def update_lead_status(lead_id: str, data: LeadStatusUpdate):
    lead = lead_manager.update_lead_status(lead_id, data.status)
    if not lead:
        raise HTTPException(404, "Lead no encontrado o estado inválido")
    return lead.to_dict()


@app.put("/api/v1/leads/{lead_id}/assign", tags=["Leads"], summary="Asignar agente al lead")
def assign_agent(lead_id: str, data: AgentAssign):
    lead = lead_manager.assign_agent(lead_id, data.agent_name)
    if not lead:
        raise HTTPException(404, "Lead no encontrado")
    webhook_manager.trigger_sync("lead.assigned", lead.to_dict())
    return lead.to_dict()


@app.post("/api/v1/leads/{lead_id}/auto-assign", tags=["Leads"], summary="Auto-asignar agente")
def auto_assign_agent(lead_id: str, data: AutoAssignRequest):
    """Asigna automáticamente el mejor agente según zona y carga de trabajo."""
    lead = lead_manager.auto_assign(lead_id, data.agents)
    if not lead:
        raise HTTPException(404, "Lead no encontrado")
    webhook_manager.trigger_sync("lead.assigned", lead.to_dict())
    return lead.to_dict()


# ==========================================
# ENDPOINTS: CONVERSACIÓN
# ==========================================

@app.post("/api/v1/leads/{lead_id}/messages", tags=["Conversación"], summary="Enviar mensaje del lead")
def send_message(lead_id: str, data: MessageSend):
    """Procesa un mensaje del lead, genera respuesta automática y actualiza scoring."""
    lead = lead_manager.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead no encontrado")

    # Registrar mensaje del lead
    lead.add_message("lead", data.message, data.channel)

    # Obtener propiedades matching
    matches = lead_manager.get_matching_properties(lead_id)

    # Procesar con motor de conversación
    response = conversation_engine.process_message(data.message, lead, matches)

    # Registrar respuesta del agente
    lead.add_message("agent", response.message, data.channel)

    # Re-score
    lead_manager.score_lead(lead_id)

    # Webhook si hay mensaje
    webhook_manager.trigger_sync("message.received", {
        "lead_id": lead.id,
        "message": data.message,
        "response": response.message,
        "score": lead.scoring.total,
    })

    # Webhook si se pone caliente
    if lead.temperature.value == "caliente":
        webhook_manager.trigger_sync("lead.hot", lead.to_dict())

    return {
        "response": response.message,
        "intent": response.intent,
        "confidence": response.confidence,
        "lead_score": lead.scoring.total,
        "temperature": lead.temperature.value,
        "matched_properties": response.matched_properties_count,
        "qualification_progress": lead.qualification_progress,
    }


@app.get("/api/v1/leads/{lead_id}/messages", tags=["Conversación"], summary="Historial de mensajes")
def get_messages(lead_id: str):
    lead = lead_manager.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead no encontrado")
    return [
        {
            "role": m.role,
            "content": m.content,
            "channel": m.channel,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in lead.conversation
    ]


@app.get("/api/v1/leads/{lead_id}/questions", tags=["Conversación"], summary="Preguntas pendientes")
def get_pending_questions(lead_id: str):
    """Obtiene las preguntas de calificación que faltan por responder."""
    questions = lead_manager.get_next_questions(lead_id)
    if questions is None:
        raise HTTPException(404, "Lead no encontrado")
    return questions


@app.post("/api/v1/leads/{lead_id}/questions", tags=["Conversación"], summary="Responder pregunta de calificación")
def answer_question(lead_id: str, data: QuestionAnswer):
    """Responde una pregunta de calificación y actualiza scoring."""
    result = lead_manager.answer_question(lead_id, data.question_key, data.answer)
    if not result:
        raise HTTPException(404, "Lead no encontrado o pregunta ya respondida")

    # Check si se calificó
    lead = lead_manager.get_lead(lead_id)
    if lead and lead.is_qualified:
        webhook_manager.trigger_sync("lead.qualified", lead.to_dict())

    return result


# ==========================================
# ENDPOINTS: MATCHING
# ==========================================

@app.get("/api/v1/leads/{lead_id}/matches", tags=["Matching"], summary="Propiedades que encajan con el lead")
def get_lead_matches(lead_id: str):
    """Devuelve propiedades que encajan con los intereses del lead."""
    matches = lead_manager.get_matching_properties(lead_id)
    if matches is None:
        raise HTTPException(404, "Lead no encontrado")
    return {"lead_id": lead_id, "count": len(matches), "properties": matches}


@app.post("/api/v1/leads/{lead_id}/convert", tags=["Leads"], summary="Convertir lead en cliente CRM")
def convert_lead(lead_id: str):
    """Convierte un lead calificado en cliente del CRM."""
    client = lead_manager.convert_to_client(lead_id)
    if not client:
        raise HTTPException(404, "Lead no encontrado")
    webhook_manager.trigger_sync("lead.converted", {
        "lead_id": lead_id,
        "client_id": client.id,
        "name": client.name,
    })
    return {
        "message": f"Lead convertido a cliente {client.id}",
        "client_id": client.id,
        "client_name": client.name,
    }


# ==========================================
# ENDPOINTS: PROPIEDADES
# ==========================================

@app.get("/api/v1/properties", tags=["Propiedades"], summary="Buscar propiedades")
def search_properties(
    q: str | None = Query(None, description="Búsqueda rápida por texto"),
    city: str | None = None,
    property_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_bedrooms: int | None = None,
    is_rental: bool | None = None,
    sort_by: str = "price",
):
    """Búsqueda avanzada de propiedades con filtros."""
    if q:
        return agent.quick_search(q)

    from src.search.engine import SearchFilters
    filters = SearchFilters(sort_by=sort_by)
    if city:
        filters.cities = [city]
    if property_type:
        filters.property_types = [property_type]
    if min_price is not None:
        filters.min_price = min_price
    if max_price is not None:
        filters.max_price = max_price
    if min_bedrooms is not None:
        filters.min_bedrooms = min_bedrooms
    if is_rental is not None:
        filters.is_rental = is_rental

    return agent.search_properties(filters)


@app.get("/api/v1/properties/{property_id}", tags=["Propiedades"], summary="Detalle de propiedad")
def get_property(property_id: str):
    result = agent.get_property_detail(property_id)
    if not result:
        raise HTTPException(404, "Propiedad no encontrada")
    return result


# ==========================================
# ENDPOINTS: CRM
# ==========================================

@app.get("/api/v1/clients", tags=["CRM"], summary="Listar clientes")
def list_clients():
    return agent.list_clients()


@app.post("/api/v1/clients", tags=["CRM"], summary="Crear cliente")
def create_client(data: ClientCreate):
    from src.models.client import ClientInterest
    interest = ClientInterest(
        property_types=data.property_types,
        min_price=data.min_price,
        max_price=data.max_price,
        preferred_cities=data.preferred_cities,
        min_bedrooms=data.min_bedrooms,
        is_rental=data.is_rental,
    )
    client = agent.create_client(data.name, data.email, data.phone, interest)
    return {"id": client.id, "name": client.name, "status": client.status.value}


@app.get("/api/v1/clients/{client_id}", tags=["CRM"], summary="Detalle de cliente")
def get_client(client_id: str):
    result = agent.get_client_info(client_id)
    if not result:
        raise HTTPException(404, "Cliente no encontrado")
    return result


@app.get("/api/v1/clients/{client_id}/matches", tags=["CRM"], summary="Propiedades para cliente")
def get_client_matches(client_id: str):
    return agent.find_properties_for_client(client_id)


@app.post("/api/v1/visits", tags=["CRM"], summary="Programar visita")
def schedule_visit(data: VisitSchedule):
    result = agent.schedule_visit(data.client_id, data.property_id, data.visit_date, data.notes)
    if not result:
        raise HTTPException(404, "Cliente o propiedad no encontrados")
    webhook_manager.trigger_sync("visit.scheduled", {
        "client_id": data.client_id,
        "property_id": data.property_id,
        "date": data.visit_date,
    })
    return {"visit_id": result.id, "date": data.visit_date, "status": "programada"}


@app.post("/api/v1/favorites", tags=["CRM"], summary="Añadir favorito")
def add_favorite(data: FavoriteAdd):
    result = agent.add_favorite(data.client_id, data.property_id, data.notes)
    if not result:
        raise HTTPException(400, "No se pudo añadir (ya existe o datos inválidos)")
    return {"status": "ok", "property_id": data.property_id}


@app.get("/api/v1/clients/{client_id}/favorites", tags=["CRM"], summary="Favoritos del cliente")
def get_favorites(client_id: str):
    return agent.get_favorites(client_id)


# ==========================================
# ENDPOINTS: ESTIMACIÓN
# ==========================================

@app.post("/api/v1/estimate", tags=["Estimación"], summary="Estimar precio")
def estimate_price(data: PriceEstimateRequest):
    """Estima el precio de una propiedad basándose en comparables del mercado."""
    est = agent.estimate_price(
        city=data.city,
        property_type=data.property_type,
        area_m2=data.area_m2,
        bedrooms=data.bedrooms,
        features=data.features or None,
    )
    return {
        "estimated_price": est.estimated_price,
        "price_per_m2": est.price_per_m2,
        "confidence": est.confidence,
        "comparable_count": est.comparable_count,
        "price_range": {"min": est.min_price, "max": est.max_price},
        "comparables": est.comparables,
    }


@app.get("/api/v1/properties/{property_id}/comparative", tags=["Estimación"], summary="Comparativa de mercado")
def get_comparative(property_id: str):
    result = agent.get_comparative(property_id)
    if not result:
        raise HTTPException(404, "Propiedad no encontrada")
    return {
        "property_id": property_id,
        "avg_price_m2_zone": result.avg_price_m2_zone,
        "price_position": result.price_position,
        "price_difference_pct": result.price_difference_pct,
        "market_summary": result.market_summary,
        "similar_properties": result.similar_properties,
    }


@app.get("/api/v1/zones/{city}/stats", tags=["Estimación"], summary="Estadísticas por zona")
def get_zone_stats(city: str):
    return agent.get_zone_stats(city)


# ==========================================
# ENDPOINTS: WEBHOOKS
# ==========================================

@app.post("/api/v1/webhooks", tags=["Webhooks"], summary="Registrar webhook")
def register_webhook(data: WebhookRegister):
    """Registra un webhook para recibir notificaciones de eventos."""
    wh = webhook_manager.register_webhook(
        url=data.url,
        events=data.events,
        secret=data.secret,
        description=data.description,
    )
    return {
        "id": wh.id,
        "url": wh.url,
        "events": [e.value for e in wh.events],
        "active": wh.active,
    }


@app.get("/api/v1/webhooks", tags=["Webhooks"], summary="Listar webhooks")
def list_webhooks():
    return webhook_manager.list_webhooks()


@app.delete("/api/v1/webhooks/{webhook_id}", tags=["Webhooks"], summary="Eliminar webhook")
def delete_webhook(webhook_id: str):
    if not webhook_manager.unregister_webhook(webhook_id):
        raise HTTPException(404, "Webhook no encontrado")
    return {"status": "deleted"}


@app.get("/api/v1/webhooks/deliveries", tags=["Webhooks"], summary="Historial de envíos")
def get_webhook_deliveries(webhook_id: str | None = None, limit: int = 50):
    return webhook_manager.get_deliveries(webhook_id, limit)


# ==========================================
# ENDPOINTS: DASHBOARD
# ==========================================

@app.get("/api/v1/dashboard", tags=["Dashboard"], summary="Dashboard general")
def get_dashboard():
    """Dashboard completo con estadísticas de propiedades, clientes y leads."""
    prop_dashboard = agent.get_dashboard()
    lead_pipeline = lead_manager.get_pipeline()

    return {
        "properties": prop_dashboard,
        "leads": lead_pipeline,
        "webhooks_active": len([w for w in webhook_manager.webhooks.values() if w.active]),
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health", tags=["Sistema"], summary="Health check")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "properties": agent.db.total_properties,
        "clients": agent.db.total_clients,
        "leads": len(lead_manager.leads),
    }


@app.get("/", tags=["Sistema"])
def root():
    return {
        "name": "Agente Inmobiliario Inteligente API",
        "version": "2.0.0",
        "docs": "/docs",
        "description": "API para gestión inteligente de leads inmobiliarios",
    }
