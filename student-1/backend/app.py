import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app, origins=["http://localhost:8081"])

DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL", "http://localhost:5001"
).rstrip("/")
AI_SERVICE_URL = os.getenv(
    "AI_SERVICE_URL", "http://localhost:11434/api/generate"
)
AI_MODEL = "qwen2.5:0.5b"
REQUEST_TIMEOUT_SECONDS = 5
AI_REQUEST_TIMEOUT_SECONDS = 60

REQUIRED_COURSE_FIELDS = [
    "course_code",
    "course_name",
    "lecturer",
    "semester",
    "credit_points",
    "course_description",
]
TEXT_COURSE_FIELDS = [
    "course_code",
    "course_name",
    "lecturer",
    "semester",
    "course_description",
]


def database_request(method, path, **kwargs):
    try:
        return requests.request(
            method,
            f"{DATABASE_SERVICE_URL}{path}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        ), None
    except requests.RequestException:
        return None, (
            jsonify({"error": "Database service unavailable"}),
            503,
        )


def forward_database_response(response):
    try:
        body = response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from database service"}), 502

    return jsonify(body), response.status_code


def validate_course(data):
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object"

    missing_fields = [
        field
        for field in REQUIRED_COURSE_FIELDS
        if field not in data or data[field] is None or data[field] == ""
    ]
    if missing_fields:
        return None, f"Missing required fields: {', '.join(missing_fields)}"

    for field in TEXT_COURSE_FIELDS:
        if not isinstance(data[field], str) or not data[field].strip():
            return None, f"{field} must be a non-empty string"

    raw_credit_points = data["credit_points"]
    if isinstance(raw_credit_points, bool):
        return None, "credit_points must be a positive integer"

    if isinstance(raw_credit_points, int):
        credit_points = raw_credit_points
    elif isinstance(raw_credit_points, str) and raw_credit_points.strip().isdigit():
        credit_points = int(raw_credit_points.strip())
    else:
        return None, "credit_points must be a positive integer"

    if credit_points <= 0:
        return None, "credit_points must be a positive integer"

    validated = {field: data[field] for field in REQUIRED_COURSE_FIELDS}
    for field in TEXT_COURSE_FIELDS:
        validated[field] = validated[field].strip()
    validated["credit_points"] = credit_points

    return validated, None


def course_code_exists(course_code, excluded_course_id=None):
    response, error = database_request("GET", "/courses")
    if error:
        return None, error

    try:
        courses = response.json()
    except ValueError:
        return None, (
            jsonify({"error": "Invalid response from database service"}),
            502,
        )

    if response.status_code != 200 or not isinstance(courses, list):
        return None, forward_database_response(response)

    duplicate = any(
        course.get("course_code") == course_code
        and course.get("course_id") != excluded_course_id
        for course in courses
    )
    return duplicate, None


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "course-backend"})


@app.get("/api/courses")
def list_courses():
    response, error = database_request("GET", "/courses")
    if error:
        return error
    return forward_database_response(response)


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    return forward_database_response(response)


@app.post("/api/courses")
def create_course():
    course, validation_error = validate_course(request.get_json(silent=True))
    if validation_error:
        return jsonify({"error": validation_error}), 400

    duplicate, error = course_code_exists(course["course_code"])
    if error:
        return error
    if duplicate:
        return jsonify({"error": "Course code already exists"}), 409

    response, error = database_request("POST", "/courses", json=course)
    if error:
        return error
    return forward_database_response(response)


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    course, validation_error = validate_course(request.get_json(silent=True))
    if validation_error:
        return jsonify({"error": validation_error}), 400

    existing_response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    if existing_response.status_code != 200:
        return forward_database_response(existing_response)

    duplicate, error = course_code_exists(
        course["course_code"], excluded_course_id=course_id
    )
    if error:
        return error
    if duplicate:
        return jsonify({"error": "Course code already exists"}), 409

    response, error = database_request(
        "PUT", f"/courses/{course_id}", json=course
    )
    if error:
        return error
    return forward_database_response(response)


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    response, error = database_request("DELETE", f"/courses/{course_id}")
    if error:
        return error
    return forward_database_response(response)


@app.post("/api/courses/<int:course_id>/recommendation")
def generate_course_recommendation(course_id):
    course_response, error = database_request("GET", f"/courses/{course_id}")
    if error:
        return error
    if course_response.status_code != 200:
        return forward_database_response(course_response)

    try:
        course = course_response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from database service"}), 502

    if not isinstance(course, dict):
        return jsonify({"error": "Invalid response from database service"}), 502

    prompt = (
        "Give a short course summary followed by exactly 3 practical study "
        "recommendations. Be concise.\n"
        f"Course: {course.get('course_code')} - {course.get('course_name')}\n"
        f"Lecturer: {course.get('lecturer')}\n"
        f"Semester: {course.get('semester')}\n"
        f"Credit points: {course.get('credit_points')}\n"
        f"Description: {course.get('course_description')}"
    )

    try:
        ai_response = requests.post(
            AI_SERVICE_URL,
            json={
                "model": AI_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return jsonify({"error": "AI service request timed out"}), 504
    except requests.RequestException:
        return jsonify({"error": "AI service unavailable"}), 503

    if not ai_response.ok:
        return jsonify({"error": "AI service unavailable"}), 503

    try:
        ai_body = ai_response.json()
    except ValueError:
        return jsonify({"error": "Invalid response from AI service"}), 502

    recommendation = ai_body.get("response") if isinstance(ai_body, dict) else None
    if not isinstance(recommendation, str) or not recommendation.strip():
        return jsonify({"error": "Invalid response from AI service"}), 502

    return jsonify({
        "course_id": course_id,
        "recommendation": recommendation.strip(),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=True)
