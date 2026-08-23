import os
import sys
from unittest.mock import patch


# Add the backend folder to Python's import path.
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BACKEND_DIR = os.path.join(BASE_DIR, "backend")

sys.path.insert(0, BACKEND_DIR)


from app import app


def get_test_client():
    app.config["TESTING"] = True
    return app.test_client()


def test_read_events():
    """
    Test READ operation:
    GET /api/events
    """

    fake_events = [
        {
            "id": 1,
            "title": "Career Fair",
            "category": "Career",
            "date": "2026-08-25",
            "location": "Building A",
            "description": "University career fair"
        },
        {
            "id": 2,
            "title": "AI Workshop",
            "category": "Technology",
            "date": "2026-08-26",
            "location": "Building B",
            "description": "Introduction to AI"
        }
    ]

    with patch(
        "events.get_events_db",
        return_value=fake_events
    ):
        client = get_test_client()

        response = client.get("/api/events")

        assert response.status_code == 200

        data = response.get_json()

        assert len(data) == 2
        assert data[0]["title"] == "Career Fair"
        assert data[1]["title"] == "AI Workshop"


def test_create_event():
    """
    Test CREATE operation:
    POST /api/events
    """

    new_event = {
        "title": "Python Workshop",
        "category": "Technology",
        "date": "2026-08-30",
        "location": "Room 101",
        "description": "Learn Python basics",
        "emoji": "🐍"
    }

    with patch(
        "events.create_event_db",
        return_value=100
    ) as mock_create:

        client = get_test_client()

        response = client.post(
            "/api/events",
            json=new_event
        )

        assert response.status_code == 201

        data = response.get_json()

        assert data["message"] == "Event created successfully."
        assert data["id"] == 100

        mock_create.assert_called_once_with(
            "Python Workshop",
            "Technology",
            "2026-08-30",
            "Room 101",
            "Learn Python basics",
            "🐍"
        )


def test_update_event():
    """
    Test UPDATE operation:
    PUT /api/events/<id>
    """

    updated_event = {
        "title": "Updated Python Workshop",
        "category": "Technology",
        "date": "2026-08-31",
        "location": "Room 202",
        "description": "Updated workshop information",
        "emoji": "💻"
    }

    with patch(
        "events.update_event_db",
        return_value=True
    ) as mock_update:

        client = get_test_client()

        response = client.put(
            "/api/events/100",
            json=updated_event
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["message"] == "Event updated successfully."

        mock_update.assert_called_once_with(
            100,
            "Updated Python Workshop",
            "Technology",
            "2026-08-31",
            "Room 202",
            "Updated workshop information",
             "💻"
        )


def test_delete_event():
    """
    Test DELETE operation:
    DELETE /api/events/<id>
    """

    with patch(
        "events.delete_event_db",
        return_value=True
    ) as mock_delete:

        client = get_test_client()

        response = client.delete(
            "/api/events/100"
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["message"] == "Event deleted successfully."

        mock_delete.assert_called_once_with(100)


def test_create_event_missing_required_field():
    """
    Test validation:
    CREATE should fail when a required field is missing.
    """

    invalid_event = {
        "title": "Incomplete Event",
        "category": "Technology",
        "date": "2026-08-30",
        "location": "",
        "description": "Missing location"
    }

    client = get_test_client()

    response = client.post(
        "/api/events",
        json=invalid_event
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "All required fields must be provided."


def test_update_event_not_found():
    """
    Test UPDATE when event does not exist.
    """

    valid_event = {
        "title": "Unknown Event",
        "category": "Other",
        "date": "2026-08-30",
        "location": "Unknown",
        "description": "Testing event not found"
    }

    with patch(
        "events.update_event_db",
        return_value=False
    ):

        client = get_test_client()

        response = client.put(
            "/api/events/9999",
            json=valid_event
        )

        assert response.status_code == 404

        data = response.get_json()

        assert data["error"] == "Event not found."


def test_delete_event_not_found():
    """
    Test DELETE when event does not exist.
    """

    with patch(
        "events.delete_event_db",
        return_value=False
    ):

        client = get_test_client()

        response = client.delete(
            "/api/events/9999"
        )

        assert response.status_code == 404

        data = response.get_json()

        assert data["error"] == "Event not found."