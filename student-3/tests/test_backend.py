import requests


BACKEND_URL = "http://localhost:8003"


def test_backend_health():
    response = requests.get(
        f"{BACKEND_URL}/health",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"

    assert (
        data["service"]
        == "Campus Resource Management Backend API"
    )


def test_backend_get_resources():
    response = requests.get(
        f"{BACKEND_URL}/resources",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0


def test_backend_get_resource_by_id():
    response = requests.get(
        f"{BACKEND_URL}/resources/1",
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert data["resource_id"] == 1

    assert data["resource_name"] == "UTS Library"


def test_backend_invalid_resource():
    response = requests.get(
        f"{BACKEND_URL}/resources/999999",
        timeout=5
    )

    assert response.status_code == 404


def test_backend_search_filter():
    response = requests.get(
        f"{BACKEND_URL}/resources",
        params={
            "type": "Computer Lab"
        },
        timeout=5
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) > 0

    for resource in data:
        assert (
            resource["resource_type"]
            == "Computer Lab"
        )