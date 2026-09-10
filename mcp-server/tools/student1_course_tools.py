import os

import requests


STUDENT1_BACKEND_URL = os.getenv(
    "STUDENT1_BACKEND_URL",
    "http://localhost:8001",
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 5


def _fetch_courses():
    """Return the course list, or a structured error if the API call fails."""
    url = f"{STUDENT1_BACKEND_URL}/api/courses"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
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


def get_course_count():
    """Return the number of courses exposed by the Student 1 backend API."""
    courses = _fetch_courses()
    if isinstance(courses, dict) and "error" in courses:
        return courses

    return {"course_count": len(courses)}


def get_course_by_code(course_code):
    """Return the course whose code matches course_code case-insensitively."""
    if not isinstance(course_code, str) or not course_code.strip():
        return {"error": "course_code is required"}

    normalised_code = course_code.strip().upper()
    courses = _fetch_courses()
    if isinstance(courses, dict) and "error" in courses:
        return courses

    for course in courses:
        if not isinstance(course, dict):
            continue

        existing_code = course.get("course_code")
        if isinstance(existing_code, str) and existing_code.strip().upper() == normalised_code:
            return course

    return {
        "error": "Course not found",
        "course_code": normalised_code,
    }


if __name__ == "__main__":
    print("get_course_count():")
    print(get_course_count())

    print('\nget_course_by_code("COMP1001"):')
    print(get_course_by_code("COMP1001"))
