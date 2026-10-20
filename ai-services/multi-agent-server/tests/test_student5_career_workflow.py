# end-to-end API tests 

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]

if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

spec = importlib.util.spec_from_file_location(
    "student5_multi_agent_app",
    SERVER / "app.py",
)

server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

from agents import (  # noqa: E402
    career_planner_agent,
    career_worker_agent,
    career_reviewer_agent,
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """Mock career agents and create an isolated test application."""

    calls = []

    outputs = {
        "planner": {
            "plan": (
                "Analyse the selected job's responsibilities, "
                "required skills, qualifications, experience, "
                "education, ATS keywords, and missing information."
            ),
            "evidence_required": ["selected_job"],
        },
        "worker": {
            "result": (
                "JOB ANALYSIS\n\n"
                "Job title: Python Developer\n"
                "Company: Example Company\n"
                "Location: Sydney\n"
                "Industry: Technology\n"
                "Employment type: Full-time\n\n"
                "Responsibilities:\n"
                "- Develop and maintain Python applications.\n\n"
                "Required skills:\n"
                "- Python programming.\n"
                "- Problem-solving skills.\n\n"
                "Qualifications and education:\n"
                "- The requirements mention Python programming "
                "and problem-solving skills.\n"
                "- No specific degree or education requirement "
                "is stated in the supplied job record.\n\n"
                "Experience:\n"
                "- A minimum duration of experience is not stated.\n\n"
                "ATS keywords:\n"
                "- Python\n"
                "- Python programming\n"
                "- Problem-solving\n"
                "- Software development\n\n"
                "Ideal candidate summary:\n"
                "The job description indicates a candidate who can "
                "develop and maintain Python applications and apply "
                "problem-solving skills. Specific education and "
                "experience requirements cannot be confirmed from "
                "the supplied record.\n\n"
                "Candidate suitability:\n"
                "Cannot be assessed because no candidate profile "
                "is available."
            ),
            "evidence_used": ["selected_job"],
            "missing_information": [
                "The minimum required years of experience are not specified.",
                "A specific education or degree requirement is not stated.",
                "Salary information is not available.",
                "No candidate profile is available, so personal suitability "
                "cannot be assessed.",
            ],
        },
        "reviewer": {
            "risk": (
                "The job analysis is based on the supplied job record. "
                "Candidate suitability cannot be assessed without "
                "candidate information."
            ),
            "unsupported_claims": [],
            "correction": "",
            "recommendation": (
                "The job analysis is adequate and evidence-based. "
                "Proceed to human review."
            ),
        },
    }

    def stage(role):
        def run(*args):
            calls.append(role)
            return outputs[role].copy()

        return run

    monkeypatch.setattr(
        career_planner_agent, "run", stage("planner")
    )
    monkeypatch.setattr(
        career_worker_agent, "run", stage("worker")
    )
    monkeypatch.setattr(
        career_reviewer_agent, "run", stage("reviewer")
    )

    history = tmp_path / "history.jsonl"
    audit = tmp_path / "audit.jsonl"

    app = server.create_app(history, audit)
    app.config.update(TESTING=True)

    return app.test_client(), calls, history, audit


def payload():
    """Provide a job record without a candidate profile."""

    return {
        "user_request": (
            "Analyse the selected job comprehensively. Identify "
            "responsibilities, required skills, qualifications, "
            "education, experience, ATS keywords, and the ideal "
            "candidate. State missing information without inventing "
            "requirements."
        ),
        "feature": "career_management",
        "selected_job": {
            "id": 1,
            "title": "Python Developer",
            "company": "Example Company",
            "location": "Sydney",
            "industry": "Technology",
            "job_type": "Full-time",
            "description": (
                "Develop and maintain Python applications."
            ),
            "requirements": (
                "Python programming and problem-solving skills."
            ),
        },
        # Intentionally no candidate profile.
    }


def read_jsonl(path):
    if not path.exists():
        return []

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_career_workflow_order_and_pending_review(setup):
    client, calls, history, audit = setup

    response = client.post("/workflow/career", json=payload())

    assert response.status_code == 200
    body = response.get_json()

    assert calls == ["planner", "worker", "reviewer"]
    assert body["feature"] == "career_management"
    assert body["status"] == "pending_human_review"

    assert body["human_review"]["required"] is True
    assert body["human_review"]["status"] == "pending"

    assert body["planner_status"] == "completed"
    assert body["worker_status"] == "completed"
    assert body["reviewer_status"] == "completed"

    assert body["planner_result"]["evidence_required"] == [
        "selected_job"
    ]

    worker = body["worker_result"]

    assert worker["evidence_used"] == ["selected_job"]
    assert "Responsibilities:" in worker["result"]
    assert "Required skills:" in worker["result"]
    assert "Qualifications and education:" in worker["result"]
    assert "Experience:" in worker["result"]
    assert "ATS keywords:" in worker["result"]
    assert "Ideal candidate summary:" in worker["result"]

    # The worker must not claim to know the candidate's suitability.
    assert "Cannot be assessed" in worker["result"]
    assert any(
        "no candidate profile" in item.lower()
        for item in worker["missing_information"]
    )

    assert body["reviewer_result"]["unsupported_claims"] == []

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
    assert snapshots[0]["feature"] == "career_management"


@pytest.mark.parametrize(
    "decision",
    ["Accept", "Partially Accept", "Reject"],
)
def test_career_human_decision_and_audit(setup, decision):
    client, calls, history, audit = setup

    start = client.post("/workflow/career", json=payload())

    assert start.status_code == 200
    workflow_id = start.get_json()["workflow_id"]

    response = client.post(
        f"/workflow/{workflow_id}/decision",
        json={
            "decision": decision,
            "reason": "Reviewed the job analysis and reviewer findings.",
        },
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["status"] == "completed"
    assert body["human_review"]["status"] == "completed"
    assert body["human_review"]["decision"] == decision
    assert body["human_review"]["reason"] == (
        "Reviewed the job analysis and reviewer findings."
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
    [
        "wrong_feature",
        "missing_request",
        "invalid_selected_job",
        "missing_selected_job",
        "invalid_career_details",
    ],
)
def test_career_workflow_rejects_invalid_input(setup, change):
    client, calls, history, audit = setup

    body = payload()

    if change == "wrong_feature":
        body["feature"] = "course_management"
    elif change == "missing_request":
        body["user_request"] = ""
    elif change == "invalid_selected_job":
        body["selected_job"] = "invalid"
    elif change == "missing_selected_job":
        body.pop("selected_job")
    elif change == "invalid_career_details":
        body["career_details"] = "invalid"

    response = client.post("/workflow/career", json=body)

    assert response.status_code == 400
    assert calls == []
    assert read_jsonl(history) == []
    assert read_jsonl(audit) == []


def test_career_rejects_invalid_human_decision(setup):
    client, _, history, audit = setup

    start = client.post("/workflow/career", json=payload())

    assert start.status_code == 200
    workflow_id = start.get_json()["workflow_id"]

    response = client.post(
        f"/workflow/{workflow_id}/decision",
        json={"decision": "Auto Approve", "reason": "Test"},
    )

    assert response.status_code == 400

    snapshots = read_jsonl(history)

    assert snapshots[-1]["status"] == "pending_human_review"

    events = [row["event"] for row in read_jsonl(audit)]

    assert "human_decision" not in events


def test_career_prevents_duplicate_human_decision(setup):
    client, _, history, audit = setup

    start = client.post("/workflow/career", json=payload())

    assert start.status_code == 200
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


def test_career_workflow_status_endpoint(setup):
    client, _, _, _ = setup

    start = client.post("/workflow/career", json=payload())

    assert start.status_code == 200
    workflow_id = start.get_json()["workflow_id"]

    response = client.get("/workflow/status")

    assert response.status_code == 200

    workflows = response.get_json()["workflows"]

    assert {
        "workflow_id": workflow_id,
        "status": "pending_human_review",
        "human_review_status": "pending",
    } in workflows
