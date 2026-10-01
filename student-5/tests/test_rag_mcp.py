import requests

BACKEND_URL = "http://127.0.0.1:8005"
MCP_URL = "http://127.0.0.1:9001/mcp"
RAG_URL = "http://127.0.0.1:9101"


def test_mcp_server_is_reachable():
    response = requests.get(MCP_URL, timeout=10)
    assert response.status_code < 500


def test_rag_is_reachable():
    response = requests.post(
        f"{RAG_URL}/retrieve/career",
        json={
            "query": "How should I prepare for the interview?",
            "top_k": 4,
        },
        timeout=30,
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)