import sys
from pathlib import Path
from unittest.mock import Mock, patch

from flask import Flask

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from agent.multi_agent_routes import multi_agent_routes


def client():
    app = Flask(__name__)
    app.register_blueprint(multi_agent_routes, url_prefix="/api")
    app.config["TESTING"] = True
    return app.test_client()


def test_career_workflow_endpoint():
    upstream = Mock()
    upstream.status_code = 200
    upstream.json.return_value = {
        "workflow_id": "career-test",
        "status": "pending_human_review",
    }

    with patch(
        "agent.multi_agent_routes.requests.request",
        return_value=upstream,
    ) as request:
        response = client().post(
            "/api/workflow/career",
            json={
                "user_request": "Find matching roles",
                "selected_job": {"id": 12, "title": "Analyst"},
            },
        )

    assert response.status_code == 200
    assert response.get_json()["workflow_id"] == "career-test"
    assert request.call_args.kwargs["method"] == "POST"
    assert request.call_args.kwargs["url"].endswith("/workflow/career")


def test_career_workflow_decision_endpoint():
    upstream = Mock()
    upstream.status_code = 200
    upstream.json.return_value = {
        "workflow_id": "career-test",
        "status": "completed",
        "human_review": {"status": "completed", "decision": "Accept"},
    }

    with patch(
        "agent.multi_agent_routes.requests.request",
        return_value=upstream,
    ) as request:
        response = client().post(
            "/api/workflow/career-test/decision",
            json={"decision": "Accept", "reason": "Reviewed"},
        )

    assert response.status_code == 200
    assert response.get_json()["human_review"]["decision"] == "Accept"
    assert request.call_args.kwargs["method"] == "POST"
    assert request.call_args.kwargs["url"].endswith(
        "/workflow/career-test/decision"
    )
