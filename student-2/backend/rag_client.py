import os

import requests


RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL",
    "http://localhost:9101",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 10


def retrieve_assignment_context(query, top_k=3):
    """Retrieve grounded assignment context from the shared RAG server."""
    if not isinstance(query, str) or not query.strip():
        return {
            "error": "query is required",
            "matches": [],
            "insufficient_context": True,
        }

    try:
        response = requests.post(
            f"{RAG_SERVER_URL}/retrieve/assignment",
            json={
                "query": query.strip(),
                "top_k": top_k,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
        result = response.json()

    except requests.RequestException as error:
        return {
            "error": "RAG server unavailable",
            "details": str(error),
            "matches": [],
            "insufficient_context": True,
        }

    except ValueError as error:
        return {
            "error": "Invalid RAG server response",
            "details": str(error),
            "matches": [],
            "insufficient_context": True,
        }

    if not isinstance(result, dict):
        return {
            "error": "Invalid RAG server response",
            "details": "Expected a JSON object",
            "matches": [],
            "insufficient_context": True,
        }

    return result