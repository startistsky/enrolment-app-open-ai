import os
import sys
from unittest.mock import patch


# Add backend folder to Python import path
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BACKEND_DIR = os.path.join(BASE_DIR, "backend")

sys.path.insert(0, BACKEND_DIR)


from app import app


def get_test_client():
    app.config["TESTING"] = True
    return app.test_client()


def test_ai_agentic_workflow():
    """
    Test the complete Agentic AI workflow:

    Plan -> Act -> Observe -> Adapt
    """

    fake_events = [
        {
            "id": 1,
            "title": "Career Fair 2026",
            "category": "Career",
            "date": "2026-08-25",
            "location": "Main Hall",
            "description": "Meet employers and explore career opportunities."
        },
        {
            "id": 2,
            "title": "AI Workshop",
            "category": "Technology",
            "date": "2026-08-27",
            "location": "Room 101",
            "description": "Introduction to artificial intelligence."
        }
    ]

    fake_plan = (
        "Look for career-related events in the campus event database."
    )

    fake_final_answer = (
        "Career Fair 2026 is available on 2026-08-25 "
        "at the Main Hall."
    )

    # call_llm() is called twice:
    # 1. PLAN
    # 2. ADAPT
    with patch(
        "ai.get_events",
        return_value=fake_events
    ), patch(
        "ai.call_llm",
        side_effect=[
            fake_plan,
            fake_final_answer
        ]
    ):

        client = get_test_client()

        response = client.post(
            "/api/ai",
            json={
                "message": "Are there any career events?"
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        # Check final AI response
        assert "response" in data
        assert data["response"] == fake_final_answer

        # Check Agentic workflow exists
        assert "agentic_workflow" in data

        workflow = data["agentic_workflow"]

        # Check all four stages
        assert "plan" in workflow
        assert "act" in workflow
        assert "observe" in workflow
        assert "adapt" in workflow

        # PLAN
        assert workflow["plan"] == fake_plan

        # ACT
        assert "Retrieved 2 events" in workflow["act"]

        # OBSERVE
        assert "Career Fair 2026" in workflow["observe"]
        assert "AI Workshop" in workflow["observe"]

        # ADAPT
        assert workflow["adapt"] == fake_final_answer


def test_ai_missing_message():
    """
    Test that the AI API rejects an empty message.
    """

    client = get_test_client()

    response = client.post(
        "/api/ai",
        json={}
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "Message is required."


def test_ai_empty_database():
    """
    Test Agentic AI workflow when the database
    contains no events.
    """

    fake_plan = (
        "Search the campus event database for matching events."
    )

    fake_final_answer = (
        "No matching campus events are currently available."
    )

    with patch(
        "ai.get_events",
        return_value=[]
    ), patch(
        "ai.call_llm",
        side_effect=[
            fake_plan,
            fake_final_answer
        ]
    ):

        client = get_test_client()

        response = client.post(
            "/api/ai",
            json={
                "message": "What events are available?"
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        workflow = data["agentic_workflow"]

        assert workflow["plan"] == fake_plan

        assert (
            workflow["act"]
            == "Retrieved 0 events from the database service."
        )

        assert (
            workflow["observe"]
            == "The database returned no campus events."
        )

        assert workflow["adapt"] == fake_final_answer


def test_ai_service_failure():
    """
    Test error handling when Ollama / AI service
    cannot be reached.
    """

    with patch(
        "ai.call_llm",
        side_effect=RuntimeError(
            "Failed to communicate with AI service."
        )
    ):

        client = get_test_client()

        response = client.post(
            "/api/ai",
            json={
                "message": "Show me career events."
            }
        )

        assert response.status_code == 503

        data = response.get_json()

        assert "error" in data
        assert "Failed to communicate" in data["error"]