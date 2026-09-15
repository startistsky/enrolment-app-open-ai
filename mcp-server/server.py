import sys

from mcp.server import MCPServer

from tools.student1_course_tools import (
    get_course_by_code,
    get_course_count,
)

from tools.student4_event_tools import (
    get_event_count,
    get_event_by_title,
)

from tools.shared_tools import (
    list_project_files,
    read_ci_report,
)


mcp = MCPServer("Smart Campus MCP")

AVAILABLE_TOOLS = [
    "course_count",
    "course_by_code",
    "event_count",
    "event_by_title",
    "project_files",
    "ci_report",
]


@mcp.tool()
def course_count():
    """Return the total number of Course Management records."""
    return get_course_count()


@mcp.tool()
def course_by_code(course_code: str):
    """Return a Course Management record matching the supplied course code."""
    return get_course_by_code(course_code)


@mcp.tool()
def event_count():
    """Return the total number of Campus Event records."""
    return get_event_count()


@mcp.tool()
def event_by_title(event_title: str):
    """Return a Campus Event record matching the supplied title."""
    return get_event_by_title(event_title)


@mcp.tool()
def project_files(directory_path: str = ".."):
    """List direct children of a directory inside the project repository."""
    return list_project_files(directory_path)


@mcp.tool()
def ci_report(report_path: str = "../reports/report.json"):
    """Read the CI evidence JSON report when it is available."""
    return read_ci_report(report_path)


if __name__ == "__main__":
    print("Starting Smart Campus MCP Server...", file=sys.stderr)
    print("Server status: RUNNING", file=sys.stderr)
    print("Transport: Streamable HTTP", file=sys.stderr)
    print("MCP endpoint: http://localhost:9001/mcp", file=sys.stderr)
    print("Available tools:", file=sys.stderr)

    for tool_name in AVAILABLE_TOOLS:
        print(f"- {tool_name}", file=sys.stderr)

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=9001,
        streamable_http_path="/mcp",
    )