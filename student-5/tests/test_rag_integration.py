from unittest.mock import Mock, patch

def test_chunk_text():
    from retrievers.student5_career_retriever import (
    chunk_text,
    )

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


def test_chunk_text_empty():
    from retrievers.student5_career_retriever import (
    chunk_text,
    )

    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_load_knowledge():
    from retrievers import student5_career_retriever as retriever

    mock_file = Mock()

    mock_file.stem = "resume_guidance"
    mock_file.name = "resume_guidance.txt"

    mock_file.read_text.return_value = (
        "A resume should present information relevant "
        "to the position being applied for."
    )

    with patch.object(
        retriever.KNOWLEDGE_DIR,
        "exists",
        return_value=True,
    ), patch.object(
        retriever.KNOWLEDGE_DIR,
        "glob",
        return_value=[mock_file],
    ):

        documents = retriever.load_knowledge()

    assert len(documents) > 0

    document = documents[0]

    assert document["source"] == (
        "resume_guidance.txt"
    )
    assert document["chunk"] == 0
    assert "resume" in document["text"].lower()


def test_retrieve():
    from retrievers import student5_career_retriever as retriever

    mock_result = {
        "documents": [[
            "A resume should contain relevant skills."
        ]],
        "metadatas": [[
            {
                "source": "resume_guidance.txt",
                "chunk": 0,
            }
        ]],
        "distances": [[
            0.47
        ]],
    }

    with patch.object(
        retriever._collection,
        "query",
        return_value=mock_result,
    ) as mock_query:

        results = retriever.retrieve(
            "How should I prepare a resume?",
            top_k=4,
        )

    mock_query.assert_called_once_with(
        query_texts=[
            "How should I prepare a resume?"
        ],
        n_results=4,
    )

    assert len(results) == 1
    assert results[0]["source"] == (
        "resume_guidance.txt"
    )
    assert results[0]["chunk"] == 0
    assert results[0]["distance"] == 0.47


def test_retrieve_empty_query():
    from retrievers import student5_career_retriever as retriever

    with patch.object(
        retriever._collection,
        "query",
    ) as mock_query:

        result = retriever.retrieve("")

    mock_query.assert_not_called()

    assert result == []


def test_retrieve_context():
    from retrievers import student5_career_retriever as retriever

    mock_results = [
        {
            "text": (
                "A resume should contain relevant skills."
            ),
            "source": "resume_guidance.txt",
            "chunk": 0,
            "distance": 0.47,
        },
        {
            "text": (
                "Use terminology from the job "
                "advertisement."
            ),
            "source": "ats_guidance.txt",
            "chunk": 0,
            "distance": 0.51,
        },
    ]

    with patch.object(
        retriever,
        "retrieve",
        return_value=mock_results,
    ):

        result = retriever.retrieve_context(
            "How should I prepare my resume?"
        )

    assert result["confidence"] == "medium"

    assert "resume_guidance.txt" in result["sources"]
    assert "ats_guidance.txt" in result["sources"]

    assert (
        "A resume should contain relevant skills."
        in result["context"]
    )

    assert (
        "Use terminology from the job advertisement."
        in result["context"]
    )

    assert len(result["results"]) == 2


def test_retrieve_context_no_results():
    from retrievers import student5_career_retriever as retriever

    with patch.object(
        retriever,
        "retrieve",
        return_value=[],
    ):

        result = retriever.retrieve_context(
            "unrelated query"
        )

    assert result["context"] == ""
    assert result["sources"] == []
    assert result["confidence"] == "low"
    assert result["results"] == []


def test_retrieve_career_context():
    from retrievers import student5_career_retriever as retriever

    expected = {
        "context": "career context",
        "sources": ["resume_guidance.txt"],
        "confidence": "high",
        "results": [],
    }

    with patch.object(
        retriever,
        "retrieve_context",
        return_value=expected,
    ):

        result = retriever.retrieve_career_context(
            "resume preparation"
        )

    assert result == expected


def test_rag_status():
    from retrievers import student5_career_retriever as retriever

    with patch.object(
        retriever._collection,
        "count",
        return_value=6,
    ):

        result = retriever.rag_status()

    assert result["success"] is True
    assert result["available"] is True
    assert result["collection"] == (
        "student5_career_knowledge"
    )
    assert result["documents"] == 6
    assert result["embedding_model"] == (
        "all-MiniLM-L6-v2"
    )