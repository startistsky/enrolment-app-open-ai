import sys
from pathlib import Path
import os
import json
import pytest
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BACKEND_DIR = PROJECT_ROOT / "backend"
MODEL_DIR = BACKEND_DIR / "model"
CRUD_DIR = BACKEND_DIR / "crud"

# make path importable 
for path in (
    PROJECT_ROOT,
    BACKEND_DIR,
    MODEL_DIR,
    CRUD_DIR,
):
    path_str = str(path)

    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# import tools 
from agent.agent import (
    choose_action,
    observe_result,
    adapt_action,
    create_pending_approval,
    run_career_agent,
)

# Tests
def test_choose_action_ats():
    result = choose_action(
        "What ATS keywords should I use?"
    )
    assert result == "analyse_job"


def test_choose_action_requirements():
    result = choose_action(
        "What are the job requirements?"
    )
    assert result == "requirements"


def test_choose_action_skills():
    result = choose_action(
        "What skills do I need?"
    )
    assert result == "requirements"


def test_choose_action_qualification():
    result = choose_action(
        "What qualification do I need?"
    )
    assert result == "requirements"


def test_choose_action_experience():
    result = choose_action(
        "What experience is required?"
    )
    assert result == "requirements"


def test_choose_action_general_job_information():
    result = choose_action(
        "Tell me about this job"
    )
    assert result == "job_information"


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

    result = adapt_action(
        "analyse_job",
        observation,
        "What ATS keywords should I use?"
    )
    assert result == "requirements"


def test_adapt_requirements_to_job_information():
    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "Not enough information"
    }

    result = adapt_action(
        "requirements",
        observation,
        "What skills are required?"
    )
    assert result == "job_information"


def test_no_adaptation():
    observation = {
        "success": True,
        "needs_adaptation": False,
        "reason": "Enough information"
    }

    result = adapt_action(
        "requirements",
        observation,
        "What skills are required?"
    )
    assert result == "requirements"

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

    result = run_career_agent(
        job,
        ""
    )

    assert result["success"] is False
    assert result["error"] == "Message is required."


def test_run_career_agent_whitespace_message():
    job = {
        "id": 1,
        "title": "Python Developer"
    }

    result = run_career_agent(
        job,
        "   "
    )

    assert result["success"] is False
    assert result["error"] == "Message is required."
