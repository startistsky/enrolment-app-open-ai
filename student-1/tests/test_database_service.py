def test_database_health(database_client):
    response = database_client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["service"] == "course-database"


def test_database_starts_with_seeded_courses(database_client):
    response = database_client.get("/courses")

    assert response.status_code == 200
    assert len(response.get_json()) >= 10


def test_database_course_crud(database_client):
    course = {
        "course_code": "TEST1001",
        "course_name": "Test Course",
        "lecturer": "Test Lecturer",
        "semester": "Spring 2026",
        "credit_points": 6,
        "course_description": "A course created by the automated tests.",
    }

    create_response = database_client.post("/courses", json=course)
    assert create_response.status_code == 201
    course_id = create_response.get_json()["course_id"]

    updated_course = {
        **course,
        "course_name": "Updated Test Course",
        "course_description": "An updated automated test course.",
    }
    update_response = database_client.put(
        f"/courses/{course_id}",
        json=updated_course,
    )
    assert update_response.status_code == 200

    get_response = database_client.get(f"/courses/{course_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["course_name"] == "Updated Test Course"

    delete_response = database_client.delete(f"/courses/{course_id}")
    assert delete_response.status_code == 200

    deleted_response = database_client.get(f"/courses/{course_id}")
    assert deleted_response.status_code == 404
