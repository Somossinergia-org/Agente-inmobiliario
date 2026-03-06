"""Tests para el estimador de precios."""

from src.data.database import Database
from src.estimation.estimator import PriceEstimator


def setup_estimator():
    db = Database()
    return PriceEstimator(db)


def test_estimate_price_madrid():
    est = setup_estimator()
    result = est.estimate_price("Madrid", "piso", 90, bedrooms=3)
    assert result.estimated_price > 0
    assert result.comparable_count > 0


def test_estimate_with_features():
    est = setup_estimator()
    base = est.estimate_price("Madrid", "piso", 90, bedrooms=3)
    premium = est.estimate_price("Madrid", "piso", 90, bedrooms=3, features=["piscina", "terraza"])
    assert premium.estimated_price >= base.estimated_price


def test_estimate_no_comparables():
    est = setup_estimator()
    result = est.estimate_price("CiudadInexistente", "castillo", 1000)
    assert result.confidence == "baja"


def test_market_comparative():
    est = setup_estimator()
    comp = est.get_market_comparative("RES-001")
    assert comp is not None
    assert comp.market_summary


def test_zone_stats():
    est = setup_estimator()
    stats = est.get_zone_stats("Madrid")
    assert stats["count"] > 0
    assert stats["avg_price"] > 0


def test_zone_stats_no_data():
    est = setup_estimator()
    stats = est.get_zone_stats("CiudadInexistente")
    assert stats["count"] == 0
