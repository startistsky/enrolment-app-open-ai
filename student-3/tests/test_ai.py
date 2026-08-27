import requests


BACKEND_URL = "http://localhost:8003"


def post_recommendation(question):
    return requests.post(
        f"{BACKEND_URL}/recommend",
        json={
            "question": question
        },
        timeout=60
    )


def test_recommend_requires_question():
    response = requests.post(
        f"{BACKEND_URL}/recommend",
        json={},
        timeout=5
    )

    assert response.status_code == 400

    data = response.json()

    assert data["error"] == "Question is required"


def test_printer_candidate_filtering():
    response = post_recommendation(
        "Where can I print something?"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["model"] == "qwen2.5:0.5b"

    candidates = data["candidate_resources"]

    assert len(candidates) > 0

    for candidate in candidates:
        assert (
            candidate["resource_type"]
            == "Printer"
        )


def test_computer_lab_candidate_filtering():
    response = post_recommendation(
        "I need a computer lab that is currently available."
    )

    assert response.status_code == 200

    data = response.json()

    candidates = data["candidate_resources"]

    assert len(candidates) > 0

    for candidate in candidates:
        assert (
            candidate["resource_type"]
            == "Computer Lab"
        )

        assert (
            candidate["availability_status"]
            == "Available"
        )


def test_study_room_capacity_filtering():
    response = post_recommendation(
        "I need a study room for 6 people."
    )

    assert response.status_code == 200

    data = response.json()

    candidates = data["candidate_resources"]

    assert len(candidates) > 0

    for candidate in candidates:
        if (
            candidate["resource_type"]
            == "Study Room"
        ):
            assert candidate["resource_id"] is not None


def test_ai_returns_recommendation():
    response = post_recommendation(
        "I need a quiet place to study."
    )

    assert response.status_code == 200

    data = response.json()

    assert "recommendation" in data

    assert (
        len(
            data["recommendation"].strip()
        )
        > 0
    )

    assert data["candidate_count"] > 0


def test_negation_excludes_printer_and_library():
    response = post_recommendation(
        "I need an available computer lab, not a printer or library."
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        "Computer Lab"
        in data["requested_resource_types"]
    )

    assert (
        "Printer"
        in data["excluded_resource_types"]
    )

    assert (
        "Library"
        in data["excluded_resource_types"]
    )

    candidates = data["candidate_resources"]

    assert len(candidates) > 0

    for candidate in candidates:
        assert (
            candidate["resource_type"]
            == "Computer Lab"
        )


def test_negation_excludes_study_rooms():
    response = post_recommendation(
        "I only want a printer. Do not recommend study rooms."
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        "Printer"
        in data["requested_resource_types"]
    )

    assert (
        "Study Room"
        in data["excluded_resource_types"]
    )

    candidates = data["candidate_resources"]

    assert len(candidates) > 0

    for candidate in candidates:
        assert (
            candidate["resource_type"]
            == "Printer"
        )