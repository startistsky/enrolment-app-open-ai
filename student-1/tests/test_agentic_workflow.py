from unittest.mock import Mock


COURSE = {
    "course_id": 1,
    "course_code": "COMP1001",
    "course_name": "Introduction to Information Technology",
    "lecturer": "Dr. John Smith",
    "semester": "Spring 2026",
    "credit_points": 6,
    "course_description": "Introduction to core information technology concepts.",
}

VALID_RECOMMENDATION = """Summary: A concise introduction to core IT concepts.
Study Recommendations:
1. Review the lecture material after each class.
2. Practise the core concepts with small exercises.
3. Create a weekly revision plan."""


def database_course_response():
    response = Mock(status_code=200)
    response.json.return_value = COURSE
    return response


def ollama_response(text):
    response = Mock(ok=True)
    response.json.return_value = {"response": text}
    return response


def test_valid_first_response_does_not_retry(
    backend_app,
    backend_client,
    monkeypatch,
):
    monkeypatch.setattr(
        backend_app,
        "database_request",
        Mock(return_value=(database_course_response(), None)),
    )
    mocked_ollama = Mock(return_value=ollama_response(VALID_RECOMMENDATION))
    monkeypatch.setattr(backend_app.requests, "post", mocked_ollama)

    response = backend_client.post("/api/courses/1/recommendation")

    assert response.status_code == 200
    body = response.get_json()
    assert body["recommendation"] == VALID_RECOMMENDATION
    assert [item["phase"] for item in body["agentic_trace"]] == [
        "plan", "act", "observe", "adapt"
    ]
    assert body["agentic_trace"][2]["status"] == "passed"
    assert body["agentic_trace"][3]["status"] == "not_required"
    assert mocked_ollama.call_count == 1


def test_invalid_first_response_triggers_one_corrective_retry(
    backend_app,
    backend_client,
    monkeypatch,
):
    monkeypatch.setattr(
        backend_app,
        "database_request",
        Mock(return_value=(database_course_response(), None)),
    )
    mocked_ollama = Mock(side_effect=[
        ollama_response("Study this course carefully."),
        ollama_response(VALID_RECOMMENDATION),
    ])
    monkeypatch.setattr(backend_app.requests, "post", mocked_ollama)

    response = backend_client.post("/api/courses/1/recommendation")

    assert response.status_code == 200
    body = response.get_json()
    assert body["recommendation"] == VALID_RECOMMENDATION
    assert body["agentic_trace"][2]["status"] == "correction_required"
    assert body["agentic_trace"][3]["status"] == "completed"
    assert mocked_ollama.call_count == 2
    corrected_prompt = mocked_ollama.call_args_list[1].kwargs["json"]["prompt"]
    assert "previous response did not match" in corrected_prompt
