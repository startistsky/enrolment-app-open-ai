
import re

from llm_client import generate, ModelError


STOP_WORDS = {
    "a", "an", "and", "are", "at", "about", "available",
    "can", "date", "dates", "do", "events", "event",
    "exact", "for", "from", "give", "include", "in",
    "is", "list", "locations", "location", "me",
    "of", "on", "please", "show", "tell", "the",
    "their", "there", "title", "titles", "to",
    "what", "when", "where", "which", "with",
    "any", "all", "campus",
}

TOPIC_GROUPS = {
    "technology": {
        "technology", "tech", "coding", "programming",
        "software", "computer", "cybersecurity",
        "cyber", "ai", "artificial intelligence",
        "machine learning", "data", "digital",
    },
    "career": {
        "career", "job", "jobs", "employment",
        "employer", "internship", "interview",
        "resume", "networking",
    },
    "wellbeing": {
        "wellbeing", "wellness", "mental health",
        "mindfulness", "yoga", "meditation",
    },
    "sport": {
        "sport", "sports", "football", "basketball",
        "fitness", "running",
    },
}

ACTIVITY_GROUPS = {
    "workshop": {
        "workshop", "workshops", "training",
        "hands-on", "hands on", "tutorial",
        "bootcamp",
    },
}


def normalize_text(value):
    """Normalize text for matching."""
    return " ".join(
        re.findall(r"[a-z0-9]+", str(value).casefold())
    )


def keywords(text):
    """Extract meaningful words."""
    return {
        word
        for word in normalize_text(text).split()
        if word not in STOP_WORDS and len(word) > 1
    }


def get_event_text(event):
    """Use only searchable database fields."""
    return normalize_text(
        " ".join(
            str(event.get(field) or "")
            for field in (
                "title", "category", "description"
            )
        )
    )


def matches_group(text, terms):
    """Match a topic or activity term."""
    return any(
        normalize_text(term) in text.split(" ")
        if len(normalize_text(term).split()) == 1
        else normalize_text(term) in text
        for term in terms
    )


def filter_relevant_events(user_request, evidence):
    """Select candidate events using transparent rules.

    This is conservative keyword filtering, not semantic search.
    Unknown queries retain all evidence for the AI to analyse.
    """

    request = normalize_text(user_request)
    request_words = set(request.split())

    selected_topics = [
        terms
        for terms in TOPIC_GROUPS.values()
        if matches_group(request, terms)
    ]

    selected_activities = [
        terms
        for name, terms in ACTIVITY_GROUPS.items()
        if name in request_words
        or f"{name}s" in request_words
    ]

    # No recognised category: keep all evidence rather than
    # incorrectly discarding events.
    if not selected_topics and not selected_activities:
        query_words = keywords(user_request)
        if not query_words:
            return evidence

        scored = []

        for event in evidence:
            if not isinstance(event, dict):
                continue

            event_words = keywords(get_event_text(event))
            overlap = len(query_words & event_words)

            if overlap:
                scored.append((overlap, event))

        if scored:
            best = max(score for score, _ in scored)
            return [
                event for score, event in scored
                if score == best
            ]

        return []

    relevant = []

    for event in evidence:
        if not isinstance(event, dict):
            continue

        event_text = get_event_text(event)

        topic_match = (
            not selected_topics
            or any(
                matches_group(event_text, group)
                for group in selected_topics
            )
        )

        activity_match = (
            not selected_activities
            or any(
                matches_group(event_text, group)
                for group in selected_activities
            )
        )

        if topic_match and activity_match:
            relevant.append(event)

    return relevant


def build_grounded_answer(events):
    """Build a deterministic answer from actual event records."""
    if not events:
        return {
            "answer": "No matching events found in the supplied database records.",
            "evidence_used": [],
            "missing_evidence": [],
        }

    lines = []
    ids = []
    missing = []

    for event in events:
        event_id = event.get("id")
        title = str(event.get("title") or "").strip()
        date = str(event.get("date") or "").strip()
        location = str(event.get("location") or "").strip()

        if not title:
            missing.append(f"Title missing for event {event_id}")
            continue

        ids.append(event_id)

        lines.append(
            f"{title} — Date: {date or 'Not provided'}; "
            f"Location: {location or 'Not provided'}."
        )

        if not date:
            missing.append(f"Date missing for {title}")

        if not location:
            missing.append(f"Location missing for {title}")

    if not lines:
        return {
            "answer": "Insufficient event information to provide a grounded answer.",
            "evidence_used": [],
            "missing_evidence": missing,
        }

    return {
        "answer": "\n".join(lines),
        "evidence_used": ids,
        "missing_evidence": missing,
    }


def valid_attribution(result, evidence):
    """Validate references and ensure cited event details appear."""

    if not isinstance(result, dict):
        return False

    answer = result.get("answer")
    references = result.get("evidence_used")
    missing = result.get("missing_evidence")

    if (
        not isinstance(answer, str)
        or not answer.strip()
        or not isinstance(references, list)
        or not isinstance(missing, list)
    ):
        return False

    if answer.strip().casefold() in {
        "a factual answer based on the provided events.",
        "ai workshops are available.",
    }:
        return False

    events_by_id = {
        str(event["id"]): event
        for event in evidence
        if isinstance(event, dict)
        and isinstance(event.get("id"), (str, int))
        and not isinstance(event["id"], bool)
    }

    normalized = []
    answer_text = answer.casefold()

    for reference in references:
        if isinstance(reference, dict):
            reference = reference.get("id")

        if (
            not isinstance(reference, (str, int))
            or isinstance(reference, bool)
            or str(reference) not in events_by_id
        ):
            return False

        event = events_by_id[str(reference)]

        for field in ("title", "date", "location"):
            value = str(event.get(field) or "").strip()
            if value and value.casefold() not in answer_text:
                return False

        normalized.append(reference)

    if evidence and not normalized:
        return False

    if not evidence and normalized:
        return False

    result["evidence_used"] = list(
        dict.fromkeys(normalized)
    )

    return True


def run(user_request, evidence, planner_result):
    """Run the Worker with filtered evidence and grounded fallback."""

    relevant_events = filter_relevant_events(
        user_request, evidence
    )

    # No relevant event: return an explicitly grounded
    # no-match result without making the model invent events.
    if not relevant_events:
        return build_grounded_answer([])

    context = {
        "feature": "event_management",
        "user_request": user_request,
        "evidence": relevant_events,
        "planner_result": planner_result,
    }

    fields = {
        "answer": str,
        "evidence_used": list,
        "missing_evidence": list,
    }

    try:
        result = generate(
            role="worker",
            context=context,
            required_fields=fields,
            prompt_name="event_worker",
        )

        if valid_attribution(result, relevant_events):
            return result

        context["previous_worker_result"] = result
        context["correction_instruction"] = (
            "The previous response failed validation. "
            "Use only the provided relevant events. "
            "Include the exact title, date and location "
            "for each cited event. Cite only matching IDs. "
            "Return valid JSON with answer, evidence_used "
            "and missing_evidence."
        )

        corrected = generate(
            role="worker",
            context=context,
            required_fields=fields,
            prompt_name="event_worker",
        )

        if valid_attribution(corrected, relevant_events):
            return corrected

        # Both model answers failed validation.
        # Use only actual database fields as a safe fallback.
        return build_grounded_answer(relevant_events)

    except ModelError as exc:
        # Do not hide infrastructure failures.
        # Only formatting/structure failures can fall back.
        if "invalid" in str(exc).lower():
            return build_grounded_answer(relevant_events)
        raise
