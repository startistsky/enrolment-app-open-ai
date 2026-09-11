from copy import deepcopy
from unittest.mock import Mock


QUERY = "What course covers databases?"
COURSE_MATCH = {
    "source_id": "course:COMP3311",
    "citation": "Course Management record: COMP3311",
    "confidence": "medium",
    "score": 3,
    "context": {
        "course_id": 3,
        "course_code": "COMP3311",
        "course_name": "Database Systems",
        "lecturer": "Dr. Example",
        "semester": "Spring 2026",
        "credit_points": 6,
        "course_description": "Database concepts.",
    },
}


def successful_retrieval(matches=None, query=QUERY):
    return {
        "ok": True,
        "result": {
            "query": query,
            "matches": deepcopy(matches if matches is not None else [COURSE_MATCH]),
            "insufficient_context": False,
        },
    }


def test_rag_course_retrieval_success(backend_app, backend_client, monkeypatch):
    call_rag_course_retrieval = Mock(return_value=successful_retrieval())
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        call_rag_course_retrieval,
    )

    response = backend_client.post("/api/rag/course", json={"query": QUERY})
    body = response.get_json()

    assert response.status_code == 200
    assert "result" in body
    assert body["result"]["insufficient_context"] is False
    assert body["result"]["matches"][0]["context"]["course_code"] == "COMP3311"
    call_rag_course_retrieval.assert_called_once_with(QUERY, 3)


def test_rag_grounded_answer_success(backend_app, backend_client, monkeypatch):
    retrieval = successful_retrieval()
    answer = "COMP3311 Database Systems covers database concepts."
    generate_answer = Mock(return_value=(answer, None))
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=retrieval),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        generate_answer,
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})
    body = response.get_json()

    assert response.status_code == 200
    assert body["answer"] == answer
    assert body["citations"] == ["Course Management record: COMP3311"]
    assert body["confidence"] == "medium"
    assert body["insufficient_context"] is False
    assert body["retrieved_context"] == retrieval["result"]["matches"]
    generate_answer.assert_called_once()


def test_rag_grounded_answer_insufficient_context_skips_ai(
    backend_app,
    backend_client,
    monkeypatch,
):
    query = "Tell me about quantum agriculture"
    retrieval = {
        "ok": True,
        "result": {
            "query": query,
            "matches": [],
            "insufficient_context": True,
            "message": "Insufficient context: no relevant Course Management information was found.",
        },
    }
    generate_answer = Mock()
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=retrieval),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        generate_answer,
    )

    response = backend_client.post("/api/rag/answer", json={"query": query})
    body = response.get_json()

    assert response.status_code == 200
    assert body["insufficient_context"] is True
    assert body["confidence"] == "low"
    assert body["citations"] == []
    assert body["retrieved_context"] == []
    assert "Insufficient context" in body["answer"]
    generate_answer.assert_not_called()


def test_rag_server_unavailable_returns_503(
    backend_app,
    backend_client,
    monkeypatch,
):
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value={
            "ok": False,
            "status": 503,
            "error": "RAG server unavailable",
            "detail": "connection failed",
        }),
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})

    assert response.status_code == 503
    assert response.get_json()["error"] == "RAG server unavailable"


def test_rag_retrieval_failure_returns_502(
    backend_app,
    backend_client,
    monkeypatch,
):
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value={
            "ok": False,
            "status": 502,
            "error": "RAG retrieval failed",
            "detail": "invalid response",
        }),
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "RAG retrieval failed",
        "detail": "invalid response",
    }


def test_rag_ai_service_unavailable(backend_app, backend_client, monkeypatch):
    def ai_unavailable(_query, _retrieval_result):
        return None, (
            backend_app.jsonify({"error": "AI service unavailable"}),
            503,
        )

    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=successful_retrieval()),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        Mock(side_effect=ai_unavailable),
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})

    assert response.status_code == 503
    assert response.get_json()["error"] == "AI service unavailable"


def test_rag_answer_rejects_non_json(backend_client):
    response = backend_client.post("/api/rag/answer")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Content-Type must be application/json"


def test_rag_answer_rejects_non_object_json(backend_client):
    response = backend_client.post("/api/rag/answer", json=["invalid"])

    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body must be a JSON object"


def test_rag_confidence_comes_from_top_match(
    backend_app,
    backend_client,
    monkeypatch,
):
    first_match = deepcopy(COURSE_MATCH)
    first_match["confidence"] = "high"
    second_match = deepcopy(COURSE_MATCH)
    second_match["source_id"] = "course:COMP9999"
    second_match["confidence"] = "low"
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=successful_retrieval([first_match, second_match])),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        Mock(return_value=("Grounded answer", None)),
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})

    assert response.status_code == 200
    assert response.get_json()["confidence"] == "high"


def test_rag_citations_are_deduplicated(
    backend_app,
    backend_client,
    monkeypatch,
):
    first_match = deepcopy(COURSE_MATCH)
    second_match = deepcopy(COURSE_MATCH)
    second_match["source_id"] = "course:COMP9999"
    monkeypatch.setattr(
        backend_app,
        "call_rag_course_retrieval",
        Mock(return_value=successful_retrieval([first_match, second_match])),
    )
    monkeypatch.setattr(
        backend_app,
        "generate_grounded_course_answer",
        Mock(return_value=("Grounded answer", None)),
    )

    response = backend_client.post("/api/rag/answer", json={"query": QUERY})

    assert response.status_code == 200
    assert response.get_json()["citations"] == [
        "Course Management record: COMP3311"
    ]
