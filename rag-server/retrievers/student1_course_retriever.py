import os
import re
from pprint import pprint

import requests


STUDENT1_BACKEND_URL = os.getenv(
    "STUDENT1_BACKEND_URL",
    "http://localhost:8001",
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 5
MAX_TOP_K = 10

QUERY_STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "course",
    "covers",
    "credit",
    "for",
    "is",
    "me",
    "of",
    "points",
    "tell",
    "teaches",
    "the",
    "what",
    "which",
    "who",
    "worth",
}


def _fetch_courses():
    """Return live courses, or structured backend error information."""
    try:
        response = requests.get(
            f"{STUDENT1_BACKEND_URL}/api/courses",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        courses = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {
            "error": "Student 1 backend unavailable",
            "detail": str(exc),
        }

    if not isinstance(courses, list):
        return {
            "error": "Invalid response from Student 1 backend",
            "detail": "Expected the courses response to be a JSON list",
        }

    return courses


def _tokenize(value):
    """Return lowercase alphanumeric tokens for deterministic matching."""
    return re.findall(r"[a-z0-9]+", str(value).lower())


def _tokens_match(query_token, field_token):
    """Match equal tokens or meaningful singular/plural-style partials."""
    if query_token == field_token:
        return True
    if min(len(query_token), len(field_token)) < 4:
        return False
    shorter, longer = sorted((query_token, field_token), key=len)
    return len(longer) - len(shorter) <= 2 and longer.startswith(shorter)


def _score_course(course, query_tokens):
    """Score one course and report whether its code matched exactly."""
    code_tokens = _tokenize(course.get("course_code", ""))
    name_tokens = _tokenize(course.get("course_name", ""))
    supporting_tokens = _tokenize(" ".join(
        str(course.get(field, ""))
        for field in (
            "lecturer",
            "semester",
            "credit_points",
            "course_description",
        )
    ))

    score = 0
    exact_code_match = False
    for query_token in query_tokens:
        if query_token in code_tokens:
            score += 8
            exact_code_match = True
        elif any(_tokens_match(query_token, token) for token in code_tokens):
            score += 5

        if query_token in name_tokens:
            score += 4
        elif any(_tokens_match(query_token, token) for token in name_tokens):
            score += 2

        if any(_tokens_match(query_token, token) for token in supporting_tokens):
            score += 1

    return score, exact_code_match


def _confidence_for(score, exact_code_match):
    """Map a deterministic relevance score to a confidence category."""
    if exact_code_match or score >= 8:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def retrieve_course_context(query, top_k=3):
    """Retrieve the most relevant live Course Management records."""
    if not isinstance(query, str) or not query.strip():
        return {
            "query": "",
            "matches": [],
            "insufficient_context": True,
            "message": "A retrieval query is required",
        }

    original_query = query.strip()
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
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
            "message": "Insufficient context: no relevant Course Management information was found.",
        }

    courses = _fetch_courses()
    if isinstance(courses, dict) and "error" in courses:
        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            **courses,
        }

    scored_courses = []
    for course in courses:
        if not isinstance(course, dict):
            continue

        course_code = course.get("course_code")
        if not isinstance(course_code, str) or not course_code.strip():
            continue

        score, exact_code_match = _score_course(course, query_tokens)
        if score <= 0:
            continue

        normalised_code = course_code.strip().upper()
        scored_courses.append({
            "source_id": f"course:{normalised_code}",
            "citation": f"Course Management record: {normalised_code}",
            "confidence": _confidence_for(score, exact_code_match),
            "score": score,
            "context": course,
        })

    scored_courses.sort(
        key=lambda match: (-match["score"], match["source_id"])
    )
    matches = scored_courses[:top_k]

    if not matches:
        return {
            "query": original_query,
            "matches": [],
            "insufficient_context": True,
            "message": "Insufficient context: no relevant Course Management information was found.",
        }

    return {
        "query": original_query,
        "matches": matches,
        "insufficient_context": False,
    }


if __name__ == "__main__":
    example_queries = [
        "Tell me about COMP1001",
        "Who teaches Machine Learning?",
        "What course covers databases?",
        "What course is worth 12 credit points?",
        "Tell me about quantum agriculture",
    ]

    for example_query in example_queries:
        print(f"\nQuery: {example_query}")
        pprint(retrieve_course_context(example_query), sort_dicts=False)
