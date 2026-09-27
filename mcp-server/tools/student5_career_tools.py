import os
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Student5 Career Tools")

# Configuration
BACKEND_URL = os.getenv(
    "CAREER_BACKEND_URL",
    "http://127.0.0.1:8005"
)


RAG_URL = os.getenv(
    "RAG_URL",
    "http://127.0.0.1:9101"
)

# Backend helper
def get_backend_job(
    job_id
):

    response = requests.get(

        f"{BACKEND_URL}/api/jobs/{job_id}",

        timeout=10
    )

    response.raise_for_status()

    return response.json()

# MCP - Selected Job
@mcp.tool()
def get_selected_job(
    job_id: int
):
    """
    Retrieve the selected job from
    the career database.
    """

    try:

        job = get_backend_job(
            job_id
        )

        return {
            "success": True,
            "job": job
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }

# MCP - Job Requirements
@mcp.tool()
def get_job_requirements(
    job_id: int
):
    """
    Retrieve requirements and description
    for the selected job.
    """

    try:

        job = get_backend_job(
            job_id
        )

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
            )
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }

# MCP - Job Analysis
@mcp.tool()
def analyse_selected_job(
    job_id: int
):
    """
    Analyse the selected job using
    the existing career AI analysis endpoint.
    """

    try:

        response = requests.post(

            (
                f"{BACKEND_URL}/api/jobs/"
                f"{job_id}/analyse"
            ),

            timeout=120
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }

# MCP - RAG Knowledge
@mcp.tool()
def retrieve_career_knowledge(
    query: str,
    top_k: int = 4
):
    """
    Retrieve grounded career guidance from
    the shared local RAG server.
    """

    query = str(
        query or ""
    ).strip()

    if not query:

        return {
            "success": False,
            "error": "Query is required."
        }

    try:

        response = requests.post(

            f"{RAG_URL}/retrieve/career",

            json={
                "query": query,
                "top_k": top_k
            },

            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        return {
            "success": True,
            **result
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }

# MCP Server
if __name__ == "__main__":

    mcp.run(
        transport="stdio"
    )
