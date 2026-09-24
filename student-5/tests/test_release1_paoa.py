from unittest.mock import patch

JOB = {
"id": 11,
"title": "Software Engineer",
"company": "Test Company",
"location": "Sydney",
"industry": "Technology",
"job_type": "Full-time",
"salary": "Not provided",
"description": (
"Build and maintain software applications."
),
"requirements": (
"Python, SQL and software development experience."
),
"application_url": "https://example.com/apply",
}

def test_plan_resume_question():
    from agent import choose_action

    action = choose_action(
        "How can I improve my resume for this job?"
    )

    assert action == "analyse_job"


def test_plan_requirements_question():
    from agent import choose_action

    action = choose_action(
        "What qualifications and skills are required?"
    )

    assert action == "requirements"


def test_plan_interview_question():
    from agent import choose_action

    action = choose_action(
        "How should I prepare for the interview?"
    )

    assert action == "career_rag"


def test_plan_default_question():
    from agent import choose_action

    action = choose_action(
        "Tell me about this job."
    )

    assert action == "job_information"


def test_observe_successful_rag():
    from agent import observe_result

    rag_result = {
        "confidence": "high",
        "context": "Resume guidance...",
        "sources": [
            "resume_guidance.txt"
        ],
        "results": [
            {
                "source": "resume_guidance.txt",
                "text": "Resume guidance.",
                "chunk": 0,
            }
        ],
    }

    observation = observe_result(
        "career_rag",
        rag_result,
        "How should I prepare my resume?",
    )

    assert observation["success"] is True
    assert observation["needs_adaptation"] is False
    assert observation["rag"]["confidence"] == "high"
    assert (
        "resume_guidance.txt"
        in observation["rag"]["sources"]
    )

def test_observe_empty_rag():
    from agent import observe_result

    rag_result = {
        "confidence": "low",
        "context": "",
        "sources": [],
        "results": [],
    }

    observation = observe_result(
        "career_rag",
        rag_result,
        "How should I prepare my resume?",
    )

    assert observation["success"] is False
    assert observation["needs_adaptation"] is True

def test_adapt_rag_failure():
    from agent import adapt_action

    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "No relevant career knowledge.",
    }

    action = adapt_action(
        "career_rag",
        observation,
        "How should I prepare my resume?",
    )

    assert action == "job_information"


def test_adapt_analysis_failure():
    from agent import adapt_action

    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "Analysis unavailable.",
    }

    action = adapt_action(
        "analyse_job",
        observation,
        "Analyse this job for ATS keywords.",
    )

    assert action == "requirements"


def test_adapt_requirements_failure():
    from agent import adapt_action

    observation = {
        "success": False,
        "needs_adaptation": True,
        "reason": "Requirements unavailable.",
    }

    action = adapt_action(
        "requirements",
        observation,
        "What are the requirements?",
    )

    assert action == "job_information"


def test_generate_response():
    from agent import generate_response

    with patch(
        "agent.load_prompt",
        return_value="generated prompt",
    ) as mock_prompt, patch(
        "agent.ask_smart",
        return_value="Final career response.",
    ) as mock_ai:

        result = generate_response(
            "How should I prepare?",
            JOB,
            "career_rag",
            {
                "confidence": "high",
                "sources": ["resume_guidance.txt"],
                "results": [],
            },
            {
                "success": True,
                "needs_adaptation": False,
                "reason": "Relevant knowledge retrieved.",
            },
        )

    assert result == "Final career response."

    mock_prompt.assert_called_once()

    mock_ai.assert_called_once_with(
        "generated prompt"
    )


def test_full_paoa_successful_rag_path():
    """
    PLAN:
    career_rag

    ACT:
        retrieve career knowledge

    OBSERVE:
        RAG is adequate

    ADAPT:
        no adaptation

    RESPONSE:
        generate AI response

    HUMAN REVIEW:
        awaiting_approval
    """

    from agent import run_career_agent

    rag_result = {
        "confidence": "high",
        "context": (
            "A resume should present information "
            "relevant to the position."
        ),
        "sources": [
            "resume_guidance.txt",
            "ats_guidance.txt",
        ],
        "results": [
            {
                "source": "resume_guidance.txt",
                "chunk": 0,
                "text": (
                    "A resume should present relevant "
                    "information."
                ),
                "distance": 0.47,
            }
        ],
    }

    with patch(
        "agent.get_career_rag_tool",
        return_value=rag_result,
    ) as mock_rag, patch(
        "agent.ask_smart",
        return_value=(
            "Tailor your resume to the selected job."
        ),
    ) as mock_ai:

        result = run_career_agent(
            JOB,
            "How should I prepare for the interview?"
        )

    mock_rag.assert_called_once()
    mock_ai.assert_called_once()

    assert result["success"] is True
    assert result["status"] == "awaiting_approval"
    assert result["planned_action"] == "career_rag"
    assert result["action"] == "career_rag"
    assert result["adapted"] is False
    assert result["requires_human_approval"] is True

    assert result["rag"]["confidence"] == "high"

    assert (
        "resume_guidance.txt"
        in result["rag"]["sources"]
    )


def test_full_paoa_rag_adaptation():
    """
    PLAN:
    career_rag

    ACT:
        RAG returns no results

    OBSERVE:
        inadequate

    ADAPT:
        job_information

    SECOND ACT:
        selected job information

    RESPONSE:
        AI response

    HUMAN REVIEW:
        awaiting approval
    """

    from agent import run_career_agent

    empty_rag = {
        "confidence": "low",
        "context": "",
        "sources": [],
        "results": [],
    }

    job_result = {
        "success": True,
        "job": JOB,
    }

    with patch(
        "agent.get_career_rag_tool",
        return_value=empty_rag,
    ) as mock_rag, patch(
        "agent.get_job_tool",
        return_value=job_result,
    ) as mock_job, patch(
        "agent.ask_smart",
        return_value="Job information response.",
    ):

        result = run_career_agent(
            JOB,
            "How should I prepare for this career?"
        )

    mock_rag.assert_called_once()

    mock_job.assert_called_once_with(
        JOB["id"]
    )

    assert result["success"] is True
    assert result["planned_action"] == "career_rag"
    assert result["action"] == "job_information"
    assert result["adapted"] is True
    assert result["requires_human_approval"] is True