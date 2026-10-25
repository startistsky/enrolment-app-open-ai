
import os
import sys
from unittest.mock import patch, Mock

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)
sys.path.insert(0, BACKEND_DIR)

from app import app


def test_multi_agent_requires_message():
    app.config["TESTING"] = True

    with app.test_client() as client:
        response = client.post(
            "/api/multi-agent/event-workflow",
            json={}
        )

    assert response.status_code == 400


def test_multi_agent_disabled_in_cloud():
    app.config["TESTING"] = True

    with patch.dict(
        os.environ,
        {"MULTI_AGENT_ENABLED": "false"}
    ):
        with app.test_client() as client:
            response = client.post(
                "/api/multi-agent/event-workflow",
                json={"user_request": "Find events"}
            )

    assert response.status_code == 503


def test_multi_agent_sends_event_evidence():
    app.config["TESTING"] = True

    fake_events = [
        {
            "id": 1,
            "title": "AI Workshop",
            "category": "Technology",
            "date": "2026-10-15",
            "location": "Campus"
        }
    ]

    fake_response = Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "workflow_id": "test-123",
        "status": "pending_human_review"
    }

    with patch.dict(
        os.environ,
        {"MULTI_AGENT_ENABLED": "true"}
    ), patch(
        "multi_agent.get_events",
        return_value=fake_events
    ), patch(
        "multi_agent.requests.post",
        return_value=fake_response
    ) as mock_post:

        with app.test_client() as client:
            response = client.post(
                "/api/multi-agent/event-workflow",
                json={"user_request": "Find AI events"}
            )

    assert response.status_code == 200

    payload = mock_post.call_args.kwargs["json"]

    assert payload["feature"] == "event_management"
    assert payload["evidence"] == fake_events
    assert payload["user_request"] == "Find AI events"


def test_human_review_rejects_invalid_decision():
    app.config["TESTING"] = True

    with patch.dict(
        os.environ,
        {"MULTI_AGENT_ENABLED": "true"}
    ):
        with app.test_client() as client:
            response = client.post(
                "/api/multi-agent/event-workflow/test-123/decision",
                json={"decision": "Invalid"}
            )

    assert response.status_code == 400


def test_human_review_submits_valid_decision():
    app.config["TESTING"] = True
    upstream = Mock()
    upstream.status_code = 200
    upstream.json.return_value = {
        "workflow_id": "test-123",
        "status": "completed",
        "human_review": {"status": "completed", "decision": "Accept"},
    }

    with patch.dict(os.environ, {"MULTI_AGENT_ENABLED": "true"}), patch(
        "multi_agent.requests.post",
        return_value=upstream,
    ) as mock_post:
        with app.test_client() as client:
            response = client.post(
                "/api/multi-agent/event-workflow/test-123/decision",
                json={"decision": "Accept", "reason": "Reviewed"},
            )

    assert response.status_code == 200
    assert response.get_json()["human_review"]["decision"] == "Accept"
    assert mock_post.call_args.args[0].endswith(
        "/workflow/test-123/decision"
    )
