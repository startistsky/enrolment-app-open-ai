import os
import requests

BACKEND_URL = os.getenv(
    "CAREER_BACKEND_URL",
    "http://127.0.0.1:8005"
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
