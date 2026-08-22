# backend/ai_service.py

import json
import os

import requests


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2"
)

OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "120")
)


# =========================================================
# Helpers
# =========================================================

def extract_json(text):
    """
    Extract JSON from an AI response.

    Handles:
    - normal JSON
    - ```json ... ```
    - JSON surrounded by explanatory text
    """

    if isinstance(text, dict):
        return text

    if not text:
        return {}

    text = str(text).strip()

    # Remove markdown fences
    if text.startswith("```"):
        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # Direct JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:

        try:
            return json.loads(
                text[start:end + 1]
            )
        except json.JSONDecodeError:
            pass

    return {}


def ask_ollama(prompt, model=None):
    """
    Send a prompt to Ollama.
    """

    selected_model = model or OLLAMA_MODEL

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


# =========================================================
# Fast AI
# =========================================================

def ask_fast(prompt):
    """
    Fast/general AI request.
    """

    return ask_ollama(prompt)


# =========================================================
# Smart AI
# =========================================================

def ask_smart(prompt):
    """
    More deliberate AI request.

    Currently uses the same Ollama model as ask_fast,
    but is kept as a separate function so the career agent
    can use different models later.
    """

    model = os.getenv(
        "OLLAMA_SMART_MODEL",
        OLLAMA_MODEL
    )

    return ask_ollama(
        prompt,
        model=model
    )


# =========================================================
# Ollama status
# =========================================================

def check_ollama():
    """
    Check whether Ollama is running.
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
            model.get("name", "")
            for model in models
        ]

        return {
            "success": True,
            "available": True,
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
            "models": model_names
        }

    except Exception as error:

        return {
            "success": False,
            "available": False,
            "url": OLLAMA_URL,
            "model": OLLAMA_MODEL,
            "error": str(error)
        }


# =========================================================
# Job analysis
# =========================================================

def analyse_job(
    description,
    requirements
):

    prompt = f"""
You are an expert recruitment and ATS analyst.

Analyse this job.

JOB DESCRIPTION:
{description}

JOB REQUIREMENTS:
{requirements}

Return ONLY valid JSON.

Use this exact structure:

{{
    "skills": [
        "Python",
        "JavaScript",
        "SQL"
    ],

    "qualifications": [
        "Degree in Computer Science or related field",
        "Strong problem solving skills"
    ],

    "experience": [
        "Web development experience",
        "Experience with React or similar frameworks"
    ],

    "ats_keywords": [
        "Python",
        "JavaScript",
        "React",
        "SQL",
        "Software Engineering",
        "Problem Solving"
    ],

    "summary": "A short summary of what the employer is looking for."
}}

Rules:

- skills = technical and soft skills explicitly or strongly implied
- qualifications = degrees, certifications and educational requirements
- experience = previous work, technical or practical experience required
- ats_keywords = important terms a candidate should include in an ATS-friendly resume
- summary = concise explanation of the job

Do not return markdown.
Do not return headings.
Do not return explanations outside JSON.
"""

    response = ask_fast(prompt)

    result = extract_json(response)

    # Safe defaults
    return {
        "skills": result.get(
            "skills",
            []
        ),

        "qualifications": result.get(
            "qualifications",
            []
        ),

        "experience": result.get(
            "experience",
            []
        ),

        "ats_keywords": result.get(
            "ats_keywords",
            []
        ),

        "summary": result.get(
            "summary",
            ""
        )
    }


# =========================================================
# Career chat
# =========================================================

def career_chat(
    message,
    job=None
):

    job_context = ""

    if job:

        job_context = f"""
CURRENT JOB:

Title: {job.get("title", "")}
Company: {job.get("company", "")}
Location: {job.get("location", "")}
Industry: {job.get("industry", "")}

Description:
{job.get("description", "")}

Requirements:
{job.get("requirements", "")}
"""

    prompt = f"""
You are CareerConnect Career Agent.

Help the student understand careers, jobs,
applications, qualifications and skill gaps.

{job_context}

STUDENT MESSAGE:
{message}

Give a helpful, concise answer.

Do not invent information about the job.
"""

    return ask_fast(prompt)