import sys

from mcp.server import MCPServer

from tools.student1_course_tools import (
    get_course_by_code,
    get_course_count,
)

from tools.student3_resource_tools import (
    get_resource_by_type,
    get_resource_count,
)

from tools.student4_event_tools import (
    get_event_count,
    get_event_by_title,
)

from tools.shared_tools import (
    list_project_files,
    read_ci_report,
)

from tools.student5_career_tools import (
    get_selected_job,
    get_job_requirements,
    analyse_selected_job,
)

mcp = MCPServer("Smart Campus MCP")

AVAILABLE_TOOLS = [
    "course_count",
    "course_by_code",
    "resource_count",
    "resource_by_type",
    "event_count",
    "event_by_title",
    "project_files",
    "ci_report",
    "career_get_job_mcp",
    "career_get_job_requirements_mcp",
    "career_analyse_selected_job_mcp",
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
def resource_count():
    """Return the total number of Campus Resource records."""
    return get_resource_count()


@mcp.tool()
def resource_by_type(resource_type: str):
    """Return Campus Resource records matching the supplied resource type."""
    return get_resource_by_type(resource_type)


@mcp.tool()
def event_count():
    """Return the total number of Campus Event records."""
    return get_event_count()

@mcp.tool()
def event_by_title(event_title: str):
    """Return a Campus Event record matching the supplied title."""
    return get_event_by_title(event_title)

# student 5 tools
@mcp.tool()
def career_get_job_mcp(job_id: int):
    """Get complete information about a selected career job."""
    return get_selected_job(job_id)

@mcp.tool()
def career_get_job_requirements_mcp(job_id: int):
    """Get requirements and description of a selected job."""
    return get_job_requirements(job_id)

@mcp.tool()
def career_analyse_selected_job_mcp(job_id: int):
    """Analyse the selected career job."""
    return analyse_selected_job(job_id)

# general tools
@mcp.tool()
def project_files(directory_path: str = ".."):
    """List direct children of a directory inside the project repository."""
    return list_project_files(directory_path)


@mcp.tool()
def ci_report(report_path: str = "../reports/report.json"):
    """Read the CI evidence JSON report when it is available."""
    return read_ci_report(report_path)

# main
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