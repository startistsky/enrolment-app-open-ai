import sys
from pathlib import Path
import importlib.util

import pytest
import requests
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Define path 
MCP_PATH = (
    PROJECT_ROOT
    / "mcp-server"
    / "tools"
    / "student5_career_tools.py"
)

# Load Student 5 MCP module
if not MCP_PATH.exists():
    pytest.fail(
        f"Student 5 MCP not found: {MCP_PATH}"
    )

spec = importlib.util.spec_from_file_location(
    "student5_career_tools",
    MCP_PATH,
)

if spec is None or spec.loader is None:
    pytest.fail(
        f"Could not load Student 5 MCP module: {MCP_PATH}"
    )


student5_career_tools = (
    importlib.util.module_from_spec(spec)
)

sys.modules[
    "student5_career_tools"
] = student5_career_tools

spec.loader.exec_module(
    student5_career_tools
)

# Define MCP functions
get_backend_job = (
    student5_career_tools.get_backend_job
)

get_selected_job = (
    student5_career_tools.get_selected_job
)

get_job_requirements = (
    student5_career_tools.get_job_requirements
)

analyse_selected_job = (
    student5_career_tools.analyse_selected_job
)

retrieve_career_knowledge = (
    student5_career_tools.retrieve_career_knowledge
)

mcp = student5_career_tools.mcp

BACKEND_URL = student5_career_tools.BACKEND_URL
RAG_URL = student5_career_tools.RAG_URL


def test_get_backend_job_success():
    mock_response = Mock()

    mock_response.json.return_value = {
        "id": 1,
        "title": "Python Developer",
        "company": "Example Company",
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "student5_career_tools.requests.get",
        return_value=mock_response,
    ) as mock_get:

        result = get_backend_job(1)

    assert result["id"] == 1
    assert result["title"] == "Python Developer"
    assert result["company"] == "Example Company"

    mock_get.assert_called_once_with(
        f"{BACKEND_URL}/api/jobs/1",
        timeout=10,
    )


def test_get_backend_job_request_failure():
    with patch(
        "student5_career_tools.requests.get",
        side_effect=requests.RequestException(
            "Backend unavailable"
        ),
    ):

        with pytest.raises(
            requests.RequestException
        ):
            get_backend_job(1)


def test_get_backend_job_http_error():
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = (
        requests.HTTPError("404 Not Found")
    )

    with patch(
        "student5_career_tools.requests.get",
        return_value=mock_response,
    ):

        with pytest.raises(
            requests.HTTPError
        ):
            get_backend_job(1)

def test_get_selected_job_success():
    job = {
        "id": 1,
        "title": "Python Developer",
        "company": "Example Company",
    }

    with patch(
        "student5_career_tools.get_backend_job",
        return_value=job,
    ) as mock_get_job:

        result = get_selected_job(1)

    assert result["success"] is True
    assert result["job"] == job

    mock_get_job.assert_called_once_with(1)


def test_get_selected_job_backend_failure():
    with patch(
        "student5_career_tools.get_backend_job",
        side_effect=requests.RequestException(
            "Backend unavailable"
        ),
    ):

        result = get_selected_job(1)

    assert result["success"] is False
    assert "error" in result
    assert "Backend unavailable" in result["error"]

def test_get_job_requirements_success():
    job = {
        "id": 1,
        "title": "Python Developer",
        "company": "Example Company",
        "requirements": "Python, FastAPI, SQL",
        "description": "Backend development role.",
    }

    with patch(
        "student5_career_tools.get_backend_job",
        return_value=job,
    ) as mock_get_job:

        result = get_job_requirements(1)

    assert result["success"] is True
    assert result["job_id"] == 1
    assert result["title"] == "Python Developer"
    assert result["company"] == "Example Company"
    assert result["requirements"] == (
        "Python, FastAPI, SQL"
    )
    assert result["description"] == (
        "Backend development role."
    )

    mock_get_job.assert_called_once_with(1)


def test_get_job_requirements_missing_optional_fields():
    job = {
        "id": 2,
        "title": "Data Analyst",
    }

    with patch(
        "student5_career_tools.get_backend_job",
        return_value=job,
    ):

        result = get_job_requirements(2)

    assert result["success"] is True
    assert result["job_id"] == 2
    assert result["title"] == "Data Analyst"
    assert result["company"] == ""
    assert result["requirements"] == ""
    assert result["description"] == ""


def test_get_job_requirements_backend_failure():
    with patch(
        "student5_career_tools.get_backend_job",
        side_effect=requests.RequestException(
            "Backend unavailable"
        ),
    ):

        result = get_job_requirements(1)

    assert result["success"] is False
    assert "error" in result
    assert "Backend unavailable" in result["error"]

def test_analyse_selected_job_success():
    mock_response = Mock()

    mock_response.json.return_value = {
        "success": True,
        "job_id": 1,
        "analysis": "Strong Python match.",
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = analyse_selected_job(1)

    assert result["success"] is True
    assert result["job_id"] == 1
    assert result["analysis"] == (
        "Strong Python match."
    )

    mock_post.assert_called_once_with(
        f"{BACKEND_URL}/api/jobs/1/analyse",
        timeout=120,
    )


def test_analyse_selected_job_backend_failure():
    with patch(
        "student5_career_tools.requests.post",
        side_effect=requests.RequestException(
            "Analysis service unavailable"
        ),
    ):

        result = analyse_selected_job(1)

    assert result["success"] is False
    assert "error" in result
    assert "Analysis service unavailable" in result["error"]


def test_analyse_selected_job_http_error():
    mock_response = Mock()

    mock_response.raise_for_status.side_effect = (
        requests.HTTPError("Analysis endpoint failed")
    )

    with patch(
        "student5_career_tools.requests.post",
        return_value=mock_response,
    ):

        result = analyse_selected_job(1)

    assert result["success"] is False
    assert "error" in result


def test_retrieve_career_knowledge_empty_query():
    result = retrieve_career_knowledge("")

    assert result["success"] is False
    assert result["error"] == "Query is required."


def test_retrieve_career_knowledge_whitespace_query():
    result = retrieve_career_knowledge("   ")

    assert result["success"] is False
    assert result["error"] == "Query is required."


def test_retrieve_career_knowledge_none_query():
    result = retrieve_career_knowledge(None)

    assert result["success"] is False
    assert result["error"] == "Query is required."


def test_retrieve_career_knowledge_success():
    mock_response = Mock()

    mock_response.json.return_value = {
        "context": (
            "Python is commonly used in "
            "backend development."
        ),
        "sources": [
            "career-skills.txt"
        ],
        "confidence": "high",
        "results": [
            {
                "text": (
                    "Python is commonly used in "
                    "backend development."
                ),
                "source": "career-skills.txt",
                "chunk": 0,
                "distance": 0.2,
            }
        ],
    }

    mock_response.raise_for_status.return_value = None

    query = (
        "What skills are needed for "
        "backend development?"
    )

    with patch(
        "student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = retrieve_career_knowledge(
            query,
            top_k=4,
        )

    assert result["success"] is True
    assert result["context"]
    assert result["sources"]
    assert result["confidence"] == "high"
    assert result["results"]

    mock_post.assert_called_once_with(
        f"{RAG_URL}/retrieve/career",
        json={
            "query": query,
            "top_k": 4,
        },
        timeout=30,
    )


def test_retrieve_career_knowledge_strips_query():
    mock_response = Mock()

    mock_response.json.return_value = {
        "context": "Career information.",
        "sources": [
            "career.txt"
        ],
        "confidence": "medium",
        "results": [],
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = retrieve_career_knowledge(
            "  career planning  ",
            top_k=2,
        )

    assert result["success"] is True

    mock_post.assert_called_once_with(
        f"{RAG_URL}/retrieve/career",
        json={
            "query": "career planning",
            "top_k": 2,
        },
        timeout=30,
    )


def test_retrieve_career_knowledge_rag_failure():
    with patch(
        "student5_career_tools.requests.post",
        side_effect=requests.RequestException(
            "RAG server unavailable"
        ),
    ):

        result = retrieve_career_knowledge(
            "career planning"
        )

    assert result["success"] is False
    assert "error" in result
    assert "RAG server unavailable" in result["error"]


def test_retrieve_career_knowledge_top_k():
    mock_response = Mock()

    mock_response.json.return_value = {
        "context": "Career information.",
        "sources": [
            "career.txt"
        ],
        "confidence": "high",
        "results": [],
    }

    mock_response.raise_for_status.return_value = None

    with patch(
        "student5_career_tools.requests.post",
        return_value=mock_response,
    ) as mock_post:

        result = retrieve_career_knowledge(
            "Python careers",
            top_k=8,
        )

    assert result["success"] is True

    mock_post.assert_called_once_with(
        f"{RAG_URL}/retrieve/career",
        json={
            "query": "Python careers",
            "top_k": 8,
        },
        timeout=30,
    )


# Check MCP server
def test_mcp_server_exists():
    assert mcp is not None


def test_mcp_server_has_expected_name():
    # FastMCP exposes the configured server name.
    assert mcp.name == "Student5 Career Tools"


def test_mcp_expected_tools_exist():
    assert callable(get_selected_job)
    assert callable(get_job_requirements)
    assert callable(analyse_selected_job)
    assert callable(retrieve_career_knowledge)
