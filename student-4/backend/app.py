from flask import Flask, jsonify, send_from_directory, request
import requests
import sqlite3
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(
    BASE_DIR,
    "../database/events.db"
)

FRONTEND_DIR = os.path.join(
    BASE_DIR,
    "../frontend"
)

SHARED_CSS_DIR = os.path.join(
    BASE_DIR,
    "../../shared/frontend/css"
)


def get_events_ai():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, date, category, location, description
        FROM events
    """)

    events = cursor.fetchall()
    conn.close()

    return events


@app.route("/shared/css/<path:filename>")
def shared_css(filename):
    return send_from_directory(
        SHARED_CSS_DIR,
        filename
    )

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/js/<path:filename>")
def frontend_js(filename):
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "js"),
        filename
    )


@app.route("/api/events", methods=["GET"])
def get_events():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")

    rows = cursor.fetchall()

    conn.close()

    events = [dict(row) for row in rows]

    return jsonify(events)

@app.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json() or {}

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    date = data.get("date", "").strip()
    location = data.get("location", "").strip()
    description = data.get("description", "").strip()

    if not title or not category or not date or not location or not description:
        return jsonify({
            "error": "All required fields must be provided."
        }), 400

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO events (
            title,
            category,
            date,
            location,
            description
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            title,
            category,
            date,
            location,
            description,
        ),
    )

    event_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Event created successfully.",
        "id": event_id
    }), 201

@app.route("/api/events/<int:event_id>", methods=["PUT"])
def update_event(event_id):
    data = request.get_json() or {}

    title = data.get("title", "").strip()
    category = data.get("category", "").strip()
    date = data.get("date", "").strip()
    location = data.get("location", "").strip()
    description = data.get("description", "").strip()

    if not title or not category or not date or not location or not description:
        return jsonify({
            "error": "All required fields must be provided."
        }), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE events
        SET
            title = ?,
            category = ?,
            date = ?,
            location = ?,
            description = ?
        WHERE id = ?
        """,
        (
            title,
            category,
            date,
            location,
            description,
            event_id,
        ),
    )

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({
            "error": "Event not found."
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Event updated successfully."
    }), 200

@app.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,),
    )

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({
            "error": "Event not found."
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Event deleted successfully."
    }), 200


@app.route("/api/ai", methods=["POST"])
def ai_assistant():
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({"error": "Message is required"}), 400

    events = get_events_ai()

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

if __name__ == "__main__":
    app.run(debug=True, port=8000)