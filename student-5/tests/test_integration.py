import requests

BACKEND_URL = "http://127.0.0.1:8005"
MCP_URL = "http://127.0.0.1:9001"


def test_mcp_server_is_reachable():
    response = requests.get(MCP_URL, timeout=10)
    assert response.status_code < 500


def test_career_agent_rag_is_reachable():
    response = requests.post(
        f"{BACKEND_URL}/api/jobs/1/agent",
        json={"message": "How should I prepare for the interview?"},
        timeout=120,
    )

    assert response.status_code == 200
