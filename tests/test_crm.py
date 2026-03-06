"""Tests para el CRM."""

from datetime import datetime

from src.data.database import Database
from src.crm.manager import CRMManager
from src.models.client import ClientInterest


def setup_crm():
    db = Database()
    return CRMManager(db), db


def test_create_client():
    crm, _ = setup_crm()
    client = crm.create_client("Test User", "test@test.com", "+34 600 000 000")
    assert client.id.startswith("CLI-")
    assert client.name == "Test User"


def test_get_client_summary():
    crm, _ = setup_crm()
    summary = crm.get_client_summary("CLI-001")
    assert summary is not None
    assert summary["name"] == "María García López"


def test_schedule_visit():
    crm, _ = setup_crm()
    visit = crm.schedule_visit("CLI-001", "RES-001", datetime.now(), "Visita de prueba")
    assert visit is not None
    assert visit.client_id == "CLI-001"
    assert visit.property_id == "RES-001"


def test_get_client_visits():
    crm, _ = setup_crm()
    crm.schedule_visit("CLI-001", "RES-001", datetime.now(), "Test")
    visits = crm.get_client_visits("CLI-001")
    assert len(visits) >= 1


def test_add_favorite():
    crm, _ = setup_crm()
    fav = crm.add_favorite("CLI-001", "RES-001", "Me gusta mucho")
    assert fav is not None
    assert fav.property_id == "RES-001"


def test_duplicate_favorite():
    crm, _ = setup_crm()
    crm.add_favorite("CLI-001", "RES-001")
    fav2 = crm.add_favorite("CLI-001", "RES-001")
    assert fav2 is None


def test_remove_favorite():
    crm, _ = setup_crm()
    crm.add_favorite("CLI-001", "RES-001")
    assert crm.remove_favorite("CLI-001", "RES-001")


def test_get_favorites():
    crm, _ = setup_crm()
    crm.add_favorite("CLI-001", "RES-001")
    crm.add_favorite("CLI-001", "RES-003")
    favs = crm.get_client_favorites("CLI-001")
    assert len(favs) == 2


def test_find_matching_properties():
    crm, _ = setup_crm()
    # CLI-001 busca pisos/dúplex en Madrid, 200k-400k, 3+ hab
    matches = crm.find_matching_properties("CLI-001")
    assert len(matches) > 0
    for m in matches:
        assert m.price >= 200000
        assert m.price <= 400000


def test_add_client_note():
    crm, _ = setup_crm()
    client = crm.add_client_note("CLI-001", "Nota de prueba")
    assert client is not None
    assert "Nota de prueba" in client.notes


def test_all_clients_summary():
    crm, _ = setup_crm()
    summaries = crm.get_all_clients_summary()
    assert len(summaries) >= 5
