import os
import requests

BACKEND_URL = os.getenv(
    "CAREER_BACKEND_URL",
    "http://127.0.0.1:8005"
)

RAG_URL = os.getenv(
    "RAG_URL",
    "http://127.0.0.1:9101"
)

def get_backend_job(job_id: int):
    """
    Retrieve a job from the Flask backend.
    """

    response = requests.get(
        f"{BACKEND_URL}/api/jobs/{job_id}",
        timeout=10
    )

    response.raise_for_status()

    return response.json()

# MCP: Selected Job
def get_selected_job(job_id: int):
    """
    Retrieve the selected job from the career backend.
    """

    try:

        job = get_backend_job(job_id)

        return {
            "success": True,
            "job": job
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }


# MCP: Job Requirements
def get_job_requirements(job_id: int):
    """
    Retrieve requirements and description
    for the selected job.
    """

    try:

        job = get_backend_job(job_id)

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

# MCP: Job Analysis
def analyse_selected_job(job_id: int):
    """
    Analyse the selected job through
    the Flask backend AI analysis endpoint.
    """

    try:

        response = requests.post(
            f"{BACKEND_URL}/api/jobs/{job_id}/analyse",
            timeout=120
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }

# MCP: RAG Knowledge
def retrieve_career_knowledge(
    query: str,
    top_k: int = 4
):
    """
    Retrieve grounded career knowledge
    from the RAG server.

    MCP exposes this function as a tool.
    The MCP server calls this function,
    which then calls the RAG server.
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

        top_k = int(top_k)

        if top_k < 1:
            top_k = 1

        if top_k > 10:
            top_k = 10

    except (TypeError, ValueError):

        top_k = 4


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
            "confidence": result.get(
                "confidence",
                "low"
            ),
            "context": result.get(
                "context",
                ""
            ),
            "results": result.get(
                "results",
                []
            ),
            "sources": result.get(
                "sources",
                []
            )
        }

    except requests.RequestException as error:

        return {
            "success": False,
            "error": str(error)
        }
