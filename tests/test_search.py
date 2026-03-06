"""Tests para el motor de búsqueda."""

from src.data.database import Database
from src.search.engine import SearchEngine, SearchFilters


def setup_engine():
    db = Database()
    return SearchEngine(db)


def test_search_all_available():
    engine = setup_engine()
    results = engine.search(SearchFilters())
    assert len(results) > 0


def test_search_by_city():
    engine = setup_engine()
    results = engine.search(SearchFilters(cities=["Madrid"]))
    assert all(r.city == "Madrid" for r in results)


def test_search_by_type():
    engine = setup_engine()
    results = engine.search(SearchFilters(property_types=["piso"]))
    assert all(r.property_type.value == "piso" for r in results)


def test_search_by_budget():
    engine = setup_engine()
    results = engine.search_by_budget(100000, 300000)
    assert all(100000 <= r.price <= 300000 for r in results)


def test_search_residential():
    engine = setup_engine()
    results = engine.search_residential(min_bedrooms=3)
    for r in results:
        assert hasattr(r, "bedrooms")
        assert r.bedrooms >= 3


def test_search_commercial():
    engine = setup_engine()
    results = engine.search_commercial()
    assert len(results) > 0


def test_search_land():
    engine = setup_engine()
    results = engine.search_land()
    assert len(results) > 0


def test_search_rural():
    engine = setup_engine()
    results = engine.search_rural()
    assert len(results) > 0


def test_search_garages():
    engine = setup_engine()
    results = engine.search_garages()
    assert len(results) > 0


def test_quick_search():
    engine = setup_engine()
    results = engine.quick_search("mar")
    assert len(results) > 0


def test_search_rental():
    engine = setup_engine()
    results = engine.search(SearchFilters(is_rental=True))
    assert all(r.is_rental for r in results)


def test_sort_by_price():
    engine = setup_engine()
    results = engine.search(SearchFilters(sort_by="price", sort_ascending=True, is_rental=False))
    for i in range(len(results) - 1):
        assert results[i].price <= results[i + 1].price


def test_property_count_by_type():
    engine = setup_engine()
    counts = engine.get_property_count_by_type()
    assert len(counts) > 0
    assert sum(counts.values()) >= 50
