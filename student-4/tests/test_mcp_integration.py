import os
import sys
from unittest.mock import patch


# Add Student 4 backend to Python import path.
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BACKEND_DIR = os.path.join(
    BASE_DIR,
    "backend"
)

sys.path.insert(
    0,
    BACKEND_DIR
)


from app import app


EVENT = {
    "id": 14,
    "title": "Cybersecurity Challenge",
    "category": "Workshop",
    "date": "2026-08-18",
    "location": "Building 10",
    "description": (
        "Solve beginner-friendly cybersecurity puzzles "
        "in teams and learn core security concepts."
    ),
    "emoji": "🔐"
}


def get_test_client():
    app.config["TESTING"] = True
    return app.test_client()


def test_mcp_event_count_endpoint():
    """
    Test the Student 4 event_count MCP endpoint.
    """

    with patch(
        "ai.call_mcp_tool",
        return_value={
            "ok": True,
            "result": {
                "event_count": 16
            }
        }
    ) as mock_mcp:

        client = get_test_client()

        response = client.get(
            "/api/mcp/event-count"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["tool"] == "event_count"
        assert data["result"]["event_count"] == 16

        mock_mcp.assert_called_once_with(
            "event_count"
        )


def test_mcp_event_by_title_endpoint():
    """
    Test the Student 4 event_by_title MCP endpoint.
    """

    with patch(
        "ai.call_mcp_tool",
        return_value={
            "ok": True,
            "result": EVENT
        }
    ) as mock_mcp:

        client = get_test_client()

        response = client.get(
            "/api/mcp/event-by-title"
            "?title=Cybersecurity%20Challenge"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["tool"] == "event_by_title"

        assert (
            data["result"]["title"]
            == "Cybersecurity Challenge"
        )

        assert (
            data["result"]["location"]
            == "Building 10"
        )

        mock_mcp.assert_called_once_with(
            "event_by_title",
            {
                "event_title":
                "Cybersecurity Challenge"
            }
        )


def test_mcp_event_by_title_requires_title():
    """
    Test validation when no event title is supplied.
    """

    client = get_test_client()

    response = client.get(
        "/api/mcp/event-by-title"
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "title is required"


def test_ai_event_count_uses_mcp():
    """
    Test that normal /api/ai questions about
    the number of events use MCP.
    """

    with patch(
        "ai.call_mcp_tool",
        return_value={
            "ok": True,
            "result": {
                "event_count": 16
            }
        }
    ) as mock_mcp:

        client = get_test_client()

        response = client.post(
            "/api/ai",
            json={
                "message":
                "How many events are there?"
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        assert (
            data["response"]
            == (
                "There are 16 campus events "
                "currently available."
            )
        )

        workflow = data[
            "agentic_workflow"
        ]

        assert workflow["mode"] == "mcp"
        assert workflow["tool"] == "event_count"

        assert "plan" in workflow
        assert "act" in workflow
        assert "observe" in workflow
        assert "adapt" in workflow

        assert (
            workflow["adapt"]
            == data["response"]
        )

        mock_mcp.assert_called_once_with(
            "event_count"
        )


def test_mcp_server_unavailable_returns_503():
    """
    Test MCP server error handling.
    """

    with patch(
        "ai.call_mcp_tool",
        return_value={
            "ok": False,
            "status": 503,
            "error": "MCP server unavailable",
            "detail": "connection failed"
        }
    ):

        client = get_test_client()

        response = client.get(
            "/api/mcp/event-count"
        )

        assert response.status_code == 503

        data = response.get_json()

        assert (
            data["error"]
            == "MCP server unavailable"
        )