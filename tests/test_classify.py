from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.database import get_db

client = TestClient(app)


def override_get_db():
    db = MagicMock()

    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = None
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock

    yield db


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("app.routers.classify.classify_email")
def test_classify_factura(mock_classify):
    mock_classify.return_value = {
        "message_id": "test_001",
        "category": "facturas",
        "label_name": "TFG/Facturas",
        "confidence": 0.85,
        "phishing_score": 0.02,
        "engine_used": "keywords",
        "explanation": "Keyword match: facturas",
    }

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/classify", json={
        "message_id": "test_001",
        "subject": "Factura marzo 2026",
        "sender": "billing@empresa.com",
        "snippet": "Adjuntamos su factura del mes de marzo",
        "body": "",
        "engine": "keywords",
    })

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "facturas"
    assert data["confidence"] > 0.5


@patch("app.routers.classify.classify_email")
def test_classify_phishing(mock_classify):
    mock_classify.return_value = {
        "message_id": "test_002",
        "category": "phishing",
        "label_name": "TFG/Phishing",
        "confidence": 0.92,
        "phishing_score": 0.95,
        "engine_used": "keywords",
        "explanation": "Señales de phishing detectadas",
    }

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/classify", json={
        "message_id": "test_002",
        "subject": "Verifica tu cuenta urgente o será suspendida",
        "sender": "seguridad@banco-fake.com",
        "snippet": "Haz clic aquí inmediatamente para confirmar tu contraseña",
        "body": "",
        "engine": "keywords",
    })

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "phishing"
    assert data["phishing_score"] > 0.7