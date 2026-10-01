import os
import asyncio
import json
import requests

from model.database import get_db

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# ============================================================
# CONFIGURATION
# ============================================================

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://127.0.0.1:9001/mcp"
)

RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL",
    "http://127.0.0.1:9101"
)


# ============================================================
# LOCAL DATABASE JOB TOOL
# ============================================================

def get_job_tool(job_id):
    """
    Retrieve a selected job from the local backend database.

    This is used by the Career Agent to establish the selected
    job context.

    MCP also has a career_get_job_mcp tool. The agent can use
    that tool when it needs MCP-validated job information.
    """

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


# ============================================================
# MCP CLIENT
# ============================================================

async def _call_mcp_tool(
    tool_name,
    arguments
):
    """
    Call a tool on the shared Smart Campus MCP server.

    MCP server:
        http://127.0.0.1:9001/mcp
    """

    async with streamable_http_client(
        MCP_SERVER_URL
    ) as (
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
    Convert MCP CallToolResult into a normal Python value.
    """

    # --------------------------------------------------------
    # Structured content - SDK naming
    # --------------------------------------------------------

    structured = getattr(
        result,
        "structuredContent",
        None
    )

    if structured is not None:
        return structured


    # --------------------------------------------------------
    # Structured content - alternate SDK naming
    # --------------------------------------------------------

    structured = getattr(
        result,
        "structured_content",
        None
    )

    if structured is not None:
        return structured


    # --------------------------------------------------------
    # Text content
    # --------------------------------------------------------

    content = getattr(
        result,
        "content",
        []
    )

    for item in content:

        text = getattr(
            item,
            "text",
            None
        )

        if text:

            try:
                return json.loads(text)

            except json.JSONDecodeError:

                return {
                    "success": True,
                    "result": text
                }


    # --------------------------------------------------------
    # MCP error flag
    # --------------------------------------------------------

    is_error = getattr(
        result,
        "isError",
        False
    )

    if is_error:

        return {
            "success": False,
            "error": "MCP tool returned an error."
        }


    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return {
        "success": True,
        "result": result
    }


def call_mcp_tool(
    tool_name,
    arguments
):
    """
    Synchronous wrapper around the asynchronous MCP client.
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


# ============================================================
# MCP: SELECTED JOB
# ============================================================

def get_selected_job_mcp_tool(job):
    """
    Retrieve the selected job through the shared MCP server.
    """

    try:

        return call_mcp_tool(
            "career_get_job_mcp",
            {
                "job_id": int(job["id"])
            }
        )

    except Exception as error:

        print(
            "MCP SELECTED JOB ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }


# ============================================================
# MCP: JOB REQUIREMENTS
# ============================================================

def get_job_requirements_tool(job):
    """
    Retrieve job requirements through MCP.
    """

    try:

        return call_mcp_tool(
            "career_get_job_requirements_mcp",
            {
                "job_id": int(job["id"])
            }
        )

    except Exception as error:

        print(
            "MCP REQUIREMENTS ERROR:",
            repr(error)
        )

        # ----------------------------------------------------
        # Local fallback
        # ----------------------------------------------------

        return {
            "success": True,

            "job_id": job.get(
                "id"
            ),

            "title": job.get(
                "title",
                ""
            ),

            "company": job.get(
                "company",
                ""
            ),

            "requirements": job.get(
                "requirements",
                ""
            ),

            "description": job.get(
                "description",
                ""
            ),

            "source": "local_fallback"
        }


# ============================================================
# MCP: JOB ANALYSIS
# ============================================================

def analyse_job_tool(job):
    """
    Analyse the selected job through the shared MCP server.
    """

    try:

        return call_mcp_tool(
            "career_analyse_selected_job_mcp",
            {
                "job_id": int(job["id"])
            }
        )

    except Exception as error:

        print(
            "MCP JOB ANALYSIS ERROR:",
            repr(error)
        )

        # ----------------------------------------------------
        # Existing local AI fallback
        # ----------------------------------------------------

        try:

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

        except Exception as fallback_error:

            return {
                "success": False,
                "error": str(fallback_error)
            }


# ============================================================
# RAG CLIENT
# ============================================================

def get_career_rag_tool(
    message,
    job=None
):
    """
    Retrieve career knowledge from the dedicated RAG server.

    IMPORTANT:
    RAG is NOT called through MCP.

    Architecture:

        Agent
          |
          +---- MCP 9001
          |
          +---- RAG 9101
    """

    query = str(
        message or ""
    ).strip()

    if not query:

        return {
            "success": False,
            "error": "RAG query is empty.",
            "results": [],
            "sources": [],
            "confidence": "low"
        }


    # --------------------------------------------------------
    # Build RAG request
    # --------------------------------------------------------

    payload = {
        "query": query,
        "top_k": 4
    }


    # Optional job context.
    if job:

        payload["job"] = {
            "id": job.get("id"),
            "title": job.get(
                "title",
                ""
            ),
            "company": job.get(
                "company",
                ""
            )
        }


    try:

        # ----------------------------------------------------
        # Primary RAG endpoint
        # ----------------------------------------------------

        response = requests.post(
            f"{RAG_SERVER_URL}/retrieve/career",
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()


        # ----------------------------------------------------
        # Normalise response
        # ----------------------------------------------------

        if not isinstance(
            data,
            dict
        ):

            return {
                "success": False,
                "error": "Invalid RAG response.",
                "results": [],
                "sources": [],
                "confidence": "low"
            }


        data.setdefault(
            "success",
            True
        )

        data.setdefault(
            "results",
            []
        )

        data.setdefault(
            "sources",
            []
        )

        data.setdefault(
            "confidence",
            "low"
        )


        return data


    except requests.RequestException as error:

        print(
            "RAG ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error),
            "results": [],
            "sources": [],
            "confidence": "low"
        }
