"""Tests para el agente orquestador."""

from src.agent.orchestrator import RealEstateAgent
from src.search.engine import SearchFilters


def test_agent_init():
    agent = RealEstateAgent()
    assert agent.db.total_properties >= 50
    assert agent.db.total_clients >= 5


def test_dashboard():
    agent = RealEstateAgent()
    dashboard = agent.get_dashboard()
    assert dashboard["total_properties"] >= 50
    assert dashboard["available"] > 0
    assert dashboard["total_clients"] >= 5


def test_quick_search():
    agent = RealEstateAgent()
    results = agent.quick_search("Madrid")
    assert len(results) > 0


def test_search_properties():
    agent = RealEstateAgent()
    results = agent.search_properties(SearchFilters(cities=["Madrid"]))
    assert len(results) > 0


def test_property_detail():
    agent = RealEstateAgent()
    detail = agent.get_property_detail("RES-001")
    assert detail is not None
    assert detail["id"] == "RES-001"


def test_list_clients():
    agent = RealEstateAgent()
    clients = agent.list_clients()
    assert len(clients) >= 5


def test_find_properties_for_client():
    agent = RealEstateAgent()
    results = agent.find_properties_for_client("CLI-001")
    assert len(results) > 0


def test_estimate_price():
    agent = RealEstateAgent()
    est = agent.estimate_price("Madrid", "piso", 90, bedrooms=3)
    assert est.estimated_price > 0


def test_get_comparative():
    agent = RealEstateAgent()
    comp = agent.get_comparative("RES-001")
    assert comp is not None


def test_zone_stats():
    agent = RealEstateAgent()
    stats = agent.get_zone_stats("Madrid")
    assert stats["count"] > 0
