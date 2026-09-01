import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "assignments.db"))
ALLOWED_PRIORITIES = {"Low", "Medium", "High"}
ALLOWED_STATUSES = {"Not Started", "In Progress", "Completed"}

app = Flask(__name__)


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def assignment_to_dict(row):
    return dict(row)


def validate_assignment(data, partial=False):
    errors = {}
    required = ("student_id", "subject_name", "assignment_title", "due_date", "priority", "status")
    if not partial:
        for field in required:
            if not str(data.get(field, "")).strip():
                errors[field] = "This field is required."

    if "priority" in data and data["priority"] not in ALLOWED_PRIORITIES:
        errors["priority"] = "Priority must be Low, Medium, or High."
    if "status" in data and data["status"] not in ALLOWED_STATUSES:
        errors["status"] = "Status must be Not Started, In Progress, or Completed."
    if "progress" in data:
        try:
            progress = int(data["progress"])
            if not 0 <= progress <= 100:
                raise ValueError
        except (TypeError, ValueError):
            errors["progress"] = "Progress must be a whole number from 0 to 100."
    return errors


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "service": "student-2-database"})


@app.get("/assignments")
def list_assignments():
    query = "SELECT * FROM assignments WHERE 1 = 1"
    params = []
    filters = {
        "student_id": "student_id",
        "subject": "subject_name",
        "status": "status",
        "priority": "priority",
    }
    for parameter, column in filters.items():
        value = request.args.get(parameter, "").strip()
        if value:
            query += f" AND {column} = ?"
            params.append(value)

    upcoming_days = request.args.get("upcoming_days", "").strip()
    if upcoming_days:
        try:
            days = max(0, int(upcoming_days))
        except ValueError:
            return jsonify({"error": "upcoming_days must be an integer"}), 400
        query += " AND date(due_date) BETWEEN date('now') AND date('now', ?)"
        params.append(f"+{days} days")

    sort = request.args.get("sort", "deadline")
    order_by = {
        "deadline": "date(due_date) ASC",
        "priority": "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, date(due_date) ASC",
        "progress": "progress DESC, date(due_date) ASC",
        "created": "datetime(created_time) DESC",
    }.get(sort, "date(due_date) ASC")
    query += f" ORDER BY {order_by}"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return jsonify([assignment_to_dict(row) for row in rows])


@app.get("/assignments/<int:assignment_id>")
def get_assignment(assignment_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "Assignment not found"}), 404
    return jsonify(assignment_to_dict(row))


@app.post("/assignments")
def create_assignment():
    data = request.get_json(silent=True) or {}
    data.setdefault("status", "Not Started")
    data.setdefault("progress", 0)
    errors = validate_assignment(data)
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO assignments (
                student_id, subject_name, assignment_title, description,
                due_date, priority, status, progress
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(data["student_id"]).strip(),
                data["subject_name"].strip(),
                data["assignment_title"].strip(),
                data.get("description", "").strip(),
                data["due_date"],
                data["priority"],
                data["status"],
                int(data["progress"]),
            ),
        )
        assignment_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
    return jsonify(assignment_to_dict(row)), 201


@app.put("/assignments/<int:assignment_id>")
def update_assignment(assignment_id):
    data = request.get_json(silent=True) or {}
    with get_connection() as connection:
        current = connection.execute(
            "SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        if current is None:
            return jsonify({"error": "Assignment not found"}), 404

        merged = assignment_to_dict(current)
        merged.update(data)
        errors = validate_assignment(merged)
        if errors:
            return jsonify({"error": "Validation failed", "fields": errors}), 400

        connection.execute(
            """
            UPDATE assignments SET
                student_id = ?, subject_name = ?, assignment_title = ?,
                description = ?, due_date = ?, priority = ?, status = ?,
                progress = ?, updated_time = CURRENT_TIMESTAMP
            WHERE assignment_id = ?
            """,
            (
                str(merged["student_id"]).strip(), merged["subject_name"].strip(),
                merged["assignment_title"].strip(), merged.get("description", "").strip(),
                merged["due_date"], merged["priority"], merged["status"],
                int(merged["progress"]), assignment_id,
            ),
        )
        row = connection.execute(
            "SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
    return jsonify(assignment_to_dict(row))


@app.delete("/assignments/<int:assignment_id>")
def delete_assignment(assignment_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM assignments WHERE assignment_id = ?", (assignment_id,)
        )
    if cursor.rowcount == 0:
        return jsonify({"error": "Assignment not found"}), 404
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
