from flask import Blueprint, jsonify, request
import requests
import json
from datetime import datetime

from config import AI_SERVICE_URL, MODEL_NAME, AI_TIMEOUT
from database_api import get_events
from mcp_client import call_mcp_tool
from rag_client import retrieve_event_context

from prompts import (
    build_plan_prompt,
    build_query_prompt,
    build_chat_prompt,
    build_grounded_event_prompt
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

    if value is None:
        return ""

    return str(value).lower().strip()


def is_event_count_question(user_message):

    message = normalize_text(user_message)

    count_phrases = [
        "how many events",
        "how many event",
        "number of events",
        "number of event",
        "event count",
        "total events",
        "total number of events"
    ]

    return any(
        phrase in message
        for phrase in count_phrases
    )


def needs_event_database(user_message):

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

    text = raw_response.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

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
            if isinstance(
                data.get("keywords", []),
                list
            )
            else []
        )
    }

    normalized_user = normalize_text(
        user_message
    )

    normalized_title = normalize_text(
        query["title"]
    )

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

            return parsed.strftime(
                "%m-%d"
            )

        except ValueError:
            continue

    return ""


def normalize_month(value):

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

            return parsed.strftime(
                "%m"
            )

        except ValueError:
            continue

    return ""


def get_event_month(event_date):

    if not event_date:
        return ""

    value = str(
        event_date
    ).strip()

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

            return parsed.strftime(
                "%m"
            )

        except ValueError:
            continue

    return ""


# ============================================================
# EVENT MATCHING
# ============================================================

def event_matches(event, query):

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

    if query_date:

        if query_date != event_date:
            return False

    if query_month:

        if query_month != event_month:
            return False

    if query_title:

        if query_title not in event_title:
            return False

    if query_category:

        category_search_text = " ".join([
            event_category,
            event_title,
            event_description
        ])

        if query_category not in category_search_text:
            return False

    if query_location:

        if query_location not in event_location:
            return False

    if query_keywords:

        searchable_text = " ".join([
            event_title,
            event_category,
            event_location,
            event_description
        ])

        for keyword in query_keywords:

            keyword = normalize_text(
                keyword
            )

            if (
                keyword
                and keyword not in searchable_text
            ):
                return False

    return True


def filter_events(events, query):

    return [
        event
        for event in events
        if event_matches(
            event,
            query
        )
    ]


# ============================================================
# FINAL EVENT RESPONSE
# ============================================================

def build_event_response(
    user_message,
    matching_events
):

    if not matching_events:

        return (
            "No matching event is "
            "currently available."
        )

    message = normalize_text(
        user_message
    )

    # LOCATION QUESTION
    if (
        "where" in message
        or "location" in message
    ):

        if len(
            matching_events
        ) == 1:

            event = (
                matching_events[0]
            )

            return (
                f"{event.get('title', 'The event')} "
                f"is at "
                f"{event.get('location', 'an unspecified location')}."
            )

    # SINGLE RESULT
    if len(
        matching_events
    ) == 1:

        event = matching_events[0]

        return (
            f"I found 1 matching event:\n\n"
            f"{event.get('title', '')} — "
            f"{event.get('date', '')} at "
            f"{event.get('location', '')}. "
            f"{event.get('description', '')}"
        )

    # MULTIPLE RESULTS

    lines = [
        (
            f"I found "
            f"{len(matching_events)} "
            f"matching events:"
        )
    ]

    for event in matching_events:

        lines.append(
            (
                f"- {event.get('title', '')} — "
                f"{event.get('date', '')} at "
                f"{event.get('location', '')}"
            )
        )

    return "\n".join(
        lines
    )


# ============================================================
# GROUNDED RESPONSE VALIDATION
# ============================================================

def grounded_response_is_valid(answer, retrieved_events):
    """
    Check that a generated RAG answer is consistent with
    the retrieved event context.

    The local 0.5B model can occasionally ignore supplied
    context. If that happens, the backend falls back to a
    deterministic answer built directly from the retrieved
    records instead of returning a contradiction.
    """

    if not isinstance(answer, str) or not answer.strip():
        return False

    if not retrieved_events:
        return True

    normalized_answer = normalize_text(answer)

    contradiction_phrases = [
        "no matching event",
        "no matching events",
        "no event is available",
        "no events are available",
        "no cybersecurity events",
        "there are no",
        "context is insufficient",
        "context provided is insufficient",
    ]

    if any(
        phrase in normalized_answer
        for phrase in contradiction_phrases
    ):
        return False

    retrieved_titles = [
        normalize_text(event.get("title"))
        for event in retrieved_events
        if isinstance(event, dict)
        and event.get("title")
    ]

    if retrieved_titles and not any(
        title in normalized_answer
        for title in retrieved_titles
    ):
        return False

    return True


# ============================================================
# RELEASE 1 - MCP TEST ENDPOINTS
# ============================================================

@ai_bp.route(
    "/api/mcp/event-count",
    methods=["GET"]
)
def mcp_event_count():

    outcome = call_mcp_tool(
        "event_count"
    )

    if not outcome["ok"]:

        return jsonify({
            "error": outcome.get(
                "error"
            ),

            "detail": outcome.get(
                "detail"
            )

        }), outcome.get(
            "status",
            500
        )

    return jsonify({
        "tool": "event_count",

        "result": outcome[
            "result"
        ]

    }), 200


@ai_bp.route(
    "/api/mcp/event-by-title",
    methods=["GET"]
)
def mcp_event_by_title():

    event_title = request.args.get(
        "title",
        ""
    ).strip()

    if not event_title:

        return jsonify({
            "error": "title is required"
        }), 400

    outcome = call_mcp_tool(
        "event_by_title",
        {
            "event_title": (
                event_title
            )
        }
    )

    if not outcome["ok"]:

        return jsonify({
            "error": outcome.get(
                "error"
            ),

            "detail": outcome.get(
                "detail"
            )

        }), outcome.get(
            "status",
            500
        )

    return jsonify({
        "tool": "event_by_title",

        "result": outcome[
            "result"
        ]

    }), 200


# ============================================================
# RELEASE 1 - RAG TEST ENDPOINT
# ============================================================

@ai_bp.route(
    "/api/rag/event",
    methods=["POST"]
)
def rag_event():

    data = request.get_json() or {}

    query = str(
        data.get(
            "query",
            ""
        )
    ).strip()

    if not query:

        return jsonify({
            "error": "query is required"
        }), 400

    outcome = retrieve_event_context(
        query,
        top_k=3
    )

    if not outcome["ok"]:

        return jsonify({
            "error": outcome.get(
                "error"
            ),

            "detail": outcome.get(
                "detail"
            )

        }), outcome.get(
            "status",
            500
        )

    return jsonify(
        outcome["result"]
    ), 200


# ============================================================
# MAIN AI API
# ============================================================

@ai_bp.route(
    "/api/ai",
    methods=["POST"]
)
def ai_assistant():

    data = request.get_json() or {}

    user_message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not user_message:

        return jsonify({
            "error": (
                "Message is required."
            )
        }), 400

    try:

        # ====================================================
        # RELEASE 1 - MCP EVENT COUNT
        # ====================================================

        if is_event_count_question(
            user_message
        ):

            outcome = call_mcp_tool(
                "event_count"
            )

            if not outcome["ok"]:

                raise RuntimeError(
                    outcome.get(
                        "error",
                        "MCP event_count failed"
                    )
                )

            result = outcome.get(
                "result",
                {}
            )

            if not isinstance(
                result,
                dict
            ):

                raise RuntimeError(
                    (
                        "MCP event_count "
                        "returned an invalid result"
                    )
                )

            event_count = result.get(
                "event_count"
            )

            if event_count is None:

                raise RuntimeError(
                    (
                        "MCP event_count "
                        "returned an invalid result"
                    )
                )

            final_answer = (
                f"There are {event_count} "
                f"campus events currently available."
            )

            return jsonify({
                "response": final_answer,

                "agentic_workflow": {
                    "mode": "mcp",

                    "plan": (
                        "Use the shared MCP event_count tool "
                        "to retrieve the verified total number "
                        "of Campus Event records."
                    ),

                    "tool": (
                        "event_count"
                    ),

                    "act": (
                        "Called the shared "
                        "MCP Server event_count tool."
                    ),

                    "observe": (
                        f"MCP returned "
                        f"{event_count} events."
                    ),

                    "adapt": (
                        final_answer
                    )
                }

            }), 200

        # ====================================================
        # GENERAL CONVERSATION
        # ====================================================

        if not needs_event_database(
            user_message
        ):

            chat_prompt = (
                build_chat_prompt(
                    user_message
                )
            )

            final_answer = call_llm(
                chat_prompt
            )

            return jsonify({
                "response": (
                    final_answer
                ),

                "agentic_workflow": {
                    "mode": (
                        "general_conversation"
                    )
                }

            }), 200

        # ====================================================
        # PLAN - RELEASE 1 RAG
        # ====================================================

        plan = (
            "Retrieve relevant Campus Event records "
            "from the shared RAG Server and answer "
            "only from the retrieved context."
        )

        # ====================================================
        # RELEASE 1 - RAG
        # ====================================================

        rag_outcome = (
            retrieve_event_context(
                user_message,
                top_k=5
            )
        )

        rag_matches = []
        rag_citations = []

        if rag_outcome.get(
            "ok"
        ):

            rag_result = (
                rag_outcome.get(
                    "result",
                    {}
                )
            )

            if (
                isinstance(
                    rag_result,
                    dict
                )
                and not rag_result.get(
                    "insufficient_context",
                    True
                )
            ):

                raw_matches = (
                    rag_result.get(
                        "matches",
                        []
                    )
                )

                for match in raw_matches:

                    if not isinstance(
                        match,
                        dict
                    ):
                        continue

                    context = (
                        match.get(
                            "context"
                        )
                    )

                    if isinstance(
                        context,
                        dict
                    ):

                        rag_matches.append(
                            context
                        )

                    citation = (
                        match.get(
                            "citation"
                        )
                    )

                    if citation:

                        rag_citations.append(
                            citation
                        )

        # ====================================================
        # RAG SUCCESS
        # ====================================================

        if rag_matches:

            grounded_prompt = (
                build_grounded_event_prompt(
                    user_message,
                    rag_matches
                )
            )

            generated_answer = call_llm(
                grounded_prompt
            ).strip()

            if grounded_response_is_valid(
                generated_answer,
                rag_matches
            ):
                final_answer = generated_answer
                grounding_method = "grounded_llm"
            else:
                final_answer = (
                    build_event_response(
                        user_message,
                        rag_matches
                    )
                )
                grounding_method = (
                    "retrieved_context_fallback"
                )

            observation = (
                f"RAG retrieved "
                f"{len(rag_matches)} relevant "
                f"Campus Event record(s)."
            )

            return jsonify({
                "response": (
                    final_answer
                ),

                "agentic_workflow": {
                    "mode": "rag",

                    "plan": plan,

                    "act": (
                        "Queried the shared "
                        "RAG Server for "
                        "Campus Event context."
                    ),

                    "observe": (
                        observation
                    ),

                    "citations": (
                        rag_citations
                    ),

                    "grounding": (
                        grounding_method
                    ),

                    "adapt": (
                        final_answer
                    )
                }

            }), 200

        # ====================================================
        # RELEASE 0 FALLBACK DATABASE WORKFLOW
        # ====================================================

        plan_prompt = (
            build_plan_prompt(
                user_message
            )
        )

        plan = call_llm(
            plan_prompt
        )

        query_prompt = (
            build_query_prompt(
                user_message
            )
        )

        query_response = call_llm(
            query_prompt
        )

        query = parse_query_json(
            query_response,
            user_message
        )

        events = get_events()

        if events is None:
            events = []

        matching_events = (
            filter_events(
                events,
                query
            )
        )

        if matching_events:

            observation = (
                f"Database search found "
                f"{len(matching_events)} matching events."
            )

        else:

            observation = (
                "Database search found no matching events."
            )

        final_answer = (
            build_event_response(
                user_message,
                matching_events
            )
        )

        return jsonify({
            "response": (
                final_answer
            ),

            "agentic_workflow": {
                "mode": (
                    "event_database"
                ),

                "rag_fallback": True,

                "plan": plan,

                "query": query,

                "act": (
                    f"Retrieved "
                    f"{len(events)} events "
                    f"and found "
                    f"{len(matching_events)} "
                    f"matches."
                ),

                "observe": (
                    observation
                ),

                "adapt": (
                    final_answer
                )
            }

        }), 200

    except RuntimeError as error:

        return jsonify({
            "error": str(error)
        }), 503

    except Exception as error:

        return jsonify({
            "error": (
                "An unexpected error occurred."
            ),

            "details": str(error)

        }), 500