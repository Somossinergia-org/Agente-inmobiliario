"""Tests del motor de conversación."""

import pytest
from src.conversation.engine import ConversationEngine
from src.models.lead import Lead, LeadSource, LeadInterest, UrgencyLevel


@pytest.fixture
def engine():
    return ConversationEngine()


@pytest.fixture
def new_lead():
    return Lead(id="LEAD-TEST", name="Test User", source=LeadSource.WHATSAPP)


def test_greeting_response(engine, new_lead):
    response = engine.process_message("Hola, buenos días", new_lead)
    assert response.message
    assert response.intent == "greeting"
    assert response.confidence > 0


def test_buy_intent(engine, new_lead):
    response = engine.process_message("Quiero comprar una casa", new_lead)
    assert "is_rental" in response.extracted_data
    assert response.extracted_data["is_rental"] is False


def test_rent_intent(engine, new_lead):
    response = engine.process_message("Busco alquilar un piso", new_lead)
    assert "is_rental" in response.extracted_data
    assert response.extracted_data["is_rental"] is True


def test_apartment_intent(engine, new_lead):
    response = engine.process_message("Me interesa un piso", new_lead)
    assert "property_types" in response.extracted_data
    assert "piso" in response.extracted_data["property_types"]


def test_house_intent(engine, new_lead):
    response = engine.process_message("Busco un chalet", new_lead)
    assert "property_types" in response.extracted_data
    assert "chalet" in response.extracted_data["property_types"]


def test_commercial_intent(engine, new_lead):
    response = engine.process_message("Necesito una oficina", new_lead)
    assert "property_types" in response.extracted_data
    assert "oficina" in response.extracted_data["property_types"]


def test_urgent_intent(engine, new_lead):
    response = engine.process_message("Lo necesito urgente", new_lead)
    assert "urgency" in response.extracted_data


def test_contextual_response_asks_next_question(engine, new_lead):
    response = engine.process_message("No sé muy bien qué busco", new_lead)
    assert response.message
    assert response.intent in ("qualification", "unknown")


def test_welcome_message_whatsapp(engine):
    lead = Lead(id="L1", name="María", source=LeadSource.WHATSAPP)
    msg = engine.get_welcome_message(lead)
    assert "María" in msg
    assert "WhatsApp" in msg


def test_welcome_message_idealista(engine):
    lead = Lead(id="L1", name="Carlos", source=LeadSource.IDEALISTA)
    msg = engine.get_welcome_message(lead)
    assert "Carlos" in msg
    assert "Idealista" in msg


def test_welcome_message_web(engine):
    lead = Lead(id="L1", name="Ana", source=LeadSource.WEB_FORM)
    msg = engine.get_welcome_message(lead)
    assert "Ana" in msg


def test_property_suggestions_included(engine, new_lead):
    props = [
        {"title": "Piso en Madrid", "price": "200,000€", "area": "80m²", "bedrooms": 3},
        {"title": "Casa en Getafe", "price": "300,000€", "area": "140m²", "bedrooms": 3},
    ]
    response = engine.process_message("Quiero comprar", new_lead, matched_properties=props)
    assert "Propiedades recomendadas" in response.message
    assert response.matched_properties_count == 2


def test_thanks_response(engine, new_lead):
    response = engine.process_message("gracias", new_lead)
    assert response.message
    assert response.intent == "thanks"
