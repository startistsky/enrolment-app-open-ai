import os
import re
from pprint import pprint

import requests


STUDENT2_BACKEND_URL = os.getenv(
    "STUDENT2_BACKEND_URL",
    "http://localhost:8002",
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
    "assignment",
    "assignments",
    "for",
    "has",
    "have",
    "i",
    "in",
    "is",
    "me",
    "my",
    "of",
    "on",
    "show",
    "tell",
    "the",
    "to",
    "what",
    "when",
    "which",
}


def _fetch_assignments():
    """Return live Student 2 assignments or structured error information."""
    try:
        response = requests.get(
            f"{STUDENT2_BACKEND_URL}/api/assignments",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        assignments = response.json()

    except (requests.RequestException, ValueError) as error:
        return {
            "error": "Student 2 backend unavailable",
            "detail": str(error),
        }

    if not isinstance(assignments, list):
        return {
            "error": "Invalid response from Student 2 backend",
            "detail": "Expected the assignments response to be a JSON list",
        }

    return assignments


def _tokenize(value):
    """Return lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", str(value).lower())


def _tokens_match(query_token, field_token):
    """Allow exact and small singular/plural style matches."""
    if query_token == field_token:
        return True

    if min(len(query_token), len(field_token)) < 4:
        return False

    shorter, longer = sorted(
        (query_token, field_token),
        key=len,
    )

    return (
        len(longer) - len(shorter) <= 2
        and longer.startswith(shorter)
    )


def _field_score(query_token, field_tokens, exact_score, partial_score):
    """Score one query token against one assignment field."""
    if query_token in field_tokens:
        return exact_score

    if any(
        _tokens_match(query_token, field_token)
        for field_token in field_tokens
    ):
        return partial_score

    return 0


def _score_assignment(assignment, query_tokens):
    """Score one assignment against the user's query."""
    title_tokens = _tokenize(
        assignment.get("assignment_title", "")
    )
    subject_tokens = _tokenize(
        assignment.get("subject_name", "")
    )
    priority_tokens = _tokenize(
        assignment.get("priority", "")
    )
    status_tokens = _tokenize(
        assignment.get("status", "")
    )
    due_date_tokens = _tokenize(
        assignment.get("due_date", "")
    )
    description_tokens = _tokenize(
        assignment.get("description", "")
    )

    score = 0

    for query_token in query_tokens:
        score += _field_score(query_token, title_tokens, 6, 4)
        score += _field_score(query_token, subject_tokens, 5, 3)
        score += _field_score(query_token, priority_tokens, 5, 3)
        score += _field_score(query_token, status_tokens, 4, 2)
        score += _field_score(query_token, due_date_tokens, 3, 2)
        score += _field_score(query_token, description_tokens, 2, 1)

    return score


def _confidence_for(score):
    """Convert relevance score into a confidence label."""
    if score >= 8:
        return "high"

    if score >= 4:
        return "medium"

    return "low"


def retrieve_assignment_context(query, top_k=3):
    """Retrieve relevant live Student 2 assignment records."""
    if not isinstance(query, str) or not query.strip():
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

    top_k = min(top_k, MAX_TOP_K)

    query_tokens = [
        token
        for token in _tokenize(original_query)
        if token not in QUERY_STOP_WORDS
    ]

    if not query_tokens:
        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            "message": (
                "Insufficient context: no relevant "
                "Assignment Management information was found."
            ),
        }

    assignments = _fetch_assignments()

    if isinstance(assignments, dict) and "error" in assignments:
        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            **assignments,
        }

    scored_assignments = []

    for assignment in assignments:
        if not isinstance(assignment, dict):
            continue

        assignment_id = assignment.get("assignment_id")
        title = assignment.get("assignment_title")

        if not isinstance(title, str) or not title.strip():
            continue

        score = _score_assignment(
            assignment,
            query_tokens,
        )

        if score <= 0:
            continue

        source_identifier = (
            str(assignment_id)
            if assignment_id is not None
            else title.strip()
        )

        scored_assignments.append({
            "source_id": f"assignment:{source_identifier}",
            "citation": (
                f"Assignment record: {title.strip()}"
            ),
            "confidence": _confidence_for(score),
            "score": score,
            "context": assignment,
        })

    scored_assignments.sort(
        key=lambda match: (
            -match["score"],
            match["source_id"],
        )
    )

    matches = scored_assignments[:top_k]

    if not matches:
        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            "message": (
                "Insufficient context: no relevant "
                "Assignment Management information was found."
            ),
        }

    return {
        "query": original_query,
        "matches": matches,
        "insufficient_context": False,
    }


if __name__ == "__main__":
    example_queries = [
        "What high priority assignments do I have?",
        "Show assignments for Advanced Software Development",
        "Which assignments are in progress?",
        "Tell me about the technical report",
        "Show my quantum farming assignment",
    ]

    for example_query in example_queries:
        print(f"\nQuery: {example_query}")

        pprint(
            retrieve_assignment_context(example_query),
            sort_dicts=False,
        )