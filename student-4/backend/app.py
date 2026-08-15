from flask import Flask, jsonify, send_from_directory
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)