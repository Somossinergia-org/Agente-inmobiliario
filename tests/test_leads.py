"""Tests del sistema de leads."""

import pytest
from src.data.database import Database
from src.leads.manager import LeadManager
from src.models.lead import LeadStatus, LeadTemperature, UrgencyLevel


@pytest.fixture
def lead_mgr():
    db = Database(load_samples=True)
    return LeadManager(db)


def test_create_lead(lead_mgr):
    lead = lead_mgr.create_lead(
        name="Test User",
        source="whatsapp",
        phone="+34 600 000 000",
        email="test@email.com",
        initial_message="Hola, busco un piso",
    )
    assert lead.id.startswith("LEAD-")
    assert lead.name == "Test User"
    assert lead.source.value == "whatsapp"
    assert len(lead.conversation) == 1


def test_lead_scoring_initial(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    score = lead_mgr.score_lead(lead.id)
    assert score is not None
    assert score["total_score"] == lead.scoring.total
    assert "breakdown" in score


def test_answer_question_updates_interest(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")

    # Responder tipo de operación
    result = lead_mgr.answer_question(lead.id, "operation_type", "Comprar")
    assert result is not None
    assert lead.interest.is_rental is False

    # Responder presupuesto
    result = lead_mgr.answer_question(lead.id, "budget", "300.000€ - 500.000€")
    assert lead.interest.min_price == 300000
    assert lead.interest.max_price == 500000


def test_answer_question_location(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    lead_mgr.answer_question(lead.id, "location", "Madrid, Barcelona")
    assert "Madrid" in lead.interest.preferred_cities
    assert "Barcelona" in lead.interest.preferred_cities


def test_answer_question_urgency(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    lead_mgr.answer_question(lead.id, "urgency", "Inmediato (< 1 mes)")
    assert lead.interest.urgency == UrgencyLevel.IMMEDIATE


def test_lead_qualification_progress(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    assert lead.qualification_progress == 0.0

    lead_mgr.answer_question(lead.id, "operation_type", "Comprar")
    lead_mgr.answer_question(lead.id, "property_type", "Piso")
    lead_mgr.answer_question(lead.id, "location", "Madrid")
    lead_mgr.answer_question(lead.id, "budget", "300.000€ - 500.000€")
    lead_mgr.answer_question(lead.id, "urgency", "1-3 meses")

    assert lead.qualification_progress == 100.0


def test_get_next_questions(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    questions = lead_mgr.get_next_questions(lead.id)
    assert len(questions) == 7  # Todas las preguntas

    lead_mgr.answer_question(lead.id, "operation_type", "Comprar")
    questions = lead_mgr.get_next_questions(lead.id)
    assert len(questions) == 6


def test_matching_properties(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    lead_mgr.answer_question(lead.id, "operation_type", "Comprar")
    lead_mgr.answer_question(lead.id, "property_type", "Piso")
    lead_mgr.answer_question(lead.id, "location", "Madrid")
    lead_mgr.answer_question(lead.id, "budget", "150.000€ - 300.000€")

    matches = lead_mgr.get_matching_properties(lead.id)
    assert isinstance(matches, list)
    for m in matches:
        assert "id" in m
        assert "title" in m
        assert "price" in m


def test_convert_to_client(lead_mgr):
    lead = lead_mgr.create_lead(name="Convert Test", source="web", email="convert@test.com")
    lead_mgr.answer_question(lead.id, "operation_type", "Comprar")
    lead_mgr.answer_question(lead.id, "property_type", "Casa")
    lead_mgr.answer_question(lead.id, "budget", "300.000€ - 500.000€")

    client = lead_mgr.convert_to_client(lead.id)
    assert client is not None
    assert client.name == "Convert Test"
    assert lead.status == LeadStatus.CONVERTED
    assert lead.converted_client_id == client.id


def test_assign_agent(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    result = lead_mgr.assign_agent(lead.id, "Ana López")
    assert result is not None
    assert lead.assigned_agent == "Ana López"


def test_auto_assign(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    lead_mgr.answer_question(lead.id, "location", "Madrid")

    agents = [
        {"name": "Agent A", "zones": ["Barcelona"], "active_leads": 5},
        {"name": "Agent B", "zones": ["Madrid", "Toledo"], "active_leads": 2},
    ]
    result = lead_mgr.auto_assign(lead.id, agents)
    assert result is not None
    assert lead.assigned_agent == "Agent B"  # Madrid match + fewer leads


def test_pipeline(lead_mgr):
    lead_mgr.create_lead(name="Lead 1", source="whatsapp")
    lead_mgr.create_lead(name="Lead 2", source="idealista")
    lead_mgr.create_lead(name="Lead 3", source="formulario_web")

    pipeline = lead_mgr.get_pipeline()
    assert pipeline["total_leads"] == 3
    assert "by_status" in pipeline
    assert "by_source" in pipeline
    assert "by_temperature" in pipeline


def test_leads_by_temperature(lead_mgr):
    lead_mgr.create_lead(name="Cold Lead", source="web")
    cold = lead_mgr.get_leads_by_temperature("frio")
    assert len(cold) >= 1


def test_leads_by_status(lead_mgr):
    lead_mgr.create_lead(name="New Lead", source="web")
    new_leads = lead_mgr.get_leads_by_status("nuevo")
    assert len(new_leads) >= 1


def test_update_lead_status(lead_mgr):
    lead = lead_mgr.create_lead(name="Test", source="web")
    result = lead_mgr.update_lead_status(lead.id, "contactado")
    assert result is not None
    assert result.status == LeadStatus.CONTACTED
