import requests


DATABASE_URL = "http://localhost:5004"


def test_database_health():
    response = requests.get(
        f"{DATABASE_URL}/health",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_get_all_resources():
    response = requests.get(
        f"{DATABASE_URL}/resources",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0


def test_get_resource_by_id():
    response = requests.get(
        f"{DATABASE_URL}/resources/1",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert data["resource_id"] == 1
    assert "resource_name" in data
    assert "resource_type" in data


def test_create_update_delete_resource():
    # -----------------------------------------
    # CREATE
    # -----------------------------------------

    new_resource = {
        "resource_name": "AUTOMATED TEST RESOURCE",
        "resource_type": "Study Room",
        "building": "Building 11",
        "floor": "Level 1",
        "capacity": 4,
        "availability_status": "Available",
        "opening_hours": "9:00 AM - 5:00 PM",
        "location": "Automated Test Location",
        "description": "Temporary automated test resource."
    }

    create_response = requests.post(
        f"{DATABASE_URL}/resources",
        json=new_resource,
        timeout=5
    )

    assert create_response.status_code == 201

    created = create_response.json()

    resource_id = created["resource_id"]

    assert created["resource_name"] == (
        "AUTOMATED TEST RESOURCE"
    )

    # -----------------------------------------
    # UPDATE
    # -----------------------------------------

    update_data = {
        "capacity": 8,
        "availability_status": "Busy"
    }

    update_response = requests.put(
        f"{DATABASE_URL}/resources/{resource_id}",
        json=update_data,
        timeout=5
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["capacity"] == 8
    assert updated["availability_status"] == "Busy"

    # -----------------------------------------
    # DELETE
    # -----------------------------------------

    delete_response = requests.delete(
        f"{DATABASE_URL}/resources/{resource_id}",
        timeout=5
    )

    assert delete_response.status_code == 200

    # Confirm deleted
    get_response = requests.get(
        f"{DATABASE_URL}/resources/{resource_id}",
        timeout=5
    )

    assert get_response.status_code == 404