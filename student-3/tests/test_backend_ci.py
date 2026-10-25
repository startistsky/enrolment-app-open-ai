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


def test_multi_agent_resource_workflow_endpoint(client):
    resources = [{"resource_id": 7, "resource_name": "Study Room A"}]
    upstream = Mock()
    upstream.status_code = 200
    upstream.json.return_value = {
        "workflow_id": "resource-test",
        "status": "pending_human_review",
    }

    with patch.object(backend, "fetch_resources", return_value=resources), patch.object(
        backend.requests, "post", return_value=upstream,
    ) as post:
        response = client.post(
            "/api/multi-agent/resource",
            json={"question": "Find a study room"},
        )

    assert response.status_code == 200
    assert response.get_json()["workflow_id"] == "resource-test"
    assert post.call_args.args[0].endswith("/workflow/resource")
    assert post.call_args.kwargs["json"]["feature"] == "resource_management"
    assert post.call_args.kwargs["json"]["evidence"] == resources


def test_multi_agent_resource_decision_endpoint(client):
    upstream = Mock()
    upstream.status_code = 200
    upstream.json.return_value = {
        "workflow_id": "resource-test",
        "status": "completed",
        "human_review": {"status": "completed", "decision": "Accept"},
    }

    with patch.object(backend.requests, "post", return_value=upstream) as post:
        response = client.post(
            "/api/multi-agent/resource-test/decision",
            json={"decision": "Accept", "reason": "Reviewed"},
        )

    assert response.status_code == 200
    assert response.get_json()["human_review"]["decision"] == "Accept"
    assert post.call_args.args[0].endswith(
        "/workflow/resource-test/decision"
    )
