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


RAG_RESULT = {
    "query": "What cybersecurity events are available?",
    "matches": [
        {
            "source_id": "event:14",
            "citation": (
                "Campus Event record: "
                "Cybersecurity Challenge"
            ),
            "confidence": "high",
            "score": 8,
            "context": EVENT
        }
    ],
    "insufficient_context": False
}


def get_test_client():
    app.config["TESTING"] = True
    return app.test_client()


def test_rag_event_endpoint():
    """
    Test the Student 4 RAG retrieval endpoint.
    """

    with patch(
        "ai.retrieve_event_context",
        return_value={
            "ok": True,
            "result": RAG_RESULT
        }
    ) as mock_rag:

        client = get_test_client()

        response = client.post(
            "/api/rag/event",
            json={
                "query":
                "What cybersecurity events are available?"
            }
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data[
            "insufficient_context"
        ] is False

        assert len(
            data["matches"]
        ) == 1

        assert (
            data["matches"][0]["context"]["title"]
            == "Cybersecurity Challenge"
        )

        mock_rag.assert_called_once_with(
            "What cybersecurity events are available?",
            top_k=3
        )


def test_rag_event_requires_query():
    """
    Test validation when no RAG query is supplied.
    """

    client = get_test_client()

    response = client.post(
        "/api/rag/event",
        json={}
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "query is required"


def test_ai_event_question_uses_rag():
    """
    Test normal /api/ai Event questions use RAG.
    """

    with patch(
        "ai.retrieve_event_context",
        return_value={
            "ok": True,
            "result": RAG_RESULT
        }
    ) as mock_rag:

        with patch(
            "ai.call_llm",
            return_value=(
                "The Cybersecurity Challenge workshop "
                "is scheduled on August 18, 2026, "
                "at Building 10."
            )
        ):

            client = get_test_client()

            response = client.post(
                "/api/ai",
                json={
                    "message":
                    "What cybersecurity events are available?"
                }
            )

            assert response.status_code == 200

            data = response.get_json()

            workflow = data[
                "agentic_workflow"
            ]

            assert workflow["mode"] == "rag"

            assert (
                workflow["grounding"]
                == "grounded_llm"
            )

            assert (
                "Cybersecurity Challenge"
                in data["response"]
            )

            assert (
                "Campus Event record: "
                "Cybersecurity Challenge"
                in workflow["citations"]
            )

            assert "plan" in workflow
            assert "act" in workflow
            assert "observe" in workflow
            assert "adapt" in workflow

            mock_rag.assert_called_once_with(
                "What cybersecurity events are available?",
                top_k=5
            )


def test_rag_grounding_guard_uses_context_fallback():
    """
    Test that an incorrect LLM answer is replaced
    by a deterministic response from retrieved context.
    """

    with patch(
        "ai.retrieve_event_context",
        return_value={
            "ok": True,
            "result": RAG_RESULT
        }
    ):

        with patch(
            "ai.call_llm",
            return_value=(
                "There are no cybersecurity events "
                "available in the context provided."
            )
        ):

            client = get_test_client()

            response = client.post(
                "/api/ai",
                json={
                    "message":
                    "What cybersecurity events are available?"
                }
            )

            assert response.status_code == 200

            data = response.get_json()

            workflow = data[
                "agentic_workflow"
            ]

            assert workflow["mode"] == "rag"

            assert (
                workflow["grounding"]
                == "retrieved_context_fallback"
            )

            assert (
                "Cybersecurity Challenge"
                in data["response"]
            )

            assert (
                "Building 10"
                in data["response"]
            )


def test_rag_insufficient_context_uses_release0_fallback():
    """
    Test the Release 0 database workflow remains available
    when RAG cannot retrieve useful context.
    """

    with patch(
        "ai.retrieve_event_context",
        return_value={
            "ok": True,
            "result": {
                "query":
                "What cybersecurity events are available?",
                "matches": [],
                "insufficient_context": True,
                "message":
                "Insufficient context"
            }
        }
    ):

        with patch(
            "ai.call_llm",
            side_effect=[
                "Search the Campus Event database.",
                (
                    '{"date":"","month":"","category":"",'
                    '"title":"","location":"",'
                    '"keywords":["cybersecurity"]}'
                )
            ]
        ):

            with patch(
                "ai.get_events",
                return_value=[
                    EVENT
                ]
            ):

                client = get_test_client()

                response = client.post(
                    "/api/ai",
                    json={
                        "message":
                        "What cybersecurity events "
                        "are available?"
                    }
                )

                assert response.status_code == 200

                data = response.get_json()

                workflow = data[
                    "agentic_workflow"
                ]

                assert (
                    workflow["mode"]
                    == "event_database"
                )

                assert (
                    workflow["rag_fallback"]
                    is True
                )

                assert (
                    "Cybersecurity Challenge"
                    in data["response"]
                )


def test_rag_server_unavailable_returns_503():
    """
    Test RAG server error handling.
    """

    with patch(
        "ai.retrieve_event_context",
        return_value={
            "ok": False,
            "status": 503,
            "error": "RAG server unavailable",
            "detail": "connection failed"
        }
    ):

        client = get_test_client()

        response = client.post(
            "/api/rag/event",
            json={
                "query":
                "What cybersecurity events are available?"
            }
        )

        assert response.status_code == 503

        data = response.get_json()

        assert (
            data["error"]
            == "RAG server unavailable"
        )