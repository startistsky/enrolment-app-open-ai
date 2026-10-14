from unittest.mock import Mock


URL = "/api/multi-agent/assignment-workflow"


def workflow(status="pending_human_review"):
    human = {
        "required": True,
        "status": "pending",
        "allowed_decisions": ["Accept", "Partially Accept", "Reject"],
    }
    if status == "completed":
        human.update(status="completed", decision="Accept", reason="Checked")
    return {
        "workflow_id": "assignment-workflow-1",
        "feature": "assignment_management",
        "status": status,
        "planner_result": {"plan": "Prioritise assignments"},
        "worker_result": {"answer": "Start assignment 1"},
        "reviewer_result": {"risk": "low"},
        "human_review": human,
    }


def database_response():
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = [
        {
            "assignment_id": 1,
            "student_id": "25220967",
            "assignment_title": "Release 2",
            "priority": "High",
        }
    ]
    return response


def test_assignment_workflow_endpoint(backend_client, backend_app, monkeypatch):
    get = Mock(return_value=database_response())
    post = Mock(return_value=Mock(status_code=200, json=Mock(return_value=workflow())))
    monkeypatch.setattr(backend_app.requests, "get", get)
    monkeypatch.setattr(backend_app.requests, "post", post)

    response = backend_client.post(
        URL,
        json={"user_request": "What should I do first?", "student_id": "25220967"},
    )
    assert response.status_code == 200
    assert response.get_json()["human_review"]["status"] == "pending"
    assert post.call_args.args[0].endswith("/workflow/assignment")
    assert post.call_args.kwargs["json"]["feature"] == "assignment_management"


def test_assignment_human_decision_endpoint(backend_client, backend_app, monkeypatch):
    post = Mock(
        return_value=Mock(status_code=200, json=Mock(return_value=workflow("completed")))
    )
    monkeypatch.setattr(backend_app.requests, "post", post)
    response = backend_client.post(
        f"{URL}/assignment-workflow-1/decision",
        json={"decision": "Accept", "reason": "Checked"},
    )
    assert response.status_code == 200
    assert response.get_json()["human_review"]["decision"] == "Accept"


def test_multi_agent_routes_disabled_in_cloud(
    backend_client, backend_app, monkeypatch
):
    monkeypatch.setenv("AI_SERVICES_ENABLED", "false")
    response = backend_client.post(
        URL,
        json={"user_request": "Prioritise", "student_id": "25220967"},
    )
    assert response.status_code == 503
    assert "disabled" in response.get_json()["error"]
