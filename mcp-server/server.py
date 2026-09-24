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

from tools.student5_career_tools import (
    get_job,
    get_job_requirements,
    get_saved_jobs,
    get_application,
    get_resume,
    save_job,
    create_application,
    update_application
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

# student 5 tools
@mcp.tool()
def career_get_job(job_id: int):
    """Get complete information about a selected career job."""
    return get_job(job_id)

@mcp.tool()
def career_get_job_requirements(job_id: int):
    """Get the requirements and description of a selected job."""
    return get_job_requirements(job_id)

@mcp.tool()
def career_get_saved_jobs():
    """Get the user's saved jobs."""
    return get_saved_jobs()

@mcp.tool()
def career_get_application(job_id: int):
    """Get the user's application information for a job."""
    return get_application(job_id)

@mcp.tool()
def career_get_resume():
    """Get the user's current resume."""
    return get_resume()

@mcp.tool()
def career_save_job(job_id: int):
    """Save a selected job."""
    return save_job(job_id)

@mcp.tool()
def career_create_application(
    job_id: int,
    status: str = "Applied",
    notes: str = ""
):
    """Create an application for a job."""
    return create_application(job_id, status, notes)

@mcp.tool()
def career_update_application(
    application_id: int,
    status: str = "Interested",
    notes: str = ""
):
    """Update an existing application."""

    return update_application(application_id, status, notes)

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