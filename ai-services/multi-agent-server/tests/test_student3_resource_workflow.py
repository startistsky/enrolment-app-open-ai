"""End-to-end API tests for Student 3 Resource Management workflow."""

import importlib.util
import json
import sys
from pathlib import Path

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
