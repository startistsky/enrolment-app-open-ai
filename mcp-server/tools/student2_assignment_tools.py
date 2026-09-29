import os

import requests


STUDENT2_BACKEND_URL = os.getenv(
    "STUDENT2_BACKEND_URL",
    "http://localhost:8002",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 5


def _fetch_assignments():
    """Return assignments from the Student 2 backend API."""
    url = f"{STUDENT2_BACKEND_URL}/api/assignments"

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        assignments = response.json()

    except (requests.RequestException, ValueError) as exc:
        return {
            "error": "Student 2 backend unavailable",
            "detail": str(exc),
        }

    if not isinstance(assignments, list):
        return {
            "error": "Invalid response from Student 2 backend",
            "detail": "Expected the assignments response to be a JSON list",
        }

    return assignments


def get_assignment_count():
    """Return the total number of Assignment Management records."""
    assignments = _fetch_assignments()

    if isinstance(assignments, dict) and "error" in assignments:
        return assignments

    return {
        "assignment_count": len(assignments),
    }


def get_assignment_by_id(assignment_id):
    """Return the assignment matching the supplied assignment ID."""
    try:
        normalised_id = int(assignment_id)
    except (TypeError, ValueError):
        return {
            "error": "assignment_id must be an integer",
        }

    if normalised_id <= 0:
        return {
            "error": "assignment_id must be greater than zero",
        }

    assignments = _fetch_assignments()

    if isinstance(assignments, dict) and "error" in assignments:
        return assignments

    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue

        try:
            existing_id = int(assignment.get("assignment_id"))
        except (TypeError, ValueError):
            continue

        if existing_id == normalised_id:
            return assignment

    return {
        "error": "Assignment not found",
        "assignment_id": normalised_id,
    }


if __name__ == "__main__":
    print("get_assignment_count():")
    print(get_assignment_count())

    print("\nget_assignment_by_id(1):")
    print(get_assignment_by_id(1))