from flask import Blueprint, jsonify, request
import os
import requests

from database_api import get_events


ai_bp = Blueprint("ai", __name__)

AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL",
    "http://ollama:11434/api/generate"
)


@ai_bp.route("/api/ai", methods=["POST"])
def ai_assistant():
    data = request.get_json() or {}

    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "error": "Message is required"
        }), 400

    events = get_events()

    event_text = "\n".join(
        [
            (
                f"Title: {event['title']}, "
                f"Date: {event['date']}, "
                f"Category: {event['category']}, "
                f"Location: {event['location']}, "
                f"Description: {event['description']}"
            )
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
        AI_SERVICE_URL,
        json={
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    return jsonify({
        "response": result.get("response", "")
    })