import sys
from pathlib import Path
import importlib.util

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Define rag-server path 
RETRIEVER_PATH = (
    PROJECT_ROOT
    / "rag-server"
    / "retrievers"
    / "student5_career_retriever.py"
)

# Load retriever module
if not RETRIEVER_PATH.exists():
    pytest.fail(
        f"Student 5 RAG retriever not found: "
        f"{RETRIEVER_PATH}"
    )

spec = importlib.util.spec_from_file_location(
    "student5_career_retriever",
    RETRIEVER_PATH,
)

if spec is None or spec.loader is None:
    pytest.fail(
        f"Could not load retriever module: "
        f"{RETRIEVER_PATH}"
    )


retriever = importlib.util.module_from_spec(spec)

sys.modules[
    "student5_career_retriever"
] = retriever

spec.loader.exec_module(retriever)

# Retriever imports
KNOWLEDGE_DIR = retriever.KNOWLEDGE_DIR
COLLECTION_NAME = retriever.COLLECTION_NAME
EMBEDDING_MODEL = retriever.EMBEDDING_MODEL

chunk_text = retriever.chunk_text
load_knowledge = retriever.load_knowledge
index_knowledge = retriever.index_knowledge
retrieve = retriever.retrieve
retrieve_context = retriever.retrieve_context
retrieve_career_context = retriever.retrieve_career_context
rag_status = retriever.rag_status

# Knowledge tests
def test_knowledge_directory_exists():
    assert KNOWLEDGE_DIR.exists()
    assert KNOWLEDGE_DIR.is_dir()


def test_knowledge_files_exist():
    files = list(
        KNOWLEDGE_DIR.glob("*.txt")
    )

    assert files, (
        f"No .txt knowledge files found in "
        f"{KNOWLEDGE_DIR}"
    )

# Chunking tests
def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_creates_chunks():
    text = " ".join(
        f"word{i}"
        for i in range(100)
    )

    chunks = chunk_text(
        text,
        chunk_size=20,
        overlap=5,
    )

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk
        assert isinstance(
            chunk,
            str,
        )


def test_chunk_text_has_overlap():
    text = " ".join(
        f"word{i}"
        for i in range(50)
    )

    chunks = chunk_text(
        text,
        chunk_size=10,
        overlap=3,
    )

    assert len(chunks) > 1

    first = chunks[0].split()
    second = chunks[1].split()

    assert first[-3:] == second[:3]

# RAG health
def test_rag_status():
    result = rag_status()

    assert isinstance(
        result,
        dict,
    )

    assert "success" in result
    assert "available" in result

    if result["success"]:
        assert result["available"] is True

        assert (
            result["collection"]
            == COLLECTION_NAME
        )

        assert (
            result["embedding_model"]
            == EMBEDDING_MODEL
        )

        assert result["documents"] >= 0

# Retrieval
def test_retrieve_empty_query():
    assert retrieve("") == []
    assert retrieve("   ") == []


def test_retrieve_returns_results():
    index_knowledge()

    results = retrieve(
        "What skills are required for a job?",
        top_k=4,
    )

    assert isinstance(
        results,
        list,
    )

    assert len(results) <= 4
    assert results

    for result in results:
        assert "text" in result
        assert "source" in result
        assert "chunk" in result
        assert "distance" in result

        assert result["text"]
        assert result["source"]


def test_retrieve_respects_top_k():
    index_knowledge()

    results = retrieve(
        "career",
        top_k=2,
    )

    assert len(results) <= 2

# Context
def test_retrieve_context():
    index_knowledge()

    result = retrieve_context(
        "What skills do I need?",
        top_k=4,
    )

    assert isinstance(
        result,
        dict,
    )

    assert "context" in result
    assert "sources" in result
    assert "confidence" in result
    assert "results" in result

    assert isinstance(
        result["context"],
        str,
    )

    assert isinstance(
        result["sources"],
        list,
    )

    assert isinstance(
        result["results"],
        list,
    )

    assert result["confidence"] in {
        "low",
        "medium",
        "high",
    }


def test_retrieve_context_contains_source_labels():
    index_knowledge()

    result = retrieve_context(
        "career planning",
        top_k=2,
    )

    if not result["results"]:
        pytest.skip(
            "No RAG results returned"
        )

    assert "SOURCE 1:" in result["context"]
