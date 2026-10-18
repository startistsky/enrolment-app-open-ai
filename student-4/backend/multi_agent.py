
import os
import requests
from flask import Blueprint, jsonify, request

from database_api import get_events

multi_agent_bp = Blueprint("multi_agent", __name__)

MULTI_AGENT_URL = os.getenv(
    "MULTI_AGENT_SERVER_URL",
    "http://host.docker.internal:9201"
).rstrip("/")


@multi_agent_bp.post("/api/multi-agent/event-workflow")
def event_workflow():
    """Start a Planner -> Worker -> Reviewer workflow."""

    # Release 2: Multi-Agent must be disabled in cloud mode.
    if os.getenv("MULTI_AGENT_ENABLED", "true").lower() != "true":
        return jsonify(error="Multi-Agent is disabled"), 503

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    user_message = body.get("user_request")
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify(error="user_request is required"), 400

    try:
        events = get_events()

        if not isinstance(events, list):
            return jsonify(error="Invalid database response"), 502

        response = requests.post(
            f"{MULTI_AGENT_URL}/workflow/event",
            json={
                "feature": "event_management",
                "user_request": user_message.strip(),
                "evidence": events
            },
            timeout=400
        )

        return jsonify(response.json()), response.status_code

    except requests.Timeout:
        return jsonify(error="Multi-Agent request timed out"), 503
    except (requests.RequestException, ValueError):
        return jsonify(error="Multi-Agent service unavailable"), 503


@multi_agent_bp.post(
    "/api/multi-agent/event-workflow/<workflow_id>/decision"
)
def review_decision(workflow_id):
    """Submit a human review decision."""

    if os.getenv("MULTI_AGENT_ENABLED", "true").lower() != "true":
        return jsonify(error="Multi-Agent is disabled"), 503

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    decision = body.get("decision")
    if decision not in ("Accept", "Partially Accept", "Reject"):
        return jsonify(error="Invalid decision"), 400

    reason = body.get("reason", "")
    if not isinstance(reason, str):
        return jsonify(error="reason must be a string"), 400

    try:
        response = requests.post(
            f"{MULTI_AGENT_URL}/workflow/{workflow_id}/decision",
            json={
                "decision": decision,
                "reason": reason
            },
            timeout=15
        )
        return jsonify(response.json()), response.status_code

    except requests.Timeout:
        return jsonify(error="Review request timed out"), 503
    except (requests.RequestException, ValueError):
        return jsonify(error="Multi-Agent service unavailable"), 503
