from flask import Flask, jsonify, request
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).resolve().parent / "data" / "courses.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL UNIQUE,
            course_name TEXT NOT NULL,
            lecturer TEXT NOT NULL,
            semester TEXT NOT NULL,
            credit_points INTEGER NOT NULL,
            course_description TEXT
        )
    """)
    count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if count == 0:
        courses = [
            ("COMP1001", "Introduction to Information Technology", "Dr. John Smith", "Spring 2026", 6, "Introduction to core information technology concepts."),
            ("COMP1531", "Programming Fundamentals", "Prof. Jane Lee", "Spring 2026", 6, "Programming fundamentals and problem solving."),
            ("COMP2511", "Data Structures and Algorithms", "Dr. Michael Chan", "Autumn 2026", 6, "Core data structures and algorithm design."),
            ("COMP3311", "Database Systems", "Dr. Sarah Brown", "Autumn 2026", 6, "Relational databases, SQL and data modelling."),
            ("COMP4101", "Software Engineering", "Prof. David Wilson", "Spring 2026", 6, "Software engineering processes and practices."),
            ("COMP4201", "Web Development", "Dr. Emily Davis", "Autumn 2026", 6, "Modern web application development."),
            ("COMP5111", "Artificial Intelligence", "Prof. James Miller", "Spring 2026", 6, "Foundations of artificial intelligence."),
            ("COMP5231", "Machine Learning", "Dr. Anna Zhang", "Autumn 2026", 6, "Machine learning concepts and applications."),
            ("COMP6101", "Computer Networks", "Prof. Robert Taylor", "Spring 2026", 6, "Computer networking principles and protocols."),
            ("COMP6901", "Capstone Project", "Dr. Lisa Wang", "Autumn 2026", 12, "Team-based capstone software project.")
        ]
        conn.executemany("""
            INSERT INTO courses
            (course_code, course_name, lecturer, semester, credit_points, course_description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, courses)
    conn.commit()
    conn.close()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "course-database"})


@app.get("/courses")
def list_courses():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM courses ORDER BY course_id").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/courses/<int:course_id>")
def get_course(course_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(dict(row))


@app.post("/courses")
def create_course():
    data = request.get_json() or {}
    required = ["course_code", "course_name", "lecturer", "semester", "credit_points"]
    if any(not data.get(field) for field in required):
        return jsonify({"error": "Missing required course fields"}), 400
    try:
        conn = get_connection()
        cursor = conn.execute("""
            INSERT INTO courses
            (course_code, course_name, lecturer, semester, credit_points, course_description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["course_code"], data["course_name"], data["lecturer"],
            data["semester"], int(data["credit_points"]), data.get("course_description", "")
        ))
        conn.commit()
        course_id = cursor.lastrowid
        conn.close()
        return jsonify({"course_id": course_id, "message": "Course created"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Course code already exists"}), 409


@app.put("/courses/<int:course_id>")
def update_course(course_id):
    data = request.get_json() or {}
    required = ["course_code", "course_name", "lecturer", "semester", "credit_points"]
    if any(not data.get(field) for field in required):
        return jsonify({"error": "Missing required course fields"}), 400
    conn = get_connection()
    cursor = conn.execute("""
        UPDATE courses
        SET course_code = ?, course_name = ?, lecturer = ?, semester = ?,
            credit_points = ?, course_description = ?
        WHERE course_id = ?
    """, (
        data["course_code"], data["course_name"], data["lecturer"], data["semester"],
        int(data["credit_points"]), data.get("course_description", ""), course_id
    ))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    if changed == 0:
        return jsonify({"error": "Course not found"}), 404
    return jsonify({"message": "Course updated"})


@app.delete("/courses/<int:course_id>")
def delete_course(course_id):
    conn = get_connection()
    cursor = conn.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    if changed == 0:
        return jsonify({"error": "Course not found"}), 404
    return jsonify({"message": "Course deleted"})


if __name__ == "__main__":
    init_db()
    print("Database initialized with 10 courses.")
    app.run(host="0.0.0.0", port=5001, debug=True)
