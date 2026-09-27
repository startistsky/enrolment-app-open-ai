import sys
from pathlib import Path

import pytest
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]

AGENT_DIR = PROJECT_ROOT / "agent"
BACKEND_DIR = PROJECT_ROOT / "backend"

# make the student 5 directories importable 
for path in (
    PROJECT_ROOT,
    AGENT_DIR,
    BACKEND_DIR,
):
    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from agent.agent import (
    choose_action,
    observe_result,
    adapt_action,
    create_pending_approval,
    run_career_agent,
)

# Tests
def test_choose_action_ats():
    assert choose_action("What ATS keywords should I use?") == "analyse_job"

def test_choose_action_requirements():
    assert choose_action("What are the job requirements?") == "requirements"

def test_choose_action_skills():
    assert choose_action("What skills do I need?") == "requirements"

def test_choose_action_qualification():
    assert choose_action("What qualification do I need?") == "requirements"

def test_choose_action_experience():
    assert choose_action("What experience is required?") == "requirements"


def test_choose_action_general_job_information():
    assert choose_action("Tell me about this job") == "job_information"


def test_observe_none_result():
    result = observe_result(
        "requirements",
        None,
        "What skills are required?"
    )

    assert result["success"] is False
    assert result["needs_adaptation"] is True


def test_adapt_analysis_to_requirements():
    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "Not enough information"
    }

    assert adapt_action(
        "analyse_job",
        observation,
        "What ATS keywords should I use?"
    ) == "requirements"


def test_adapt_requirements_to_job_information():
    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "Not enough information"
    }

    assert adapt_action(
        "requirements",
        observation,
        "What skills are required?"
    ) == "job_information"


def test_no_adaptation():
    observation = {
        "success": True,
        "needs_adaptation": False,
        "reason": "Enough information"
    }

    assert adapt_action(
        "requirements",
        observation,
        "What skills are required?"
    ) == "requirements"


def test_create_pending_approval():
    observation = {
        "success": True,
        "needs_adaptation": False,
        "reason": "Enough information"
    }

    tool_result = {
        "success": True
    }

    result = create_pending_approval(
        "Python is required.",
        "requirements",
        "requirements",
        observation,
        tool_result
    )

    assert result["success"] is True
    assert result["status"] == "awaiting_approval"
    assert result["response"] == "Python is required."
    assert result["planned_action"] == "requirements"
    assert result["action"] == "requirements"
    assert result["adapted"] is False
    assert result["requires_human_approval"] is True


def test_create_pending_approval_after_adaptation():
    observation = {
        "success": True,
        "needs_adaptation": False,
        "reason": "Enough information"
    }

    tool_result = {
        "success": True
    }

    result = create_pending_approval(
        "The job requires Python.",
        "analyse_job",
        "requirements",
        observation,
        tool_result
    )

    assert result["success"] is True
    assert result["adapted"] is True
    assert result["planned_action"] == "analyse_job"
    assert result["action"] == "requirements"


def test_run_career_agent_missing_job():
    result = run_career_agent(
        None,
        "What skills are required?"
    )

    assert result["success"] is False
    assert result["error"] == "Job not found."


def test_run_career_agent_missing_message():
    job = {
        "id": 1,
        "title": "Python Developer"
    }

    result = run_career_agent(job, "")

    assert result["success"] is False
    assert result["error"] == "Message is required."


def test_run_career_agent_whitespace_message():
    job = {
        "id": 1,
        "title": "Python Developer"
    }

    result = run_career_agent(job, "   ")

    assert result["success"] is False
    assert result["error"] == "Message is required."
