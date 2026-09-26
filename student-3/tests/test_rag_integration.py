import os
import sys


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

RAG_SERVER_DIR = os.path.join(
    PROJECT_ROOT,
    "rag-server",
)

sys.path.insert(
    0,
    RAG_SERVER_DIR,
)


from retrievers.student3_resource_retriever import (
    get_confidence,
    index_knowledge,
    retrieve_resource_context,
)


# =========================================================
# RAG RETRIEVAL TESTS
# =========================================================

def test_resource_knowledge_indexing():
    """Test Student 3 resource knowledge is indexed into ChromaDB."""
    result = index_knowledge()

    assert result["status"] == "indexed"
    assert result["collection"] == "student3_resource_knowledge"
    assert result["document_count"] == 10


def test_quiet_study_semantic_retrieval():
    """Test a natural-language quiet study query retrieves a relevant resource."""
    result = retrieve_resource_context(
        "I need somewhere quiet to study.",
        top_k=3,
    )

    assert result["query"] == "I need somewhere quiet to study."
    assert result["top_k"] == 3
    assert len(result["matches"]) == 3

    top_match = result["matches"][0]

    assert top_match["resource_name"] == "Building 1 Quiet Study Area"
    assert top_match["source"] == "campus_resources.txt"
    assert top_match["confidence"] == "high"
    assert "citation" in top_match
    assert "context" in top_match


def test_printing_semantic_retrieval():
    """Test a printing query ranks printer resources highly."""
    result = retrieve_resource_context(
        "Where can I print my assignment?",
        top_k=3,
    )

    top_two_names = [
        match["resource_name"]
        for match in result["matches"][:2]
    ]

    assert "Building 11 Printer" in top_two_names
    assert "Building 2 Printer" in top_two_names


def test_computer_semantic_retrieval():
    """Test a computer query retrieves a Computer Lab first."""
    result = retrieve_resource_context(
        "I need a computer to complete my assignment.",
        top_k=3,
    )

    top_match = result["matches"][0]

    assert top_match["resource_name"] == "Building 10 Computer Lab"
    assert top_match["confidence"] == "medium"


def test_resource_confidence_thresholds():
    """Test the Student 3 retrieval confidence thresholds."""
    assert get_confidence(0.40) == "high"
    assert get_confidence(0.60) == "medium"
    assert get_confidence(0.80) == "low"


def test_resource_retrieval_requires_query():
    """Test validation when no resource query is supplied."""
    result = retrieve_resource_context("")

    assert result["error"] == "query is required"
    assert result["matches"] == []


# =========================================================
# BACKEND RAG ENDPOINT TESTS
# =========================================================

BACKEND_DIR = os.path.join(
    PROJECT_ROOT,
    "student-3",
    "backend",
)

sys.path.insert(
    0,
    BACKEND_DIR,
)

from app import app


def test_backend_rag_recommend_success(monkeypatch):
    """Test the backend returns a grounded RAG answer with evidence."""

    def mock_retrieve_resource_context(query, top_k=3):
        return {
            "query": query,
            "top_k": top_k,
            "matches": [
                {
                    "resource_name": "Building 1 Quiet Study Area",
                    "source": "campus_resources.txt",
                    "citation": (
                        "campus_resources.txt#"
                        "Building-1-Quiet-Study-Area"
                    ),
                    "confidence": "high",
                    "distance": 0.431,
                    "context": (
                        "Quiet study area for individual study."
                    ),
                }
            ],
        }

    class MockAiResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "response": (
                    "Building 1 Quiet Study Area is suitable "
                    "for quiet individual study."
                )
            }

    def mock_ai_post(*args, **kwargs):
        return MockAiResponse()

    monkeypatch.setattr(
        "app.retrieve_resource_context",
        mock_retrieve_resource_context,
    )

    monkeypatch.setattr(
        "app.requests.post",
        mock_ai_post,
    )

    client = app.test_client()

    response = client.post(
        "/rag/recommend",
        json={
            "question": "I need somewhere quiet to study."
        },
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["mode"] == "rag"
    assert data["question"] == "I need somewhere quiet to study."

    assert (
        data["answer"]
        == (
            "Building 1 Quiet Study Area is suitable "
            "for quiet individual study."
        )
    )

    assert data["confidence"] == "high"

    assert data["citations"] == [
        (
            "campus_resources.txt#"
            "Building-1-Quiet-Study-Area"
        )
    ]

    assert len(data["matches"]) == 1

    assert (
        data["matches"][0]["resource_name"]
        == "Building 1 Quiet Study Area"
    )

    assert data["matches"][0]["confidence"] == "high"


def test_backend_rag_recommend_requires_question():
    """Test validation when the backend receives an empty RAG question."""

    client = app.test_client()

    response = client.post(
        "/rag/recommend",
        json={
            "question": ""
        },
    )

    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "question is required"


def test_backend_rag_recommend_handles_rag_failure(monkeypatch):
    """Test the backend handles an unavailable RAG service."""

    def mock_rag_failure(query, top_k=3):
        return {
            "error": "RAG server unavailable",
            "matches": [],
        }

    monkeypatch.setattr(
        "app.retrieve_resource_context",
        mock_rag_failure,
    )

    client = app.test_client()

    response = client.post(
        "/rag/recommend",
        json={
            "question": "Where can I study?"
        },
    )

    data = response.get_json()

    assert response.status_code == 503
    assert data["error"] == "RAG server unavailable"
    assert data["matches"] == []


def test_backend_rag_recommend_insufficient_context(monkeypatch):
    """Test the backend does not generate an answer from weak RAG context."""

    def mock_low_confidence_context(query, top_k=3):
        return {
            "query": query,
            "top_k": top_k,
            "matches": [
                {
                    "resource_name": "Thomas Street Parking",
                    "source": "campus_resources.txt",
                    "citation": (
                        "campus_resources.txt#"
                        "Thomas-Street-Parking"
                    ),
                    "confidence": "low",
                    "distance": 0.91,
                    "context": "Campus parking information.",
                }
            ],
        }

    def fail_if_ai_called(*args, **kwargs):
        raise AssertionError(
            "AI should not be called when RAG context is insufficient."
        )

    monkeypatch.setattr(
        "app.retrieve_resource_context",
        mock_low_confidence_context,
    )

    monkeypatch.setattr(
        "app.requests.post",
        fail_if_ai_called,
    )

    client = app.test_client()

    response = client.post(
        "/rag/recommend",
        json={
            "question": "What is the best restaurant in Sydney?"
        },
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["mode"] == "rag"
    assert data["confidence"] == "low"
    assert data["citations"] == []

    assert (
        data["answer"]
        == (
            "Insufficient relevant context was found "
            "to answer this question."
        )
    )