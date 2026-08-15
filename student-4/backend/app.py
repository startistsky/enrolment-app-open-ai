from flask import Flask, jsonify, send_from_directory, request
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


if __name__ == "__main__":
    app.run(debug=True, port=8000)