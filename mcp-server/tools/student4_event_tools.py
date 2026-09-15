import os

import requests


STUDENT4_BACKEND_URL = os.getenv(
    "STUDENT4_BACKEND_URL",
    "http://localhost:8000",
).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 5


def _fetch_events():
    """Return the event list from the Student 4 backend."""
    url = f"{STUDENT4_BACKEND_URL}/api/events"

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS
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


def get_event_count():
    """Return the total number of events."""
    events = _fetch_events()

    if isinstance(events, dict) and "error" in events:
        return events

    return {
        "event_count": len(events)
    }

def get_event_by_title(event_title):
    """Return an event whose title matches the supplied title."""

    if not isinstance(event_title, str) or not event_title.strip():
        return {"error": "event_title is required"}

    search_title = event_title.strip().lower()

    events = _fetch_events()

    if isinstance(events, dict) and "error" in events:
        return events

    for event in events:
        if not isinstance(event, dict):
            continue

        existing_title = event.get("title")

        if (
            isinstance(existing_title, str)
            and search_title in existing_title.strip().lower()
        ):
            return event

    return {
        "error": "Event not found",
        "event_title": event_title.strip(),
    }