"""Tests de la API REST."""

import pytest
from fastapi.testclient import TestClient
from src.api import app


@pytest.fixture
def client():
    return TestClient(app)


# --- Health & Root ---

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["properties"] == 55


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Agente Inmobiliario" in r.text


# --- Leads ---

def test_create_lead(client):
    r = client.post("/api/v1/leads", json={
        "name": "Test Lead",
        "phone": "+34 600 000 000",
        "source": "whatsapp",
        "initial_message": "Hola, busco un piso en Madrid",
    })
    assert r.status_code == 200
    data = r.json()
    assert "lead" in data
    assert "welcome_message" in data
    assert data["lead"]["name"] == "Test Lead"


def test_list_leads(client):
    client.post("/api/v1/leads", json={"name": "Lead A"})
    r = client.get("/api/v1/leads")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_lead(client):
    r = client.post("/api/v1/leads", json={"name": "Get Me"})
    lead_id = r.json()["lead"]["id"]
    r = client.get(f"/api/v1/leads/{lead_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Get Me"


def test_lead_not_found(client):
    r = client.get("/api/v1/leads/FAKE-ID")
    assert r.status_code == 404


def test_lead_score(client):
    r = client.post("/api/v1/leads", json={"name": "Score Me"})
    lead_id = r.json()["lead"]["id"]
    r = client.get(f"/api/v1/leads/{lead_id}/score")
    assert r.status_code == 200
    assert "total_score" in r.json()
    assert "breakdown" in r.json()


def test_pipeline(client):
    client.post("/api/v1/leads", json={"name": "P1", "source": "whatsapp"})
    client.post("/api/v1/leads", json={"name": "P2", "source": "idealista"})
    r = client.get("/api/v1/leads/pipeline")
    assert r.status_code == 200
    assert "total_leads" in r.json()


# --- Conversación ---

def test_send_message(client):
    r = client.post("/api/v1/leads", json={"name": "Chat Lead"})
    lead_id = r.json()["lead"]["id"]
    r = client.post(f"/api/v1/leads/{lead_id}/messages", json={
        "message": "Hola, quiero comprar un piso en Madrid",
        "channel": "whatsapp",
    })
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "lead_score" in data
    assert "temperature" in data


def test_get_messages(client):
    r = client.post("/api/v1/leads", json={"name": "Msg Lead"})
    lead_id = r.json()["lead"]["id"]
    client.post(f"/api/v1/leads/{lead_id}/messages", json={"message": "Hola"})
    r = client.get(f"/api/v1/leads/{lead_id}/messages")
    assert r.status_code == 200
    assert len(r.json()) >= 2  # welcome + lead msg + response


def test_answer_qualification_question(client):
    r = client.post("/api/v1/leads", json={"name": "Qualify Me"})
    lead_id = r.json()["lead"]["id"]

    r = client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "operation_type",
        "answer": "Comprar",
    })
    assert r.status_code == 200
    assert r.json()["question"] == "operation_type"


def test_get_pending_questions(client):
    r = client.post("/api/v1/leads", json={"name": "Questions Lead"})
    lead_id = r.json()["lead"]["id"]
    r = client.get(f"/api/v1/leads/{lead_id}/questions")
    assert r.status_code == 200
    assert len(r.json()) == 7


# --- Matching ---

def test_lead_matches(client):
    r = client.post("/api/v1/leads", json={"name": "Match Lead"})
    lead_id = r.json()["lead"]["id"]

    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "operation_type", "answer": "Comprar"})
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "property_type", "answer": "Piso"})
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "budget", "answer": "150.000€ - 300.000€"})

    r = client.get(f"/api/v1/leads/{lead_id}/matches")
    assert r.status_code == 200
    assert "properties" in r.json()


def test_convert_lead(client):
    r = client.post("/api/v1/leads", json={"name": "Convert Me", "email": "conv@test.com"})
    lead_id = r.json()["lead"]["id"]
    r = client.post(f"/api/v1/leads/{lead_id}/convert")
    assert r.status_code == 200
    assert "client_id" in r.json()


# --- Propiedades ---

def test_search_properties(client):
    r = client.get("/api/v1/properties?q=Madrid")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_properties_with_filters(client):
    r = client.get("/api/v1/properties?city=Madrid&max_price=500000")
    assert r.status_code == 200


def test_get_property(client):
    r = client.get("/api/v1/properties/RES-001")
    assert r.status_code == 200
    assert r.json()["id"] == "RES-001"


def test_property_not_found(client):
    r = client.get("/api/v1/properties/FAKE")
    assert r.status_code == 404


# --- CRM ---

def test_list_clients(client):
    r = client.get("/api/v1/clients")
    assert r.status_code == 200
    assert len(r.json()) >= 8  # Sample clients


def test_create_client(client):
    r = client.post("/api/v1/clients", json={
        "name": "API Client",
        "email": "api@test.com",
        "phone": "+34 600 000 000",
        "property_types": ["piso"],
        "preferred_cities": ["Madrid"],
    })
    assert r.status_code == 200
    assert r.json()["name"] == "API Client"


def test_get_client(client):
    r = client.get("/api/v1/clients/CLI-001")
    assert r.status_code == 200
    assert r.json()["name"] == "María García López"


def test_schedule_visit(client):
    r = client.post("/api/v1/visits", json={
        "client_id": "CLI-001",
        "property_id": "RES-001",
        "visit_date": "2026-03-15 10:00",
        "notes": "Test visit",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "programada"


# --- Estimación ---

def test_estimate_price(client):
    r = client.post("/api/v1/estimate", json={
        "city": "Madrid",
        "property_type": "piso",
        "area_m2": 90,
        "bedrooms": 3,
    })
    assert r.status_code == 200
    assert "estimated_price" in r.json()
    assert "confidence" in r.json()


def test_comparative(client):
    r = client.get("/api/v1/properties/RES-001/comparative")
    assert r.status_code == 200
    assert "market_summary" in r.json()


def test_zone_stats(client):
    r = client.get("/api/v1/zones/Madrid/stats")
    assert r.status_code == 200
    assert r.json()["city"] == "Madrid"


# --- Webhooks ---

def test_register_webhook(client):
    r = client.post("/api/v1/webhooks", json={
        "url": "https://example.com/webhook",
        "events": ["lead.created", "lead.qualified"],
        "description": "Test webhook",
    })
    assert r.status_code == 200
    assert r.json()["active"] is True


def test_list_webhooks(client):
    client.post("/api/v1/webhooks", json={
        "url": "https://example.com/wh",
        "events": ["lead.created"],
    })
    r = client.get("/api/v1/webhooks")
    assert r.status_code == 200


def test_delete_webhook(client):
    r = client.post("/api/v1/webhooks", json={
        "url": "https://example.com/del",
        "events": ["lead.created"],
    })
    wh_id = r.json()["id"]
    r = client.delete(f"/api/v1/webhooks/{wh_id}")
    assert r.status_code == 200


# --- Dashboard ---

def test_dashboard(client):
    r = client.get("/api/v1/dashboard")
    assert r.status_code == 200
    assert "properties" in r.json()
    assert "leads" in r.json()


# --- Flujo completo ---

def test_full_lead_flow(client):
    """Test del flujo completo: crear lead → conversar → calificar → matching → convertir."""
    # 1. Crear lead
    r = client.post("/api/v1/leads", json={
        "name": "Flow Test",
        "phone": "+34 611 111 111",
        "email": "flow@test.com",
        "source": "whatsapp",
        "initial_message": "Hola",
    })
    lead_id = r.json()["lead"]["id"]

    # 2. Conversar
    r = client.post(f"/api/v1/leads/{lead_id}/messages", json={
        "message": "Quiero comprar un piso en Madrid",
    })
    assert r.json()["lead_score"] >= 0

    # 3. Calificar
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "operation_type", "answer": "Comprar"})
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "property_type", "answer": "Piso"})
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "location", "answer": "Madrid"})
    client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "budget", "answer": "150.000€ - 300.000€"})
    r = client.post(f"/api/v1/leads/{lead_id}/questions", json={
        "question_key": "urgency", "answer": "1-3 meses"})

    # 4. Matching
    r = client.get(f"/api/v1/leads/{lead_id}/matches")
    assert r.json()["count"] >= 0

    # 5. Score
    r = client.get(f"/api/v1/leads/{lead_id}/score")
    assert r.json()["total_score"] > 0
    assert r.json()["qualification_progress"] == 100.0

    # 6. Convertir
    r = client.post(f"/api/v1/leads/{lead_id}/convert")
    assert r.status_code == 200
    assert "client_id" in r.json()
