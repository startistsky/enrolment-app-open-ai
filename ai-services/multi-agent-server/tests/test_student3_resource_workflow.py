"""End-to-end API tests for Student 3 Resource Management workflow."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


SERVER = Path(__file__).resolve().parents[1]

if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

spec = importlib.util.spec_from_file_location(
    "student3_multi_agent_app", SERVER / "app.py"
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

from agents import (  # noqa: E402
    resource_planner_agent,
    resource_worker_agent,
    resource_reviewer_agent,
)
import llm_client  # noqa: E402


@pytest.fixture
def setup(tmp_path, monkeypatch):
    calls = []

    outputs = {
        "planner": {
            "plan": "Find an available study room for four students.",
            "evidence_required": ["1"],
        },
        "worker": {
            "answer": "Study Room A (ID: 1, capacity: 6, status: Available)",
            "evidence_used": ["1"],
            "missing_evidence": [],
        },
        "reviewer": {
            "risk": "No unsupported claims identified.",
            "unsupported_claims": [],
            "correction": "",
            "recommendation": "Proceed to human review.",
        },
    }

    def stage(role):
        def run(*args):
            calls.append(role)
            return outputs[role]
        return run

    monkeypatch.setattr(resource_planner_agent, "run", stage("planner"))
    monkeypatch.setattr(resource_worker_agent, "run", stage("worker"))
    monkeypatch.setattr(resource_reviewer_agent, "run", stage("reviewer"))

    history = tmp_path / "history.jsonl"
    audit = tmp_path / "audit.jsonl"

    app = server.create_app(history, audit)
    app.config.update(TESTING=True)

    return app.test_client(), calls, history, audit


def payload():
    return {
        "user_request": "Find an available study room for 4 students.",
        "feature": "resource_management",
        "evidence": [
            {
                "resource_id": 1,
                "resource_name": "Study Room A",
                "resource_type": "Study Room",
                "capacity": 6,
                "availability_status": "Available",
            }
        ],
    }


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_resource_workflow_order_and_pending_review(setup):
    client, calls, history, audit = setup

    response = client.post("/workflow/resource", json=payload())

    assert response.status_code == 200
    body = response.get_json()

    assert calls == ["planner", "worker", "reviewer"]
    assert body["feature"] == "resource_management"
    assert body["status"] == "pending_human_review"
    assert body["human_review"]["required"] is True
    assert body["human_review"]["status"] == "pending"

    assert body["worker_result"]["evidence_used"] == ["1"]

    events = [row["event"] for row in read_jsonl(audit)]

    assert events == [
        "started",
        "planner_completed",
        "worker_completed",
        "reviewer_completed",
        "human_review_pending",
    ]

    snapshots = read_jsonl(history)
    assert len(snapshots) == 1
    assert snapshots[0]["status"] == "pending_human_review"


@pytest.mark.parametrize(
    ("prompt_name", "required_fields", "output"),
    [
        (
            "resource_planner",
            {"plan": str, "evidence_required": list},
            {"plan": "Find a matching room.", "evidence_required": ["capacity"]},
        ),
        (
            "resource_worker",
            {
                "answer": str,
                "evidence_used": list,
                "missing_evidence": list,
            },
            {
                "answer": "Study Room A meets the requirements.",
                "evidence_used": ["1"],
                "missing_evidence": [],
            },
        ),
        (
            "resource_reviewer",
            {
                "risk": str,
                "unsupported_claims": list,
                "correction": str,
                "recommendation": str,
            },
            {
                "risk": "No unsupported claims identified.",
                "unsupported_claims": [],
                "correction": "",
                "recommendation": "Proceed to human review.",
            },
        ),
    ],
)
def test_resource_prompts_use_bounded_schema_valid_generation(
    monkeypatch, prompt_name, required_fields, output
):
    post = Mock(return_value=Mock(
        ok=True,
        json=Mock(return_value={"response": json.dumps(output)}),
    ))
    monkeypatch.setattr(llm_client.requests, "post", post)

    result = llm_client.generate(
        prompt_name,
        {"user_request": "Find a room.", "evidence": []},
        required_fields,
        prompt_name=prompt_name,
    )

    assert result == output
    request = post.call_args.kwargs["json"]
    assert request["options"]["num_predict"] == 256
    assert request["format"]["required"] == list(required_fields)
    assert request["format"]["additionalProperties"] is False


def test_non_resource_prompt_has_no_resource_generation_limit(monkeypatch):
    post = Mock(return_value=Mock(
        ok=True,
        json=Mock(return_value={"response": '{"plan": "Summarize the courses."}'}),
    ))
    monkeypatch.setattr(llm_client.requests, "post", post)

    assert llm_client.generate(
        "planner",
        {},
        {"plan": str},
    ) == {"plan": "Summarize the courses."}
    assert "num_predict" not in post.call_args.kwargs["json"]["options"]


@pytest.mark.parametrize(
    "decision", ["Accept", "Partially Accept", "Reject"]
)
def test_resource_human_decision_and_audit(setup, decision):
    client, calls, history, audit = setup

    start = client.post("/workflow/resource", json=payload())
    workflow_id = start.get_json()["workflow_id"]

    response = client.post(
        f"/workflow/{workflow_id}/decision",
        json={
            "decision": decision,
            "reason": "Resource evidence checked by human reviewer.",
        },
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["status"] == "completed"
    assert body["human_review"]["status"] == "completed"
    assert body["human_review"]["decision"] == decision
    assert body["human_review"]["reason"] == (
        "Resource evidence checked by human reviewer."
    )

    snapshots = read_jsonl(history)
    assert len(snapshots) == 2
    assert snapshots[-1]["status"] == "completed"
    assert snapshots[-1]["human_review"]["decision"] == decision

    events = [row["event"] for row in read_jsonl(audit)]

    assert events == [
        "started",
        "planner_completed",
        "worker_completed",
        "reviewer_completed",
        "human_review_pending",
        "human_decision",
    ]

    assert read_jsonl(audit)[-1]["human_decision"] == decision
    assert calls == ["planner", "worker", "reviewer"]


@pytest.mark.parametrize(
    "change",
    ["wrong_feature", "missing_request", "invalid_evidence"],
)
def test_resource_workflow_rejects_invalid_input(setup, change):
    client, calls, history, audit = setup

    body = payload()

    if change == "wrong_feature":
        body["feature"] = "course_management"
    elif change == "missing_request":
        body["user_request"] = ""
    else:
        body["evidence"] = {"resource_id": 1}

    response = client.post("/workflow/resource", json=body)

    assert response.status_code == 400
    assert calls == []
    assert not history.exists()
    assert not audit.exists()


def test_resource_rejects_invalid_human_decision(setup):
    client, _, history, audit = setup

    start = client.post("/workflow/resource", json=payload())
    workflow_id = start.get_json()["workflow_id"]

    response = client.post(
        f"/workflow/{workflow_id}/decision",
        json={"decision": "Auto Approve"},
    )

    assert response.status_code == 400

    snapshots = read_jsonl(history)
    assert snapshots[-1]["status"] == "pending_human_review"

    events = [row["event"] for row in read_jsonl(audit)]
    assert "human_decision" not in events


def test_resource_prevents_duplicate_human_decision(setup):
    client, _, history, audit = setup

    start = client.post("/workflow/resource", json=payload())
    workflow_id = start.get_json()["workflow_id"]

    first = client.post(
        f"/workflow/{workflow_id}/decision",
        json={"decision": "Accept", "reason": "Verified"},
    )

    second = client.post(
        f"/workflow/{workflow_id}/decision",
        json={"decision": "Reject", "reason": "Changed"},
    )

    assert first.status_code == 200
    assert second.status_code == 409

    snapshots = read_jsonl(history)
    assert snapshots[-1]["human_review"]["decision"] == "Accept"

    events = [row["event"] for row in read_jsonl(audit)]
    assert events.count("human_decision") == 1
