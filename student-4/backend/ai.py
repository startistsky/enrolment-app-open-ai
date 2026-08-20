from flask import Blueprint, jsonify, request
import requests

from event_db import get_events_for_ai


ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/api/ai", methods=["POST"])
def ai_assistant():
    data = request.get_json() or {}

    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({
            "error": "Message is required"
        }), 400

    events = get_events_for_ai()

    event_text = "\n".join(
        [
            f"Title: {event[0]}, Date: {event[1]}, Category: {event[2]}, "
            f"Location: {event[3]}, Description: {event[4]}"
            for event in events
        ]
    )

    prompt = f"""
    You are a campus event assistant.

    Here are the ONLY real events currently available in the campus events database:

    {event_text}

    User question:
    {user_message}

    IMPORTANT RULES:
    1. You must only use events listed above.
    2. Never invent, suggest, or mention any event that is not listed above.
    3. If no event matches the user's request, simply say that no matching event is currently available.
    4. Do not provide hypothetical events.
    5. Do not suggest events from your own knowledge.
    6. Keep the answer concise.

    Answer based only on the database events above.
    """

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    result = response.json()

    ai_response = result.get("response", "")

    return jsonify({
        "response": ai_response
    })