import json
import os
import requests
from pathlib import Path

# Ollama Configuration
# When running local  - change to "http://localhost:11434"
# When running Docker Compose - change to "http://ollama:11434"  

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://ollama:11434"  
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

OLLAMA_SMART_MODEL = os.getenv(
    "OLLAMA_SMART_MODEL",
    OLLAMA_MODEL
)

OLLAMA_TIMEOUT = int(
    os.getenv(
        "OLLAMA_TIMEOUT",
        "120"
    )
)

PROMPT_PATH = (Path(__file__).resolve().parent.parent / "prompt")


# Load prompt 
def load_prompt(name, **values):
    prompt_file = PROMPT_PATH / f"{name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt not found: {prompt_file}"
        )

    prompt = prompt_file.read_text(
        encoding="utf-8"
    )

    for key, value in values.items():

        placeholder = f"<<<{key.upper()}>>>"

        prompt = prompt.replace(
            placeholder,
            str(value)
        )
    return prompt

# JSON helper
def extract_json(text):
    """
    Extract a JSON object from an AI response.

    Handles:
    - Normal JSON
    - JSON inside ```json ... ```
    - JSON surrounded by other text
    """

    if isinstance(text, dict):
        return text

    if not text:
        return {}

    text = str(text).strip()

    # Remove markdown code fences
    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Try direct JSON
    try:

        return json.loads(text)

    except json.JSONDecodeError:

        pass

    # Try to find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:

            return json.loads(
                text[start:end + 1]
            )

        except json.JSONDecodeError:

            pass

    return {}

# Ollama Request
def ask_ollama(prompt,model=None):
    """
    Send a prompt to Ollama and return
    the generated text response.
    """

    selected_model = (
        model
        or OLLAMA_MODEL
    )

    try:

        response = requests.post(

            f"{OLLAMA_URL}/api/generate",

            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": False
            },

            timeout=OLLAMA_TIMEOUT

        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "response",
            ""
        )

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Could not connect to Ollama. "
            "Make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "The Ollama request timed out."
        )

    except requests.exceptions.RequestException as error:

        raise RuntimeError(
            f"Ollama request failed: {error}"
        )

# AI Modes
# fast AI
def ask_fast(prompt):
    """
    General-purpose AI request.
    """

    return ask_ollama(
        prompt,
        OLLAMA_MODEL
    )

# smart AI
def ask_smart(prompt):
    """
    More deliberate AI request.

    Uses OLLAMA_SMART_MODEL if configured.
    """

    return ask_ollama(
        prompt,
        OLLAMA_SMART_MODEL
    )

# Ollama Status
def check_ollama():
    """
    Check whether Ollama is running and
    return the available models.
    """

    try:

        response = requests.get(

            f"{OLLAMA_URL}/api/tags",

            timeout=5

        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )

        model_names = [

            model.get(
                "name",
                ""
            )

            for model in models

        ]

        return {

            "success": True,

            "available": True,

            "url": OLLAMA_URL,

            "model": OLLAMA_MODEL,

            "models": model_names

        }

    except requests.exceptions.ConnectionError:

        return {

            "success": False,

            "available": False,

            "url": OLLAMA_URL,

            "model": OLLAMA_MODEL,

            "error":
                "Could not connect to Ollama. "
                "Make sure Ollama is running."

        }

    except Exception as error:

        return {

            "success": False,

            "available": False,

            "url": OLLAMA_URL,

            "model": OLLAMA_MODEL,

            "error": str(error)

        }

# Job Analysis 
def analyse_job(description, requirements):

    prompt = load_prompt(
        "analyse_job",
        description=description,
        requirements=requirements
    )

    response = ask_fast(prompt)

    result = extract_json(response)

    skills = result.get("skills", [])
    qualifications = result.get("qualifications", [])
    experience = result.get("experience", [])
    ats_keywords = result.get("ats_keywords", [])
    summary = result.get("summary", "")

    if not isinstance(skills, list):
        skills = [str(skills)]

    if not isinstance(qualifications, list):
        qualifications = [str(qualifications)]

    if not isinstance(experience, list):
        experience = [str(experience)]

    if not isinstance(ats_keywords, list):
        ats_keywords = [str(ats_keywords)]

    return {
        "skills": skills,
        "qualifications": qualifications,
        "experience": experience,
        "ats_keywords": ats_keywords,
        "summary": str(summary)
    }


# Career agent chat
def career_chat(message, job=None):
    """
    Provide AI career and application guidance for a selected job.
    """

    if not job:
        return (
            "Please select a job before "
            "asking the Career Agent for support."
        )

    prompt = load_prompt(
        "career_chat",
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        industry=job.get("industry", ""),
        job_type=job.get("job_type", ""),
        salary=job.get("salary", ""),
        description=job.get("description", ""),
        requirements=job.get("requirements", ""),
        application_url=job.get("application_url", ""),
        message=message
    )
    return ask_smart(prompt)

# eevaluate result for adapt 
def evaluate_agent_result(message, tool_result):
    """
    Evaluate whether the tool result is sufficient to answer the user's question.
    """

    prompt = load_prompt(
        "evaluate_agent_result",
        message=message,
        tool_result=tool_result
    )

    response = ask_fast(prompt)

    try:
        result = json.loads(response)
        return {
            "adequate": bool(
                result.get("adequate", False)
            ),

            "reason": str(
                result.get("reason", "")
            )
        }

    except Exception:
        return {
            "adequate": False,
            "reason": ("Could not evaluate tool result.")
        }

