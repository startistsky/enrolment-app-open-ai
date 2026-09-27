import os
import asyncio
from model.database import get_db

# exposeRAG via MCP using the http
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# MCP configuration
MCP_URL = os.getenv(
    "MCP_URL",
    "http://127.0.0.1:9001/mcp"
)

# Local database job tool
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

# MCP client
async def _call_mcp_tool(
    tool_name,
    arguments
):
    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream
    ):
        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments
            )

            return result



def _extract_mcp_result(result):
    """
    Convert MCP CallToolResult into a normal
    Python value that the agent can use.
    """

    # If MCP returned structured content
    structured = getattr(
        result,
        "structuredContent",
        None
    )

    if structured is not None:

        return structured


    # Some SDK versions use structured_content
    structured = getattr(
        result,
        "structured_content",
        None
    )

    if structured is not None:

        return structured


    # Otherwise inspect content blocks
    content = getattr(
        result,
        "content",
        []
    )

    for item in content:

        # TextContent
        text = getattr(
            item,
            "text",
            None
        )

        if text:
            import json
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "result": text
                }

    # Fallback
    return {
        "success": True,
        "result": result
    }


def call_mcp_tool(
    tool_name,
    arguments
):
    """
    Sync wrapper around the async MCP client
    """

    result = asyncio.run(
        _call_mcp_tool(
            tool_name,
            arguments
        )
    )

    return _extract_mcp_result(
        result
    )

# MCP Job Analysis
def analyse_job_tool(job):

    try:

        return call_mcp_tool(
            "career_analyse_selected_job",
            {
                "job_id": job["id"]
            }
        )

    except Exception as error:

        print(
            "MCP JOB ANALYSIS ERROR:",
            repr(error)
        )

        # Fallback to existing local AI implementation
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

# Job Requirements
def get_job_requirements_tool(job):

    try:

        return call_mcp_tool(
            "career_get_job_requirements",
            {
                "job_id": job["id"]
            }
        )

    except Exception as error:

        print(
            "MCP REQUIREMENTS ERROR:",
            repr(error)
        )

        # Local fallback
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

# RAG through MCP
def get_career_rag_tool(
    message,
    job
):
    """
    Retrieve career knowledge through MCP.
    Backend -> MCP -> career_retrieve_knowledge -> RAG server
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
    try:
        return call_mcp_tool(
            "career_retrieve_knowledge",
            {
                "query": job_context,
                "top_k": 4
            }
        )

    except Exception as error:

        print(
            "MCP RAG ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error),
            "results": [],
            "sources": [],
            "confidence": "low"
        }
