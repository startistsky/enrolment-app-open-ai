import os
import requests

from flask import Blueprint, request, jsonify

multi_agent_routes = Blueprint(
    "multi_agent_routes",
    __name__,
)

MULTI_AGENT_SERVER_URL = os.getenv(
    "MULTI_AGENT_SERVER_URL",
    "http://127.0.0.1:9201",
).rstrip("/")



REQUEST_TIMEOUT = (5, 180)


def proxy_request(method, path, payload=None):
    """Forward a request to the shared multi-agent server."""

    url = f"{MULTI_AGENT_SERVER_URL}{path}"

    try:
        response = requests.request(
            method=method,
            url=url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            data = response.json()
        except ValueError:
            data = {"error": "Invalid response from multi-agent server."}

        return jsonify(data), response.status_code

    except requests.Timeout:
        return jsonify({
            "success": False,
            "error": "The multi-agent server timed out.",
        }), 504

    except requests.RequestException:
        return jsonify({
            "success": False,
            "error": "Could not connect to the multi-agent server.",
        }), 502


@multi_agent_routes.route(
    "/workflow/career",
    methods=["POST"],
)
def start_career_workflow():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "success": False,
            "error": "A JSON request body is required.",
        }), 400

    user_request = payload.get("user_request")
    selected_job = payload.get("selected_job")

    if not isinstance(user_request, str) or not user_request.strip():
        return jsonify({
            "success": False,
            "error": "User request is required.",
        }), 400

    if not isinstance(selected_job, dict) or not selected_job.get("id"):
        return jsonify({
            "success": False,
            "error": "A selected job with an ID is required.",
        }), 400

    # Forward to the shared server.
    return proxy_request(
        "POST",
        "/workflow/career",
        {
            "feature": "career_management",
            "user_request": user_request.strip(),
            "selected_job": selected_job,
            "career_details": payload.get("career_details", {}),
        },
    )


@multi_agent_routes.route(
    "/workflow/<workflow_id>/decision",
    methods=["POST"],
)
def submit_workflow_decision(workflow_id):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "success": False,
            "error": "A JSON request body is required.",
        }), 400

    return proxy_request(
        "POST",
        f"/workflow/{workflow_id}/decision",
        {
            "decision": payload.get("decision", ""),
            "reason": payload.get("reason", ""),
        },
    )


@multi_agent_routes.route(
    "/workflow/status",
    methods=["GET"],
)
def workflow_status():
    return proxy_request(
        "GET",
        "/workflow/status",
    )
