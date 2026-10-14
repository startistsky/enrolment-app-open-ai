def assignment_payload():
    return {
        "student_id": "25220967",
        "subject_name": "Advanced Software Development",
        "assignment_title": "Release 2 Endpoint Test",
        "description": "Validate the Student 2 assignment API.",
        "due_date": "2026-10-23",
        "priority": "High",
        "status": "Not Started",
        "progress": 0,
    }


def test_list_assignments_endpoint(database_client):
    response = database_client.get("/assignments?student_id=25220967")
    assert response.status_code == 200
    assert len(response.get_json()) >= 10


def test_create_read_update_delete_assignment_endpoints(database_client):
    created = database_client.post("/assignments", json=assignment_payload())
    assert created.status_code == 201
    assignment_id = created.get_json()["assignment_id"]

    read = database_client.get(f"/assignments/{assignment_id}")
    assert read.status_code == 200
    assert read.get_json()["assignment_title"] == "Release 2 Endpoint Test"

    updated = database_client.put(
        f"/assignments/{assignment_id}",
        json={"status": "In Progress", "progress": 40},
    )
    assert updated.status_code == 200
    assert updated.get_json()["progress"] == 40

    deleted = database_client.delete(f"/assignments/{assignment_id}")
    assert deleted.status_code == 204
    assert database_client.get(f"/assignments/{assignment_id}").status_code == 404
