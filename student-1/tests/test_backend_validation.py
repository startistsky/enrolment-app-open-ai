def valid_course():
    return {
        "course_code": "TEST2001",
        "course_name": "Backend Test Course",
        "lecturer": "Test Lecturer",
        "semester": "Autumn 2026",
        "credit_points": 6,
        "course_description": "A course used to test backend validation.",
    }


def test_backend_health(backend_client):
    response = backend_client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["service"] == "course-backend"


def test_backend_rejects_missing_required_fields(backend_client):
    response = backend_client.post(
        "/api/courses",
        json={"course_code": "TEST2001"},
    )

    assert response.status_code == 400
    assert "Missing required fields" in response.get_json()["error"]


def test_backend_rejects_invalid_credit_points(backend_client):
    course = valid_course()
    course["credit_points"] = "six"

    response = backend_client.post("/api/courses", json=course)

    assert response.status_code == 400
    assert response.get_json()["error"] == "credit_points must be a positive integer"


def test_backend_rejects_non_positive_credit_points(backend_client):
    course = valid_course()
    course["credit_points"] = 0

    response = backend_client.post("/api/courses", json=course)

    assert response.status_code == 400
    assert response.get_json()["error"] == "credit_points must be a positive integer"
