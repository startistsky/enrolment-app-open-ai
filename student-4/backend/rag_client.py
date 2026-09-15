import requests

from config import (
    RAG_SERVER_URL,
    RAG_TIMEOUT,
)


def retrieve_event_context(query, top_k=3):
    """
    Retrieve grounded Campus Event context
    from the shared RAG Server.
    """

    url = f"{RAG_SERVER_URL}/retrieve/event"

    try:
        response = requests.post(
            url,
            json={
                "query": query,
                "top_k": top_k,
            },
            timeout=RAG_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

    except requests.exceptions.RequestException as error:
        return {
            "ok": False,
            "status": 503,
            "error": "RAG server unavailable",
            "detail": str(error),
        }

    except ValueError as error:
        return {
            "ok": False,
            "status": 502,
            "error": "Invalid response from RAG server",
            "detail": str(error),
        }

    if not isinstance(result, dict):
        return {
            "ok": False,
            "status": 502,
            "error": "Invalid response from RAG server",
            "detail": "Expected a JSON object",
        }

    return {
        "ok": True,
        "result": result,
    }