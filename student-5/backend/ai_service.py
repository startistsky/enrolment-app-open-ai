import json
import os

import requests

# Ollama Configuration
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2"
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
def ask_ollama(
    prompt,
    model=None
):
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
def ask_fast(prompt):
    """
    General-purpose AI request.
    """

    return ask_ollama(
        prompt,
        OLLAMA_MODEL
    )


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
def analyse_job(
    description,
    requirements
):
    """
    Analyse a selected job using AI.

    Returns:

    - skills
    - qualifications
    - experience
    - ATS keywords
    - summary
    """

    prompt = f"""
You are an expert recruitment and ATS analyst.

Analyse the following job.

JOB DESCRIPTION:
{description}

JOB REQUIREMENTS:
{requirements}

Return ONLY valid JSON using this exact structure:

{{
    "skills": [],
    "qualifications": [],
    "experience": [],
    "ats_keywords": [],
    "summary": ""
}}

Rules:

- skills = technical and soft skills required for the job
- qualifications = degrees, certifications and educational requirements
- experience = previous work, technical or practical experience required
- ats_keywords = important terms relevant to an ATS-friendly resume
- summary = concise summary of what the employer is looking for

Only include information supported by the job description
or requirements.

Do not invent requirements.

Do not return markdown.

Do not return headings.

Do not return explanations outside JSON.
"""

    response = ask_fast(
        prompt
    )

    result = extract_json(
        response
    )

    # Validate result
    skills = result.get(
        "skills",
        []
    )

    qualifications = result.get(
        "qualifications",
        []
    )

    experience = result.get(
        "experience",
        []
    )

    ats_keywords = result.get(
        "ats_keywords",
        []
    )

    summary = result.get(
        "summary",
        ""
    )

    # Make sure list fields are actually lists
    if not isinstance(skills, list):
        skills = [str(skills)]

    if not isinstance(qualifications, list):
        qualifications = [
            str(qualifications)
        ]

    if not isinstance(experience, list):
        experience = [
            str(experience)
        ]

    if not isinstance(ats_keywords, list):
        ats_keywords = [
            str(ats_keywords)
        ]

    return {

        "skills": skills,

        "qualifications": qualifications,

        "experience": experience,

        "ats_keywords": ats_keywords,

        "summary": str(summary)

    }

# Career Agent Chat
def career_chat(
    message,
    job=None
):
    """
    Provide AI career and application guidance
    for a selected job.

    The AI only receives the selected job and
    the student's question.
    """

    if not job:

        return (
            "Please select a job before "
            "asking the Career Agent for support."
        )

    # Selected job context
    job_context = f"""
SELECTED JOB

Title:
{job.get("title", "")}

Company:
{job.get("company", "")}

Location:
{job.get("location", "")}

Industry:
{job.get("industry", "")}

Job Type:
{job.get("job_type", "")}

Salary:
{job.get("salary", "")}

Description:
{job.get("description", "")}

Requirements:
{job.get("requirements", "")}

Application URL:
{job.get("application_url", "")}
"""

    # Agent prompt
    prompt = f"""
You are CareerConnect's AI Career and Application Agent.

You are helping a student understand and apply for
the selected job.

{job_context}

STUDENT QUESTION:
{message}

You can help with:

- Understanding the job requirements
- Explaining technical and soft skills
- Explaining qualifications
- Identifying possible skill gaps
- Improving a resume for this job
- Suggesting ATS keywords
- Preparing an application
- Suggesting application next steps
- Preparing for interviews
- Explaining the job description
- Providing general career advice related to this job

Important rules:

1. Base your answer on the selected job.
2. Do not invent information about the job.
3. If the job does not provide enough information,
   clearly say that the information is not available.
4. Do not claim that the student is qualified unless
   enough information about the student is available.
5. Do not invent salary, requirements, qualifications,
   company information or application details.
6. Keep the response concise and practical.
7. Give actionable advice where appropriate.
8. If the student asks something unrelated to the selected
   job, politely explain that you can primarily help with
   this job and its application.

Return a normal text response.
"""

    return ask_smart(
        prompt
    )