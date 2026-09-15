from flask import Blueprint, jsonify, request
import requests
import json
from datetime import datetime

from config import AI_SERVICE_URL, MODEL_NAME, AI_TIMEOUT
from database_api import get_events
from mcp_client import call_mcp_tool

from prompts import (
    build_plan_prompt,
    build_query_prompt,
    build_chat_prompt
)


ai_bp = Blueprint("ai", __name__)


# ============================================================
# OLLAMA
# ============================================================

def call_llm(prompt):
    """
    Send a prompt to Ollama and return the generated text.
    """

    try:
        response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 250,
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            },
            timeout=AI_TIMEOUT
        )

        response.raise_for_status()

        result = response.json()

        return result.get("response", "").strip()

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Failed to communicate with AI service: {error}"
        )


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_text(value):
    """
    Normalize text for case-insensitive matching.
    """

    if value is None:
        return ""

    return str(value).lower().strip()


def needs_event_database(user_message):
    """
    Decide whether the message appears to be asking about
    campus events.

    Normal conversation goes directly to the LLM.
    Event-related questions use the database workflow.
    """

    message = normalize_text(user_message)

    event_keywords = [
        "event",
        "events",
        "activity",
        "activities",
        "workshop",
        "workshops",
        "career",
        "careers",
        "sport",
        "sports",
        "wellbeing",
        "social",
        "community",
        "creative",
        "campus",
        "basketball",
        "handball",
        "yoga",
        "fair",
        "mixer",
        "club",
        "expo",
        "building",
        "location",
        "where is",
        "when is",
        "this week",
        "next week",
        "weekend",
        "today",
        "tomorrow",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        " jan",
        " feb",
        " mar",
        " apr",
        " jun",
        " jul",
        " aug",
        " sep",
        " oct",
        " nov",
        " dec"
    ]

    return any(
        keyword in message
        for keyword in event_keywords
    )


# ============================================================
# AI QUERY EXTRACTION
# ============================================================

def empty_query():
    return {
        "date": "",
        "month": "",
        "category": "",
        "title": "",
        "location": "",
        "keywords": []
    }


def parse_query_json(raw_response, user_message):
    """
    Parse and clean structured JSON returned by Ollama.

    Small models sometimes add markdown formatting or incorrectly
    copy the entire user question into the title field.
    """

    text = raw_response.strip()

    # Remove common markdown wrappers.
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    # Try to extract the JSON object if extra text appears.
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1:
        text = text[first_brace:last_brace + 1]

    try:
        data = json.loads(text)

    except json.JSONDecodeError:
        return empty_query()

    query = {
        "date": str(
            data.get("date", "")
        ).strip(),

        "month": str(
            data.get("month", "")
        ).strip(),

        "category": str(
            data.get("category", "")
        ).strip(),

        "title": str(
            data.get("title", "")
        ).strip(),

        "location": str(
            data.get("location", "")
        ).strip(),

        "keywords": (
            data.get("keywords", [])
            if isinstance(data.get("keywords", []), list)
            else []
        )
    }

    # --------------------------------------------------------
    # Clean bad title extraction
    # --------------------------------------------------------

    normalized_user = normalize_text(user_message)
    normalized_title = normalize_text(query["title"])

    # Exact copy of the user's question is not an event title.
    if normalized_title == normalized_user:
        query["title"] = ""

    question_phrases = [
        "any event",
        "any events",
        "what event",
        "what events",
        "which event",
        "which events",
        "are there",
        "events at",
        "events on",
        "events in",
        "event at",
        "event on",
        "event in",
        "events this",
        "events next",
        "events today",
        "events tomorrow"
    ]

    normalized_title = normalize_text(
        query["title"]
    )

    if any(
        phrase in normalized_title
        for phrase in question_phrases
    ):
        query["title"] = ""

    return query


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_date(value):
    """
    Convert different date formats into MM-DD.

    Examples:

    2026-08-08
    8 August 2026
    8 August
    August 8
    8 Aug

    all become:

    08-08
    """

    if not value:
        return ""

    value = str(value).strip()

    possible_formats = [
        "%Y-%m-%d",

        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",

        "%d %B",
        "%d %b",
        "%B %d",
        "%b %d",

        "%d/%m/%Y",
        "%d/%m"
    ]

    for date_format in possible_formats:

        try:
            parsed = datetime.strptime(
                value,
                date_format
            )

            return parsed.strftime("%m-%d")

        except ValueError:
            continue

    return ""


def normalize_month(value):
    """
    Convert different month formats into a month number.

    Examples:

    August -> 08
    Aug    -> 08
    """

    if not value:
        return ""

    value = str(value).strip()

    possible_formats = [
        "%B",
        "%b"
    ]

    for date_format in possible_formats:

        try:
            parsed = datetime.strptime(
                value,
                date_format
            )

            return parsed.strftime("%m")

        except ValueError:
            continue

    return ""


def get_event_month(event_date):
    """
    Extract month from an event date.
    """

    if not event_date:
        return ""

    value = str(event_date).strip()

    possible_formats = [
        "%Y-%m-%d",

        "%d %B %Y",
        "%d %b %Y",

        "%B %d %Y",
        "%b %d %Y"
    ]

    for date_format in possible_formats:

        try:
            parsed = datetime.strptime(
                value,
                date_format
            )

            return parsed.strftime("%m")

        except ValueError:
            continue

    return ""


# ============================================================
# EVENT MATCHING
# ============================================================

def event_matches(event, query):
    """
    Determine whether one database event matches the
    structured query.
    """

    event_title = normalize_text(
        event.get("title")
    )

    event_category = normalize_text(
        event.get("category")
    )

    event_location = normalize_text(
        event.get("location")
    )

    event_description = normalize_text(
        event.get("description")
    )

    event_date = normalize_date(
        event.get("date", "")
    )

    event_month = get_event_month(
        event.get("date", "")
    )

    query_title = normalize_text(
        query.get("title")
    )

    query_category = normalize_text(
        query.get("category")
    )

    query_location = normalize_text(
        query.get("location")
    )

    query_date = normalize_date(
        query.get("date", "")
    )

    query_month = normalize_month(
        query.get("month", "")
    )

    query_keywords = query.get(
        "keywords",
        []
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if query_date:

        if query_date != event_date:
            return False

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    if query_month:

        if query_month != event_month:
            return False

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if query_title:

        if query_title not in event_title:
            return False

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    if query_category:

        category_search_text = " ".join([
            event_category,
            event_title,
            event_description
        ])

        if query_category not in category_search_text:
            return False

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if query_location:

        if query_location not in event_location:
            return False

    # --------------------------------------------------------
    # KEYWORDS
    # --------------------------------------------------------

    if query_keywords:

        searchable_text = " ".join([
            event_title,
            event_category,
            event_location,
            event_description
        ])

        for keyword in query_keywords:

            keyword = normalize_text(keyword)

            if (
                keyword
                and keyword not in searchable_text
            ):
                return False

    return True


def filter_events(events, query):
    """
    Filter database events using the structured query.
    """

    return [
        event
        for event in events
        if event_matches(event, query)
    ]


# ============================================================
# DETERMINISTIC FINAL RESPONSE
# ============================================================

def build_event_response(user_message, matching_events):
    """
    Build a reliable answer directly from database results.

    Ollama is NOT allowed to decide whether matching events exist.
    This prevents hallucinations and incorrect fallback responses.
    """

    if not matching_events:
        return "No matching event is currently available."

    message = normalize_text(user_message)

    # --------------------------------------------------------
    # LOCATION QUESTION
    # --------------------------------------------------------

    if (
        "where" in message
        or "location" in message
    ):

        if len(matching_events) == 1:

            event = matching_events[0]

            return (
                f"{event.get('title', 'The event')} is at "
                f"{event.get('location', 'an unspecified location')}."
            )

    # --------------------------------------------------------
    # SINGLE RESULT
    # --------------------------------------------------------

    if len(matching_events) == 1:

        event = matching_events[0]

        return (
            f"I found 1 matching event:\n\n"
            f"{event.get('title', '')} — "
            f"{event.get('date', '')} at "
            f"{event.get('location', '')}. "
            f"{event.get('description', '')}"
        )

    # --------------------------------------------------------
    # MULTIPLE RESULTS
    # --------------------------------------------------------

    lines = [
        f"I found {len(matching_events)} matching events:"
    ]

    for event in matching_events:

        lines.append(
            (
                f"- {event.get('title', '')} — "
                f"{event.get('date', '')} at "
                f"{event.get('location', '')}"
            )
        )

    return "\n".join(lines)



# ============================================================
# RELEASE 1 - MCP
# ============================================================

@ai_bp.route("/api/mcp/event-count", methods=["GET"])
def mcp_event_count():
    outcome = call_mcp_tool("event_count")

    if not outcome["ok"]:
        return jsonify({
            "error": outcome.get("error"),
            "detail": outcome.get("detail"),
        }), outcome.get("status", 500)

    return jsonify({
        "tool": "event_count",
        "result": outcome["result"],
    }), 200


@ai_bp.route("/api/mcp/event-by-title", methods=["GET"])
def mcp_event_by_title():
    event_title = request.args.get("title", "").strip()

    if not event_title:
        return jsonify({
            "error": "title is required"
        }), 400

    outcome = call_mcp_tool(
        "event_by_title",
        {
            "event_title": event_title
        }
    )

    if not outcome["ok"]:
        return jsonify({
            "error": outcome.get("error"),
            "detail": outcome.get("detail"),
        }), outcome.get("status", 500)

    return jsonify({
        "tool": "event_by_title",
        "result": outcome["result"],
    }), 200
# ============================================================
# API
# ============================================================

@ai_bp.route("/api/ai", methods=["POST"])
def ai_assistant():
    """
    Hybrid Agentic AI workflow.

    General conversation:
        User -> Ollama

    Event query:
        Plan
        -> Extract Query
        -> Act
        -> Observe
        -> Deterministic Adapt
    """

    data = request.get_json() or {}

    user_message = data.get(
        "message",
        ""
    ).strip()

    if not user_message:

        return jsonify({
            "error": "Message is required."
        }), 400

    try:

        # ====================================================
        # GENERAL CONVERSATION
        # ====================================================

        if not needs_event_database(
            user_message
        ):

            chat_prompt = build_chat_prompt(
                user_message
            )

            final_answer = call_llm(
                chat_prompt
            )

            return jsonify({
                "response": final_answer,

                "agentic_workflow": {
                    "mode": "general_conversation"
                }
            }), 200

        # ====================================================
        # PLAN
        # ====================================================

        plan_prompt = build_plan_prompt(
            user_message
        )

        plan = call_llm(
            plan_prompt
        )

        # ====================================================
        # EXTRACT STRUCTURED QUERY
        # ====================================================

        query_prompt = build_query_prompt(
            user_message
        )

        query_response = call_llm(
            query_prompt
        )

        query = parse_query_json(
            query_response,
            user_message
        )

        # ====================================================
        # ACT
        # ====================================================

        events = get_events()

        if events is None:
            events = []

        matching_events = filter_events(
            events,
            query
        )

        # ====================================================
        # OBSERVE
        # ====================================================

        if matching_events:

            observation = (
                f"Database search found "
                f"{len(matching_events)} matching events."
            )

        else:

            observation = (
                "Database search found no matching events."
            )

        # ====================================================
        # ADAPT
        #
        # Important:
        # Python creates the final factual response.
        # Ollama does not decide whether results exist.
        # ====================================================

        final_answer = build_event_response(
            user_message,
            matching_events
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({
            "response": final_answer,

            "agentic_workflow": {
                "mode": "event_database",

                "plan": plan,

                "query": query,

                "act": (
                    f"Retrieved {len(events)} events and "
                    f"found {len(matching_events)} matches."
                ),

                "observe": observation,

                "adapt": final_answer
            }
        }), 200

    except RuntimeError as error:

        return jsonify({
            "error": str(error)
        }), 503

    except Exception as error:

        return jsonify({
            "error": "An unexpected error occurred.",
            "details": str(error)
        }), 500