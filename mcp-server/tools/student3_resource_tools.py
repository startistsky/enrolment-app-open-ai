import os

import requests


STUDENT3_DATABASE_API_URL = os.getenv(
    "STUDENT3_DATABASE_API_URL",
    "http://localhost:5004",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 5


def _fetch_resources(params=None):
    """Return the resource list from the Student 3 database API."""
    url = f"{STUDENT3_DATABASE_API_URL}/resources"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        resources = response.json()

    except (requests.RequestException, ValueError) as exc:
        return {
            "error": "Student 3 resource service unavailable",
            "detail": str(exc),
        }

    if not isinstance(resources, list):
        return {
            "error": "Invalid response from Student 3 resource service",
            "detail": "Expected the resources response to be a JSON list",
        }

    return resources


def get_resource_count():
    """Return the total number of campus resources."""
    resources = _fetch_resources()

    if isinstance(resources, dict) and "error" in resources:
        return resources

    return {
        "resource_count": len(resources)
    }


def get_resource_by_type(resource_type):
    """Return campus resources matching the supplied resource type."""
    if not isinstance(resource_type, str) or not resource_type.strip():
        return {
            "error": "resource_type is required"
        }

    normalised_type = resource_type.strip()

    resources = _fetch_resources({
        "type": normalised_type
    })

    if isinstance(resources, dict) and "error" in resources:
        return resources

    if not resources:
        return {
            "error": "Resource type not found",
            "resource_type": normalised_type,
        }

    return {
        "resource_type": normalised_type,
        "resource_count": len(resources),
        "resources": resources,
    }


if __name__ == "__main__":
    print("get_resource_count():")
    print(get_resource_count())

    print('\nget_resource_by_type("Printer"):')
    print(get_resource_by_type("Printer"))