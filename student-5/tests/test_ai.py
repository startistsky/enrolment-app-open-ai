import json

import pytest

from agent.ai_service import (
    extract_json,
    load_prompt,
    check_ollama,
    analyse_job,
)


def test_extract_json_direct():
    text = '{"skills": ["Python"], "summary": "Backend developer"}'

    result = extract_json(text)

    assert result["skills"] == ["Python"]
    assert result["summary"] == "Backend developer"


def test_extract_json_markdown():
    text = """```json
{
    "skills": ["Python", "SQL"],
    "qualifications": [],
    "experience": [],
    "ats_keywords": ["Python", "SQL"],
    "summary": "Backend developer"
}
```"""

    result = extract_json(text)

    assert result["skills"] == ["Python", "SQL"]
    assert result["ats_keywords"] == ["Python", "SQL"]


def test_extract_json_with_extra_text():
    text = """
Here is the analysis:

{
    "skills": ["Python"],
    "qualifications": [],
    "experience": [],
    "ats_keywords": ["Python"],
    "summary": "Python developer"
}

End.
"""

    result = extract_json(text)

    assert result["skills"] == ["Python"]


def test_extract_json_invalid():
    result = extract_json("This is not JSON")

    assert result == {}


def test_extract_json_empty():
    assert extract_json("") == {}
    assert extract_json(None) == {}


def test_load_analyse_job_prompt():
    prompt = load_prompt(
        "analyse_job",
        description="Python backend developer",
        requirements="Python, SQL and REST API"
    )

    assert "Python backend developer" in prompt
    assert "Python, SQL and REST API" in prompt


def test_load_analyse_job_prompt_contains_json():
    prompt = load_prompt(
        "analyse_job",
        description="Python developer",
        requirements="Python"
    )

    assert '"skills"' in prompt
    assert '"qualifications"' in prompt
    assert '"experience"' in prompt
    assert '"ats_keywords"' in prompt
    assert '"summary"' in prompt


def test_missing_prompt():
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")


# def test_check_ollama():
#     result = check_ollama()

#     assert result["available"] is True
#     assert result["success"] is True
#     assert len(result["models"]) > 0


def test_analyse_job(monkeypatch):
    fake_response = json.dumps({
        "skills": ["Python", "SQL", "REST API"],
        "qualifications": [],
        "experience": ["Backend development"],
        "ats_keywords": [
            "Python",
            "SQL",
            "REST API"
        ],
        "summary": (
            "Python backend developer "
            "with SQL and REST API experience."
        )
    })

    monkeypatch.setattr(
        "agent.ai_service.ask_fast",
        lambda prompt: fake_response
    )

    result = analyse_job(
        "Python backend developer",
        "Python, SQL, REST API experience"
    )

    assert result["skills"] == [
        "Python",
        "SQL",
        "REST API"
    ]

    assert result["qualifications"] == []

    assert result["experience"] == [
        "Backend development"
    ]

    assert result["ats_keywords"] == [
        "Python",
        "SQL",
        "REST API"
    ]

    assert "Python backend developer" in result["summary"]


def test_analyse_job_invalid_ai_response(monkeypatch):
    monkeypatch.setattr(
        "agent.ai_service.ask_fast",
        lambda prompt: "This is not JSON"
    )

    result = analyse_job(
        "Python developer",
        "Python experience"
    )

    assert result["skills"] == []
    assert result["qualifications"] == []
    assert result["experience"] == []
    assert result["ats_keywords"] == []
    assert result["summary"] == ""


def test_analyse_job_non_list_values(monkeypatch):
    fake_response = json.dumps({
        "skills": "Python",
        "qualifications": "Bachelor degree",
        "experience": "Backend development",
        "ats_keywords": "Python",
        "summary": "Developer"
    })

    monkeypatch.setattr(
        "agent.ai_service.ask_fast",
        lambda prompt: fake_response
    )

    result = analyse_job(
        "Python developer",
        "Python"
    )

    assert result["skills"] == ["Python"]
    assert result["qualifications"] == [
        "Bachelor degree"
    ]
    assert result["experience"] == [
        "Backend development"
    ]
    assert result["ats_keywords"] == ["Python"]
