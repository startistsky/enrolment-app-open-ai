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