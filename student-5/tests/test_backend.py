import os
import json
import pytest

from agent.agent import (
    choose_action,
    observe_result,
    adapt_action,
    create_pending_approval,
    run_career_agent,
)


def test_choose_action_resume():
    result = choose_action(
        "Can you improve my resume?"
    )

    assert result == "analyse_job"


def test_choose_action_cv():
    result = choose_action(
        "Can you improve my CV?"
    )

    assert result == "analyse_job"


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


def test_create_pending_approval():
    observation = {
        "success": True,
        "needs_adaptation": False,
        "reason": "Enough information"
    }

    result = create_pending_approval(
        "Python is required.",
        "requirements",
        "requirements",
        observation
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

    result = create_pending_approval(
        "The job requires Python.",
        "analyse_job",
        "requirements",
        observation
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
