"""Tests para las propiedades y la base de datos."""

from src.data.properties import get_all_properties, get_sample_clients
from src.data.database import Database
from src.models.property import PropertyStatus, PropertyType


def test_all_properties_count():
    props = get_all_properties()
    assert len(props) >= 50, f"Se esperaban al menos 50 propiedades, hay {len(props)}"


def test_all_property_types_covered():
    props = get_all_properties()
    types = {p.property_type for p in props}
    required = {
        PropertyType.APARTMENT,
        PropertyType.HOUSE,
        PropertyType.VILLA,
        PropertyType.DUPLEX,
        PropertyType.PENTHOUSE,
        PropertyType.STUDIO,
        PropertyType.COMMERCIAL_OFFICE,
        PropertyType.COMMERCIAL_RETAIL,
        PropertyType.COMMERCIAL_WAREHOUSE,
        PropertyType.LAND_URBAN,
        PropertyType.LAND_RUSTIC,
        PropertyType.RURAL_ESTATE,
        PropertyType.RURAL_COUNTRY_HOUSE,
        PropertyType.GARAGE,
        PropertyType.STORAGE,
    }
    missing = required - types
    assert not missing, f"Faltan tipos: {missing}"


def test_properties_have_valid_data():
    for prop in get_all_properties():
        assert prop.id, "Propiedad sin ID"
        assert prop.title, "Propiedad sin título"
        assert prop.price > 0, f"Propiedad {prop.id} con precio <= 0"
        assert prop.area_m2 > 0, f"Propiedad {prop.id} sin superficie"
        assert prop.city, f"Propiedad {prop.id} sin ciudad"


def test_price_per_m2():
    props = get_all_properties()
    for prop in props:
        assert prop.price_per_m2 > 0


def test_rental_properties_exist():
    props = get_all_properties()
    rentals = [p for p in props if p.is_rental]
    assert len(rentals) >= 5, "Se esperaban al menos 5 propiedades de alquiler"


def test_database_loads():
    db = Database()
    assert db.total_properties >= 50
    assert db.total_clients >= 5


def test_database_get_property():
    db = Database()
    prop = db.get_property("RES-001")
    assert prop is not None
    assert prop.city == "Madrid"


def test_database_available_properties():
    db = Database()
    available = db.get_available_properties()
    assert len(available) > 0
    assert all(p.status == PropertyStatus.AVAILABLE for p in available)


def test_sample_clients():
    clients = get_sample_clients()
    assert len(clients) >= 5
    for client in clients:
        assert client.id
        assert client.name
        assert client.email
        assert client.phone
