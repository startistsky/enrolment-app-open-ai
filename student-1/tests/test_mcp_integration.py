from unittest.mock import Mock


def test_mcp_course_count_success(backend_app, backend_client, monkeypatch):
    call_mcp_tool = Mock(return_value={
        "ok": True,
        "result": {"course_count": 11},
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.get("/api/mcp/course-count")

    assert response.status_code == 200
    assert response.get_json()["tool"] == "course_count"
    assert response.get_json()["result"]["course_count"] == 11
    call_mcp_tool.assert_called_once_with("course_count", None)


def test_mcp_course_by_code_success(backend_app, backend_client, monkeypatch):
    course = {
        "course_id": 1,
        "course_code": "COMP1001",
        "course_name": "Introduction to Information Technology",
        "lecturer": "Dr. John Smith",
        "semester": "Spring 2026",
        "credit_points": 6,
        "course_description": "Introduction to core information technology concepts.",
    }
    call_mcp_tool = Mock(return_value={"ok": True, "result": course})
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.get("/api/mcp/course-by-code/COMP1001")

    assert response.status_code == 200
    assert response.get_json()["tool"] == "course_by_code"
    assert response.get_json()["result"]["course_code"] == "COMP1001"
    call_mcp_tool.assert_called_once_with(
        "course_by_code",
        {"course_code": "COMP1001"},
    )


def test_mcp_project_files_success(backend_app, backend_client, monkeypatch):
    project_files = [
        ".github",
        "docker-compose.yml",
        "mcp-server",
        "student-1",
    ]
    call_mcp_tool = Mock(return_value={
        "ok": True,
        "result": project_files,
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.get("/api/mcp/project-files")

    assert response.status_code == 200
    assert response.get_json()["tool"] == "project_files"
    assert response.get_json()["result"] == project_files
    call_mcp_tool.assert_called_once_with(
        "project_files",
        {"directory_path": ".."},
    )


def test_mcp_ci_report_success(backend_app, backend_client, monkeypatch):
    ci_report = {"status": "passed", "tests": 9}
    call_mcp_tool = Mock(return_value={
        "ok": True,
        "result": ci_report,
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.get("/api/mcp/ci-report")

    assert response.status_code == 200
    assert response.get_json()["tool"] == "ci_report"
    assert response.get_json()["result"] == ci_report
    call_mcp_tool.assert_called_once_with(
        "ci_report",
        {"report_path": "../reports/report.json"},
    )


def test_mcp_server_unavailable_returns_503(
    backend_app,
    backend_client,
    monkeypatch,
):
    call_mcp_tool = Mock(return_value={
        "ok": False,
        "status": 503,
        "error": "MCP server unavailable",
        "detail": "connection failed",
    })
    monkeypatch.setattr(backend_app, "call_mcp_tool", call_mcp_tool)

    response = backend_client.get("/api/mcp/course-count")

    assert response.status_code == 503
    assert response.get_json()["error"] == "MCP server unavailable"


def test_mcp_protocol_failure_returns_502(
    backend_app,
    backend_client,
    monkeypatch,
):
    error_result = {
        "ok": False,
        "status": 502,
        "error": "MCP protocol or tool invocation failed",
        "detail": "invalid MCP response",
    }
    monkeypatch.setattr(
        backend_app,
        "call_mcp_tool",
        Mock(return_value=error_result),
    )

    response = backend_client.get("/api/mcp/course-count")

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "MCP protocol or tool invocation failed",
        "detail": "invalid MCP response",
    }
