import importlib
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

backend = importlib.import_module("app")


@pytest.fixture
def client():
    backend.app.config["TESTING"] = True
    return backend.app.test_client()


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_get_resources_endpoint(client):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"resource_id": 1, "resource_name": "UTS Library"}
    ]

    with patch.object(backend.requests, "get", return_value=mock_response):
        response = client.get("/resources")

    assert response.status_code == 200
    assert response.get_json()[0]["resource_name"] == "UTS Library"


def test_resource_not_found(client):
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": "Resource not found"}

    with patch.object(backend.requests, "get", return_value=mock_response):
        response = client.get("/resources/999999")

    assert response.status_code == 404


def test_database_unavailable(client):
    with patch.object(
        backend.requests,
        "get",
        side_effect=requests.ConnectionError("Database unavailable"),
    ):
        response = client.get("/resources")

    assert response.status_code == 503
    assert response.get_json()["error"] == "Database service unavailable"
