from copy import deepcopy
from unittest.mock import Mock


RAG_QUERY = "What course covers databases?"
RAG_MATCH = {
    "source_id": "course:COMP3311",
    "citation": "Course Management record: COMP3311",
    "confidence": "medium",
    "score": 3,
    "context": {
        "course_code": "COMP3311",
        "course_name": "Database Systems",
        "lecturer": "Dr. Example",
        "semester": "Spring 2026",
        "credit_points": 6,
        "course_description": "Database concepts.",
    },
}


def rag_success_result(matches=None, query=RAG_QUERY):
    return {
        "ok": True,
        "result": {
            "query": query,
            "matches": deepcopy(matches if matches is not None else [RAG_MATCH]),
            "insufficient_context": False,
        },
    }


def test_release1_paoa_mcp_course_by_code_success(
    backend_app,
    backend_client,
    monkeypatch,
):
    call_mcp_tool = Mock(return_value={
        "ok": True,
        "result": {
            "course_code": "COMP1001",
            "course_name": "Introduction to Information Technology",
            "lecturer": "Dr. John Smith",
            "semester": "Spring 2026",
            "credit_points": 6,
        },
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={
            "mode": "mcp",
            "action": "course_by_code",
            "course_code": " comp1001 ",
        },
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["mode"] == "mcp"
    assert "plan" in body
    assert "act" in body
    assert body["observe"]["valid"] is True
    assert body["adapt"]["performed"] is False
    assert body["final_result"]["course_code"] == "COMP1001"
    call_mcp_tool.assert_called_once_with(
        "course_by_code",
        {"course_code": "COMP1001"},
    )


def test_release1_paoa_mcp_course_count_success(
    backend_app,
    backend_client,
    monkeypatch,
):
    monkeypatch.setattr(
        backend_app,
        "call_mcp_tool",
        Mock(return_value={
            "ok": True,
            "result": {"course_count": 11},
        }),
    )

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "mcp", "action": "course_count"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["observe"]["valid"] is True
    assert body["adapt"]["performed"] is False
    assert body["final_result"]["course_count"] == 11


def test_release1_paoa_mcp_invalid_result_retries_once(
    backend_app,
    backend_client,
    monkeypatch,
):
    invalid_result = {
        "ok": True,
        "result": {"course_code": "COMP1001"},
    }
    call_mcp_tool = Mock(side_effect=[invalid_result, invalid_result])
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={
            "mode": "mcp",
            "action": "course_by_code",
            "course_code": "COMP1001",
        },
    )
    body = response.get_json()

    assert response.status_code == 502
    assert call_mcp_tool.call_count == 2
    assert body["adapt"]["performed"] is True
    assert body["adapt"]["retry_count"] == 1
    assert body["observe"]["valid"] is False


def test_release1_paoa_mcp_service_failure_no_retry(
    backend_app,
    backend_client,
    monkeypatch,
):
    call_mcp_tool = Mock(return_value={
        "ok": False,
        "status": 503,
        "error": "MCP server unavailable",
        "detail": "connection failed",
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "mcp", "action": "course_count"},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "MCP server unavailable"
    assert call_mcp_tool.call_count == 1


def test_release1_paoa_rag_success(backend_app, backend_client, monkeypatch):
    answer = "COMP3311 Database Systems covers database concepts."
    generate_answer = Mock(return_value=(answer, None))
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=rag_success_result()),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        generate_answer,
    )

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "rag", "query": RAG_QUERY, "top_k": 3},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["mode"] == "rag"
    assert "plan" in body
    assert "act" in body
    assert body["observe"]["valid"] is True
    assert body["observe"]["grounding_available"] is True
    assert body["adapt"]["performed"] is False
    assert body["final_result"]["insufficient_context"] is False
    assert body["final_result"]["confidence"] == "medium"
    assert body["final_result"]["citations"] == [
        "Course Management record: COMP3311"
    ]
    assert body["final_result"]["answer"] == answer
    generate_answer.assert_called_once()


def test_release1_paoa_rag_insufficient_context_skips_ai(
    backend_app,
    backend_client,
    monkeypatch,
):
    query = "Tell me about quantum agriculture"
    generate_answer = Mock()
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value={
            "ok": True,
            "result": {
                "query": query,
                "matches": [],
                "insufficient_context": True,
                "message": "Insufficient context: no relevant Course Management information was found.",
            },
        }),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        generate_answer,
    )

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "rag", "query": query},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["observe"]["valid"] is True
    assert body["observe"]["grounding_available"] is False
    assert body["adapt"]["performed"] is False
    assert body["final_result"]["insufficient_context"] is True
    assert body["final_result"]["confidence"] == "low"
    assert body["final_result"]["citations"] == []
    assert body["final_result"]["retrieved_context"] == []
    generate_answer.assert_not_called()


def test_release1_paoa_rag_invalid_result_retries_once(
    backend_app,
    backend_client,
    monkeypatch,
):
    invalid_result = rag_success_result([{
        "context": {"course_code": "COMP3311"},
    }])
    retrieve = Mock(side_effect=[invalid_result, invalid_result])
    monkeypatch.setattr(backend_app, "call_rag_course_retrieval", retrieve)

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "rag", "query": RAG_QUERY, "top_k": 3},
    )
    body = response.get_json()

    assert response.status_code == 502
    assert retrieve.call_count == 2
    assert body["adapt"]["performed"] is True
    assert body["adapt"]["retry_count"] == 1
    assert body["observe"]["valid"] is False


def test_release1_paoa_rag_service_failure_no_retry(
    backend_app,
    backend_client,
    monkeypatch,
):
    retrieve = Mock(return_value={
        "ok": False,
        "status": 503,
        "error": "RAG server unavailable",
        "detail": "connection failed",
    })
    monkeypatch.setattr(backend_app, "call_rag_course_retrieval", retrieve)

    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "rag", "query": RAG_QUERY},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "RAG server unavailable"
    assert retrieve.call_count == 1


def test_release1_paoa_rejects_invalid_mode(backend_client):
    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "invalid"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "mode must be 'mcp' or 'rag'"


def test_release1_paoa_rejects_empty_rag_query(backend_client):
    response = backend_client.post(
        "/api/agentic/release1/validate",
        json={"mode": "rag", "query": "   "},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "A RAG query is required"


def test_release1_paoa_rejects_non_json(backend_client):
    response = backend_client.post("/api/agentic/release1/validate")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Content-Type must be application/json"


def test_release1_paoa_rejects_non_object_json(backend_client):
    response = backend_client.post(
        "/api/agentic/release1/validate",
        json=["invalid"],
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body must be a JSON object"
