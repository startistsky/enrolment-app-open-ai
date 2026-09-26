import os
import sys


BACKEND_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "backend",
    )
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


import app


def test_backend_mcp_resource_count_success(monkeypatch):
    """The backend should return the MCP resource_count result."""

    def fake_call_mcp_tool(tool_name, arguments=None):
        assert tool_name == "resource_count"
        assert arguments is None

        return {
            "ok": True,
            "result": {
                "resource_count": 10
            },
        }

    monkeypatch.setattr(
        app,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    client = app.app.test_client()

    response = client.get(
        "/api/mcp/resource-count"
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["mode"] == "mcp"
    assert data["tool"] == "resource_count"
    assert data["result"]["resource_count"] == 10


def test_backend_mcp_resource_by_type_success(monkeypatch):
    """The backend should pass the resource type to the MCP tool."""

    def fake_call_mcp_tool(tool_name, arguments=None):
        assert tool_name == "resource_by_type"
        assert arguments == {
            "resource_type": "Printer"
        }

        return {
            "ok": True,
            "result": {
                "resource_type": "Printer",
                "resource_count": 2,
                "resources": [
                    {
                        "resource_name": "Building 2 Printer",
                        "resource_type": "Printer",
                    },
                    {
                        "resource_name": "Building 11 Printer",
                        "resource_type": "Printer",
                    },
                ],
            },
        }

    monkeypatch.setattr(
        app,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    client = app.app.test_client()

    response = client.get(
        "/api/mcp/resource-by-type/Printer"
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["mode"] == "mcp"
    assert data["tool"] == "resource_by_type"
    assert data["input"]["resource_type"] == "Printer"
    assert data["result"]["resource_count"] == 2

    resource_names = [
        resource["resource_name"]
        for resource in data["result"]["resources"]
    ]

    assert resource_names == [
        "Building 2 Printer",
        "Building 11 Printer",
    ]


def test_backend_mcp_resource_count_handles_unavailable_server(
    monkeypatch,
):
    """The backend should expose a clear 503 when MCP is unavailable."""

    def fake_call_mcp_tool(tool_name, arguments=None):
        return {
            "ok": False,
            "status": 503,
            "error": "MCP server unavailable",
            "detail": "Connection failed",
        }

    monkeypatch.setattr(
        app,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    client = app.app.test_client()

    response = client.get(
        "/api/mcp/resource-count"
    )

    data = response.get_json()

    assert response.status_code == 503
    assert data["error"] == "MCP server unavailable"
    assert data["detail"] == "Connection failed"


def test_backend_mcp_resource_by_type_handles_tool_failure(
    monkeypatch,
):
    """The backend should propagate an MCP tool failure safely."""

    def fake_call_mcp_tool(tool_name, arguments=None):
        assert tool_name == "resource_by_type"
        assert arguments == {
            "resource_type": "Printer"
        }

        return {
            "ok": False,
            "status": 502,
            "error": "MCP tool invocation failed",
            "detail": "Tool returned an error",
        }

    monkeypatch.setattr(
        app,
        "call_mcp_tool",
        fake_call_mcp_tool,
    )

    client = app.app.test_client()

    response = client.get(
        "/api/mcp/resource-by-type/Printer"
    )

    data = response.get_json()

    assert response.status_code == 502
    assert data["error"] == "MCP tool invocation failed"
    assert data["detail"] == "Tool returned an error"