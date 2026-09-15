import os
import re
from pprint import pprint

import requests


STUDENT4_BACKEND_URL = os.getenv(
    "STUDENT4_BACKEND_URL",
    "http://localhost:8000",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 5
MAX_TOP_K = 10


QUERY_STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "any",
    "are",
    "at",
    "available",
    "campus",
    "event",
    "events",
    "for",
    "in",
    "is",
    "me",
    "of",
    "on",
    "show",
    "tell",
    "the",
    "there",
    "what",
    "when",
    "where",
    "which",
}


def _fetch_events():
    """Return live Student 4 events or structured error information."""

    try:
        response = requests.get(
            f"{STUDENT4_BACKEND_URL}/api/events",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()
        events = response.json()

    except (requests.RequestException, ValueError) as exc:
        return {
            "error": "Student 4 backend unavailable",
            "detail": str(exc),
        }

    if not isinstance(events, list):
        return {
            "error": "Invalid response from Student 4 backend",
            "detail": "Expected the events response to be a JSON list",
        }

    return events


def _tokenize(value):
    """Return lowercase alphanumeric tokens."""

    return re.findall(
        r"[a-z0-9]+",
        str(value).lower()
    )


def _tokens_match(query_token, field_token):
    """Allow exact and small singular/plural style matches."""

    if query_token == field_token:
        return True

    if min(
        len(query_token),
        len(field_token)
    ) < 4:
        return False

    shorter, longer = sorted(
        (
            query_token,
            field_token
        ),
        key=len
    )

    return (
        len(longer) - len(shorter) <= 2
        and longer.startswith(shorter)
    )


def _score_event(event, query_tokens):
    """Score one event against the user's query."""

    title_tokens = _tokenize(
        event.get("title", "")
    )

    category_tokens = _tokenize(
        event.get("category", "")
    )

    location_tokens = _tokenize(
        event.get("location", "")
    )

    date_tokens = _tokenize(
        event.get("date", "")
    )

    description_tokens = _tokenize(
        event.get("description", "")
    )

    score = 0

    for query_token in query_tokens:

        # Title is the strongest signal.
        if query_token in title_tokens:
            score += 6

        elif any(
            _tokens_match(
                query_token,
                token
            )
            for token in title_tokens
        ):
            score += 4

        # Category is also important.
        if query_token in category_tokens:
            score += 5

        elif any(
            _tokens_match(
                query_token,
                token
            )
            for token in category_tokens
        ):
            score += 3

        # Location.
        if query_token in location_tokens:
            score += 4

        elif any(
            _tokens_match(
                query_token,
                token
            )
            for token in location_tokens
        ):
            score += 2

        # Date.
        if query_token in date_tokens:
            score += 3

        # Description provides supporting relevance.
        if query_token in description_tokens:
            score += 2

        elif any(
            _tokens_match(
                query_token,
                token
            )
            for token in description_tokens
        ):
            score += 1

    return score


def _confidence_for(score):
    """Convert relevance score to a simple confidence label."""

    if score >= 8:
        return "high"

    if score >= 4:
        return "medium"

    return "low"


def retrieve_event_context(query, top_k=3):
    """
    Retrieve the most relevant live Student 4 Event records.
    """

    if not isinstance(
        query,
        str
    ) or not query.strip():

        return {
            "query": "",
            "matches": [],
            "insufficient_context": True,
            "message": "A retrieval query is required",
        }

    original_query = query.strip()

    if (
        isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or top_k <= 0
    ):
        top_k = 3

    top_k = min(
        top_k,
        MAX_TOP_K
    )

    query_tokens = [
        token
        for token in _tokenize(
            original_query
        )
        if token not in QUERY_STOP_WORDS
    ]

    if not query_tokens:

        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            "message": (
                "Insufficient context: no relevant "
                "Campus Event information was found."
            ),
        }

    events = _fetch_events()

    if (
        isinstance(events, dict)
        and "error" in events
    ):

        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            **events,
        }

    scored_events = []

    for event in events:

        if not isinstance(
            event,
            dict
        ):
            continue

        event_id = event.get("id")
        title = event.get("title")

        if not isinstance(
            title,
            str
        ) or not title.strip():
            continue

        score = _score_event(
            event,
            query_tokens
        )

        if score <= 0:
            continue

        source_identifier = (
            str(event_id)
            if event_id is not None
            else title.strip()
        )

        scored_events.append({
            "source_id": (
                f"event:{source_identifier}"
            ),

            "citation": (
                f"Campus Event record: "
                f"{title.strip()}"
            ),

            "confidence": (
                _confidence_for(score)
            ),

            "score": score,

            "context": event,
        })

    scored_events.sort(
        key=lambda match: (
            -match["score"],
            match["source_id"]
        )
    )

    matches = scored_events[:top_k]

    if not matches:

        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            "message": (
                "Insufficient context: no relevant "
                "Campus Event information was found."
            ),
        }

    return {
        "query": original_query,
        "matches": matches,
        "insufficient_context": False,
    }


if __name__ == "__main__":

    example_queries = [
        "What cybersecurity events are available?",
        "Where is Cybersecurity Challenge?",
        "Are there any workshops?",
        "What events are in Building 10?",
        "Tell me about quantum farming",
    ]

    for example_query in example_queries:

        print(
            f"\nQuery: {example_query}"
        )

        pprint(
            retrieve_event_context(
                example_query
            ),
            sort_dicts=False
        )