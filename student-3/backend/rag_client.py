import os

import requests


RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL",
    "http://localhost:9101",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 10


def retrieve_resource_context(query, top_k=3):
    """Retrieve grounded campus resource context from the shared RAG server."""
    if not isinstance(query, str) or not query.strip():
        return {
            "error": "query is required",
            "matches": [],
        }

    try:
        response = requests.post(
            f"{RAG_SERVER_URL}/retrieve/resource",
            json={
                "query": query.strip(),
                "top_k": top_k,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        return {
            "error": "RAG server unavailable",
            "details": str(error),
            "matches": [],
        }

    except ValueError as error:
        return {
            "error": "Invalid RAG server response",
            "details": str(error),
            "matches": [],
        }