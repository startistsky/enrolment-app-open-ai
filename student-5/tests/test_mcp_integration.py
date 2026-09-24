from unittest.mock import Mock, patch

def test_mcp_server_imports():
    """
    Verify the MCP server can be imported and created.
    """

    from mcp.server import MCPServer

    server = MCPServer("Smart Campus MCP")

    assert server is not None


def test_career_get_selected_job():
    """
    MCP career job tool -> backend.
    """

    from tools.student5_career_tools import get_selected_job

    mock_response = Mock()

    mock_response.json.return_value = {
        "id": 11,
        "title": "Software Engineer",
        "company": "Example Company",
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "tools.student5_career_tools.requests.get",
        return_value=mock_response,
    ) as mock_get:

        result = get_selected_job(11)

    mock_get.assert_called_once_with(
        "http://127.0.0.1:8005/api/jobs/11",
        timeout=10,
    )

    assert result["success"] is True
    assert result["job"]["id"] == 11
    assert result["job"]["title"] == "Software Engineer"


def test_career_get_job_requirements():
    """
    MCP career requirements tool -> backend.
    """

    from tools.student5_career_tools import (
        get_job_requirements,
    )

    mock_response = Mock()

    mock_response.json.return_value = {
        "id": 11,
        "title": "Graduate Software Engineer",
        "company": "Test Company",
        "requirements": "Python, SQL",
        "description": "Build software applications.",
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "tools.student5_career_tools.requests.get",
        return_value=mock_response,
    ):

        result = get_job_requirements(11)

    assert result["success"] is True
    assert result["job_id"] == 11
    assert result["title"] == "Software Engineer"
    assert result["company"] == "Example Company"
    assert result["requirements"] == "Python, SQL"
    assert result["description"] == (
        "Build software applications."
    )


def test_career_analyse_selected_job():
    """
    MCP job analysis tool -> backend AI analysis endpoint.
    """

    from tools.student5_career_tools import (
        analyse_selected_job,
    )

    mock_response = Mock()

    mock_response.json.return_value = {
        "skills": ["Python", "SQL"],
        "qualifications": ["Degree"],
        "experience": ["Software development"],
        "ats_keywords": ["Python", "SQL"],
        "summary": "Software engineering requirements.",
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "tools.student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = analyse_selected_job(11)

    mock_post.assert_called_once_with(
        "http://127.0.0.1:8005/api/jobs/11/analyse",
        timeout=120,
    )

    assert result["skills"] == ["Python", "SQL"]
    assert result["qualifications"] == ["Degree"]
    assert result["experience"] == [
        "Software development"
    ]
    assert result["ats_keywords"] == ["Python", "SQL"]
    assert "summary" in result


def test_career_retrieve_knowledge():
    """
    MCP career RAG tool -> RAG server.
    """

    from tools.student5_career_tools import (
        retrieve_career_knowledge,
    )

    mock_response = Mock()

    mock_response.json.return_value = {
        "confidence": "high",
        "context": "Resume guidance...",
        "sources": [
            "resume_guidance.txt",
        ],
        "results": [
            {
                "source": "resume_guidance.txt",
                "chunk": 0,
                "text": (
                    "A resume should present relevant "
                    "information."
                ),
                "distance": 0.47,
            }
        ],
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "tools.student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = retrieve_career_knowledge(
            "How should I prepare my resume?",
            4,
        )

    mock_post.assert_called_once_with(
        "http://127.0.0.1:9101/retrieve/career",
        json={
            "query": "How should I prepare my resume?",
            "top_k": 4,
        },
        timeout=30,
    )

    assert result["confidence"] == "high"
    assert "resume_guidance.txt" in result["sources"]
    assert len(result["results"]) == 1


def test_career_retrieve_knowledge_empty_query():
    """
    Empty RAG queries must not reach the RAG server.
    """

    from tools.student5_career_tools import (
        retrieve_career_knowledge,
    )

    with patch(
        "tools.student5_career_tools.requests.post"
    ) as mock_post:

        result = retrieve_career_knowledge("")

    mock_post.assert_not_called()

    assert result["success"] is False
    assert result["error"] == "Query is required."


def test_mcp_career_tool_functions_are_available():
    """
    Verify the Student 5 MCP wrapper functions exist.
    """

    import server

    expected = [
        "career_get_selected_job",
        "career_get_job_requirements",
        "career_analyse_selected_job",
        "career_retrieve_knowledge",
    ]

    for name in expected:
        assert hasattr(server, name)
        assert callable(getattr(server, name))