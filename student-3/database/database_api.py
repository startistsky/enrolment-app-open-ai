from flask import Flask, jsonify, request
import sqlite3
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campus_resources.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "Student 3 Campus Resource Database API"
    }), 200


@app.route("/resources", methods=["GET"])
def get_resources():
    search = request.args.get("search", "").strip()
    resource_type = request.args.get("type", "").strip()
    building = request.args.get("building", "").strip()
    availability = request.args.get("availability", "").strip()

    query = "SELECT * FROM campus_resources WHERE 1=1"
    params = []

    if search:
        value = f"%{search}%"
        query += """
            AND (
                resource_name LIKE ?
                OR resource_type LIKE ?
                OR building LIKE ?
                OR location LIKE ?
                OR description LIKE ?
            )
        """
        params.extend([value, value, value, value, value])

    if resource_type:
        query += " AND resource_type = ?"
        params.append(resource_type)

    if building:
        query += " AND building = ?"
        params.append(building)

    if availability:
        query += " AND availability_status = ?"
        params.append(availability)

    query += " ORDER BY resource_id"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([row_to_dict(row) for row in rows]), 200


@app.route("/resources/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    conn = get_db_connection()

    row = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return jsonify({"error": "Campus resource not found"}), 404

    return jsonify(row_to_dict(row)), 200


@app.route("/resources", methods=["POST"])
def create_resource():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required_fields = [
        "resource_name",
        "resource_type",
        "building",
        "availability_status"
    ]

    missing = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing
        }), 400

    conn = get_db_connection()

    cursor = conn.execute(
        """
        INSERT INTO campus_resources (
            resource_name,
            resource_type,
            building,
            floor,
            capacity,
            availability_status,
            opening_hours,
            location,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["resource_name"],
            data["resource_type"],
            data["building"],
            data.get("floor"),
            data.get("capacity"),
            data["availability_status"],
            data.get("opening_hours"),
            data.get("location"),
            data.get("description")
        )
    )

    conn.commit()

    new_id = cursor.lastrowid

    row = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (new_id,)
    ).fetchone()

    conn.close()

    return jsonify(row_to_dict(row)), 201


@app.route("/resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body required"}), 400

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Campus resource not found"}), 404

    updated = {
        "resource_name": data.get("resource_name", existing["resource_name"]),
        "resource_type": data.get("resource_type", existing["resource_type"]),
        "building": data.get("building", existing["building"]),
        "floor": data.get("floor", existing["floor"]),
        "capacity": data.get("capacity", existing["capacity"]),
        "availability_status": data.get(
            "availability_status",
            existing["availability_status"]
        ),
        "opening_hours": data.get("opening_hours", existing["opening_hours"]),
        "location": data.get("location", existing["location"]),
        "description": data.get("description", existing["description"])
    }

    conn.execute(
        """
        UPDATE campus_resources
        SET
            resource_name = ?,
            resource_type = ?,
            building = ?,
            floor = ?,
            capacity = ?,
            availability_status = ?,
            opening_hours = ?,
            location = ?,
            description = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE resource_id = ?
        """,
        (
            updated["resource_name"],
            updated["resource_type"],
            updated["building"],
            updated["floor"],
            updated["capacity"],
            updated["availability_status"],
            updated["opening_hours"],
            updated["location"],
            updated["description"],
            resource_id
        )
    )

    conn.commit()

    row = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    conn.close()

    return jsonify(row_to_dict(row)), 200


@app.route("/resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Campus resource not found"}), 404

    conn.execute(
        "DELETE FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Campus resource deleted successfully"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5004,
        debug=True
    )
    