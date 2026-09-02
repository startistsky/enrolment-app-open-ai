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

    Plan -> Extract Query -> Act -> Observe -> Adapt
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

    fake_query = """
    {
        "date": "",
        "month": "",
        "category": "Career",
        "title": "",
        "location": "",
        "keywords": []
    }
    """

    expected_response = (
        "I found 1 matching event:\n\n"
        "Career Fair 2026 — 2026-08-25 at Main Hall. "
        "Meet employers and explore career opportunities."
    )

    # call_llm() is called twice:
    # 1. PLAN
    # 2. EXTRACT STRUCTURED QUERY
    with patch(
        "ai.get_events",
        return_value=fake_events
    ), patch(
        "ai.call_llm",
        side_effect=[
            fake_plan,
            fake_query
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

        # Check final response
        assert "response" in data
        assert data["response"] == expected_response

        # Check Agentic workflow exists
        assert "agentic_workflow" in data

        workflow = data["agentic_workflow"]

        # Check workflow mode
        assert workflow["mode"] == "event_database"

        # Check all stages
        assert "plan" in workflow
        assert "query" in workflow
        assert "act" in workflow
        assert "observe" in workflow
        assert "adapt" in workflow

        # PLAN
        assert workflow["plan"] == fake_plan

        # QUERY
        assert workflow["query"]["date"] == ""
        assert workflow["query"]["month"] == ""
        assert workflow["query"]["category"] == "Career"
        assert workflow["query"]["title"] == ""
        assert workflow["query"]["location"] == ""
        assert workflow["query"]["keywords"] == []

        # ACT
        assert (
            workflow["act"]
            == "Retrieved 2 events and found 1 matches."
        )

        # OBSERVE
        assert (
            workflow["observe"]
            == "Database search found 1 matching events."
        )

        # ADAPT
        assert workflow["adapt"] == expected_response


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

    fake_query = """
    {
        "date": "",
        "month": "",
        "category": "",
        "title": "",
        "location": "",
        "keywords": []
    }
    """

    expected_response = (
        "No matching event is currently available."
    )

    with patch(
        "ai.get_events",
        return_value=[]
    ), patch(
        "ai.call_llm",
        side_effect=[
            fake_plan,
            fake_query
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

        assert data["response"] == expected_response

        workflow = data["agentic_workflow"]

        assert workflow["mode"] == "event_database"

        # PLAN
        assert workflow["plan"] == fake_plan

        # QUERY
        assert workflow["query"] == {
            "date": "",
            "month": "",
            "category": "",
            "title": "",
            "location": "",
            "keywords": []
        }

        # ACT
        assert (
            workflow["act"]
            == "Retrieved 0 events and found 0 matches."
        )

        # OBSERVE
        assert (
            workflow["observe"]
            == "Database search found no matching events."
        )

        # ADAPT
        assert workflow["adapt"] == expected_response


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