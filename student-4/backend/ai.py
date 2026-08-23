from flask import Blueprint, jsonify, request
import requests

from config import AI_SERVICE_URL, MODEL_NAME, AI_TIMEOUT
from database_api import get_events
from prompts import build_plan_prompt, build_adapt_prompt


ai_bp = Blueprint("ai", __name__)


def call_llm(prompt):
    """
    Send a prompt to the Ollama LLM service
    and return the generated response text.
    """

    try:
        response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
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


def build_observation(events):
    """
    Convert database event records into an observation
    that can be used by the Agentic AI workflow.
    """

    if not events:
        return "The database returned no campus events."

    event_text = "\n".join(
        [
            (
                f"Title: {event.get('title', '')}, "
                f"Date: {event.get('date', '')}, "
                f"Category: {event.get('category', '')}, "
                f"Location: {event.get('location', '')}, "
                f"Description: {event.get('description', '')}"
            )
            for event in events
        ]
    )

    observation = (
        f"The database returned {len(events)} campus events.\n"
        f"{event_text}"
    )

    return observation


@ai_bp.route("/api/ai", methods=["POST"])
def ai_assistant():
    """
    Agentic AI workflow:

    Plan -> Act -> Observe -> Adapt
    """

    data = request.get_json() or {}

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "error": "Message is required."
        }), 400

    try:

        # =====================================================
        # PLAN
        # =====================================================
        # The AI first decides what information it needs
        # to answer the user's request.

        plan_prompt = build_plan_prompt(user_message)

        plan = call_llm(plan_prompt)


        # =====================================================
        # ACT
        # =====================================================
        # The system performs an action by retrieving
        # real event information from the database service.

        events = get_events()

        if events is None:
            events = []


        # =====================================================
        # OBSERVE
        # =====================================================
        # The system examines the result of the database action.

        observation = build_observation(events)


        # =====================================================
        # ADAPT
        # =====================================================
        # The AI uses the original user request,
        # its plan, and the observed database information
        # to generate the final grounded response.

        adapt_prompt = build_adapt_prompt(
            user_message,
            plan,
            observation
        )

        final_answer = call_llm(adapt_prompt)


        # =====================================================
        # RESPONSE
        # =====================================================

        return jsonify({
            "response": final_answer,

            "agentic_workflow": {
                "plan": plan,

                "act": (
                    f"Retrieved {len(events)} events "
                    f"from the database service."
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