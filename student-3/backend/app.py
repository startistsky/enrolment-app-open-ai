from flask import Flask, jsonify, request
import sqlite3
from pathlib import Path

app = Flask(__name__)

# Path to the Student 3 SQLite database
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "campus_resources.db"


def get_db_connection():
    """
    Create a connection to the SQLite database.
    row_factory allows rows to behave like dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def resource_to_dict(resource):
    """Convert a SQLite row into a normal Python dictionary."""
    return dict(resource)


# ---------------------------------------------------------
# GET /resources
# Get all resources, with optional search and filtering
# ---------------------------------------------------------
@app.route("/resources", methods=["GET"])
def get_resources():
    search = request.args.get("search", "").strip()
    resource_type = request.args.get("type", "").strip()
    building = request.args.get("building", "").strip()
    availability = request.args.get("availability", "").strip()

    query = "SELECT * FROM campus_resources WHERE 1=1"
    params = []

    if search:
        query += """
            AND (
                resource_name LIKE ?
                OR resource_type LIKE ?
                OR building LIKE ?
                OR location LIKE ?
                OR description LIKE ?
            )
        """
        search_value = f"%{search}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

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
    resources = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([resource_to_dict(resource) for resource in resources]), 200


# ---------------------------------------------------------
# GET /resources/<id>
# Get one campus resource by ID
# ---------------------------------------------------------
@app.route("/resources/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):
    conn = get_db_connection()

    resource = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    conn.close()

    if resource is None:
        return jsonify({
            "error": "Campus resource not found"
        }), 404

    return jsonify(resource_to_dict(resource)), 200


# ---------------------------------------------------------
# POST /resources
# Create a new campus resource
# ---------------------------------------------------------
@app.route("/resources", methods=["POST"])
def create_resource():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body must contain JSON data"
        }), 400

    required_fields = [
        "resource_name",
        "resource_type",
        "building",
        "availability_status"
    ]

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
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

    new_resource_id = cursor.lastrowid

    new_resource = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (new_resource_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "message": "Campus resource created successfully",
        "resource": resource_to_dict(new_resource)
    }), 201


# ---------------------------------------------------------
# PUT /resources/<id>
# Update an existing campus resource
# ---------------------------------------------------------
@app.route("/resources/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id):
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body must contain JSON data"
        }), 400

    conn = get_db_connection()

    existing_resource = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    if existing_resource is None:
        conn.close()
        return jsonify({
            "error": "Campus resource not found"
        }), 404

    updated_resource = {
        "resource_name": data.get(
            "resource_name",
            existing_resource["resource_name"]
        ),
        "resource_type": data.get(
            "resource_type",
            existing_resource["resource_type"]
        ),
        "building": data.get(
            "building",
            existing_resource["building"]
        ),
        "floor": data.get(
            "floor",
            existing_resource["floor"]
        ),
        "capacity": data.get(
            "capacity",
            existing_resource["capacity"]
        ),
        "availability_status": data.get(
            "availability_status",
            existing_resource["availability_status"]
        ),
        "opening_hours": data.get(
            "opening_hours",
            existing_resource["opening_hours"]
        ),
        "location": data.get(
            "location",
            existing_resource["location"]
        ),
        "description": data.get(
            "description",
            existing_resource["description"]
        )
    }

    # Validate required fields after merging with existing values
    required_fields = [
        "resource_name",
        "resource_type",
        "building",
        "availability_status"
    ]

    missing_fields = [
        field for field in required_fields
        if not updated_resource.get(field)
    ]

    if missing_fields:
        conn.close()
        return jsonify({
            "error": "Required fields cannot be empty",
            "missing_fields": missing_fields
        }), 400

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
            updated_resource["resource_name"],
            updated_resource["resource_type"],
            updated_resource["building"],
            updated_resource["floor"],
            updated_resource["capacity"],
            updated_resource["availability_status"],
            updated_resource["opening_hours"],
            updated_resource["location"],
            updated_resource["description"],
            resource_id
        )
    )

    conn.commit()

    resource = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "message": "Campus resource updated successfully",
        "resource": resource_to_dict(resource)
    }), 200


# ---------------------------------------------------------
# DELETE /resources/<id>
# Delete an existing campus resource
# ---------------------------------------------------------
@app.route("/resources/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id):
    conn = get_db_connection()

    existing_resource = conn.execute(
        "SELECT * FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    ).fetchone()

    if existing_resource is None:
        conn.close()
        return jsonify({
            "error": "Campus resource not found"
        }), 404

    conn.execute(
        "DELETE FROM campus_resources WHERE resource_id = ?",
        (resource_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Campus resource deleted successfully"
    }), 200


# ---------------------------------------------------------
# Simple health check
# ---------------------------------------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "Campus Resource Management API"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5003,
        debug=True
    )