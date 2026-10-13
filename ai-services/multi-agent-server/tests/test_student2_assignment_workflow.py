import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


SERVER = Path(__file__).resolve().parents[1]
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))
spec = importlib.util.spec_from_file_location("student2_multi_agent_app", SERVER / "app.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

from agents import (  # noqa: E402
    assignment_planner_agent,
    assignment_reviewer_agent,
    assignment_worker_agent,
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    calls = []
    outputs = {
        "planner": {"plan": "Rank active assignments", "evidence_required": ["priority"]},
        "worker": {"answer": "Start assignment 1", "evidence_used": ["1"], "missing_evidence": []},
        "reviewer": {"risk": "low", "unsupported_claims": [], "correction": "", "recommendation": "Review before accepting"},
    }

    def stage(role):
        def run(*args):
            calls.append(role)
            return outputs[role]
        return run

    monkeypatch.setattr(assignment_planner_agent, "run", stage("planner"))
    monkeypatch.setattr(assignment_worker_agent, "run", stage("worker"))
    monkeypatch.setattr(assignment_reviewer_agent, "run", stage("reviewer"))
    app = server.create_app(tmp_path / "history.jsonl", tmp_path / "audit.jsonl")
    app.config.update(TESTING=True)
    return app.test_client(), calls


def payload():
    return {
        "user_request": "What should I do first?",
        "feature": "assignment_management",
        "evidence": [{"assignment_id": 1, "assignment_title": "Release 2"}],
    }


def test_assignment_workflow_order_and_human_review(setup):
    response = setup[0].post("/workflow/assignment", json=payload())
    assert response.status_code == 200
    body = response.get_json()
    assert setup[1] == ["planner", "worker", "reviewer"]
    assert body["feature"] == "assignment_management"
    assert body["status"] == "pending_human_review"
    assert body["human_review"]["status"] == "pending"


def test_assignment_workflow_rejects_invalid_input(setup):
    response = setup[0].post(
        "/workflow/assignment",
        json={**payload(), "feature": "course_management"},
    )
    assert response.status_code == 400
    assert setup[1] == []


def test_assignment_workflow_records_human_decision(setup):
    workflow_id = setup[0].post(
        "/workflow/assignment", json=payload()
    ).get_json()["workflow_id"]
    response = setup[0].post(
        f"/workflow/{workflow_id}/decision",
        json={"decision": "Accept", "reason": "Evidence checked"},
    )
    assert response.status_code == 200
    assert response.get_json()["human_review"]["decision"] == "Accept"
