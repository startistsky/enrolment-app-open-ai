import os
import requests

from model.database import get_db


MCP_URL = os.getenv(
    "MCP_URL",
    "http://127.0.0.1:8020"
)

RAG_URL = os.getenv(
    "RAG_URL",
    "http://127.0.0.1:9101"
)


# job tool 
def get_job_tool(job_id):

    db = get_db()

    try:

        job = db.execute(
            """
            SELECT *
            FROM jobs
            WHERE id = ?
            """,
            (job_id,)
        ).fetchone()

        if not job:
            return None

        return dict(job)

    finally:

        db.close()


# MCP helper
def call_mcp_tool(
    tool_name,
    arguments
):
    """
    Backend adapter for the shared MCP server.

    The agent does not need to know the MCP
    implementation details.
    """

    response = requests.post(
        f"{MCP_URL}/tools/{tool_name}",
        json=arguments,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# RAG tools
def retrieve_rag_tool(
    query,
    top_k=4
):
    """
    Retrieve grounded career knowledge
    from the shared RAG server.
    """

    response = requests.post(
        f"{RAG_URL}/retrieve/career",
        json={
            "query": query,
            "top_k": top_k
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()

# job analysis 
def analyse_job_tool(job):

    try:

        return call_mcp_tool(
            "analyse_selected_job",
            {
                "job_id": job["id"]
            }
        )

    except Exception:

        # Fallback to existing local AI implementation.
        from .ai_service import analyse_job

        return analyse_job(
            job.get(
                "description",
                ""
            ),
            job.get(
                "requirements",
                ""
            )
        )

# job requirement
def get_job_requirements_tool(job):

    return {
        "success": True,

        "requirements": job.get(
            "requirements",
            ""
        ),

        "description": job.get(
            "description",
            ""
        )
    }

# RAG career 
def get_career_rag_tool(
    message,
    job
):
    """
    Retrieve career knowledge relevant to both
    the user's question and the selected job.

    The selected job is included in the query so
    retrieved career guidance is relevant to the
    current job context.
    """

    job_context = f"""
Selected job:

Title:
{job.get("title", "")}

Company:
{job.get("company", "")}

Location:
{job.get("location", "")}

Industry:
{job.get("industry", "")}

Job type:
{job.get("job_type", "")}

Description:
{job.get("description", "")}

Requirements:
{job.get("requirements", "")}

User question:
{message}
"""

    return retrieve_rag_tool(
        job_context,
        top_k=4
    )
