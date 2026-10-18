
import os
import sys
from unittest.mock import patch

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, BASE_DIR)

from app import create_app


def test_event_multi_agent_workflow(tmp_path):
    """Test Planner, Worker, Reviewer and Human Review."""

    app = create_app(
        history_path=tmp_path / "history.jsonl",
        audit_path=tmp_path / "audit.jsonl"
    )
    app.config["TESTING"] = True

    events = [
        {
            "id": 1,
            "title": "AI Workshop",
            "category": "Technology",
            "date": "2026-10-15",
            "location": "Campus",
            "description": "Introduction to AI"
        }
    ]

    planner_output = {
        "plan": "Find relevant AI events",
        "evidence_required": ["title", "date", "location"]
    }

    worker_output = {
        "answer": "AI Workshop is on 2026-10-15 at Campus.",
        "evidence_used": [1],
        "missing_evidence": []
    }

    reviewer_output = {
        "risk": "Low risk",
        "unsupported_claims": [],
        "correction": "No correction required",
        "recommendation": "Human should verify the event details"
    }

    with patch(
        "agents.event_planner_agent.run",
        return_value=planner_output
    ), patch(
        "agents.event_worker_agent.run",
        return_value=worker_output
    ), patch(
        "agents.event_reviewer_agent.run",
        return_value=reviewer_output
    ):

        client = app.test_client()

        response = client.post(
            "/workflow/event",
            json={
                "feature": "event_management",
                "user_request": "Find AI workshops",
                "evidence": events
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["status"] == "pending_human_review"
        assert data["planner_status"] == "completed"
        assert data["worker_status"] == "completed"
        assert data["reviewer_status"] == "completed"

        workflow_id = data["workflow_id"]

        review_response = client.post(
            f"/workflow/{workflow_id}/decision",
            json={
                "decision": "Accept",
                "reason": "Verified event details"
            }
        )

        assert review_response.status_code == 200

        review_data = review_response.get_json()

        assert review_data["status"] == "completed"
        assert review_data["human_review"]["decision"] == "Accept"
