# backend/agent.py

import json
import os

from ai_service import ask_fast, ask_smart


MAX_JOBS = int(os.getenv("AGENT_MAX_JOBS", "10"))
MIN_MATCH_SCORE = int(os.getenv("AGENT_MIN_MATCH_SCORE", "50"))


def safe_json_loads(value, default=None):
    """
    Safely convert an AI response into Python JSON.
    """
    if default is None:
        default = {}

    if isinstance(value, dict):
        return value

    if not value:
        return default

    text = str(value).strip()

    # Remove markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract the JSON object from surrounding text
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return default


def normalise_score(value):
    """
    Convert an AI score into a safe integer between 0 and 100.
    """
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = 0

    return max(0, min(100, score))


def run_career_agent(profile, jobs):
    """
    Match a student's career profile against available jobs.
    """

    # --------------------------------------------------------
    # Limit jobs
    # --------------------------------------------------------

    jobs = list(jobs or [])[:MAX_JOBS]

    if not jobs:
        return {
            "success": True,
            "message": "No jobs available to analyse.",
            "matches": [],
            "iterations": 0,
            "skill_gaps": [],
            "next_steps": []
        }

    # --------------------------------------------------------
    # STEP 1
    # Extract useful profile information
    # --------------------------------------------------------

    profile_prompt = f"""
You are a career profile extraction assistant.

Extract the important career matching information from this
student profile.

STUDENT PROFILE:
{json.dumps(profile, indent=2, default=str)}

Return ONLY valid JSON in this exact structure:

{{
    "skills": [],
    "locations": [],
    "industries": [],
    "job_types": [],
    "career_goals": [],
    "education": "",
    "experience": ""
}}

Do not include markdown.
Do not include explanations.
"""

    profile_response = ask_fast(profile_prompt)

    extracted_profile = safe_json_loads(
        profile_response,
        {
            "skills": [],
            "locations": [],
            "industries": [],
            "job_types": [],
            "career_goals": [],
            "education": "",
            "experience": ""
        }
    )

    # --------------------------------------------------------
    # STEP 2
    # Match jobs
    # --------------------------------------------------------

    matching_prompt = f"""
You are a job matching engine.

STUDENT PROFILE:
{json.dumps(extracted_profile, indent=2, default=str)}

JOBS:
{json.dumps(jobs, indent=2, default=str)}

For EVERY job, calculate a match score from 0 to 100.

Consider:

1. Skills
2. Location
3. Industry
4. Job type
5. Career goals
6. Education
7. Experience
8. Qualifications

Scoring guidance:

90-100 = Excellent match
75-89 = Strong match
60-74 = Good match
50-59 = Possible match
0-49 = Weak match

Return ONLY valid JSON:

{{
    "matches": [
        {{
            "job_id": 1,
            "score": 85,
            "reason": "Strong match because the student has Python and SQL skills and wants a software engineering career.",
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["React"]
        }}
    ]
}}

Every job must have a numeric score.

Do not include markdown.
Do not include explanations outside the JSON.
"""

    matching_response = ask_fast(matching_prompt)

    parsed = safe_json_loads(
        matching_response,
        {"matches": []}
    )

    matches = parsed.get("matches", [])

    if not isinstance(matches, list):
        matches = []

    # --------------------------------------------------------
    # STEP 3
    # Clean matches
    # --------------------------------------------------------

    cleaned_matches = []

    jobs_by_id = {}

    for job in jobs:
        try:
            jobs_by_id[int(job["id"])] = job
        except (KeyError, TypeError, ValueError):
            continue

    for match in matches:

        if not isinstance(match, dict):
            continue

        job_id = match.get("job_id")

        try:
            job_id = int(job_id)
        except (TypeError, ValueError):
            continue

        score = normalise_score(
            match.get("score", 0)
        )

        if score < MIN_MATCH_SCORE:
            continue

        job = jobs_by_id.get(job_id)

        if not job:
            continue

        matched_skills = match.get(
            "matched_skills",
            []
        )

        missing_skills = match.get(
            "missing_skills",
            []
        )

        if not isinstance(matched_skills, list):
            matched_skills = [str(matched_skills)]

        if not isinstance(missing_skills, list):
            missing_skills = [str(missing_skills)]

        cleaned_matches.append({
            "job_id": job_id,
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "industry": job.get("industry", ""),
            "job_type": job.get("job_type", ""),
            "score": score,
            "reason": str(
                match.get(
                    "reason",
                    "This job matches your profile."
                )
            ),
            "matched_skills": [
                str(item)
                for item in matched_skills
            ],
            "missing_skills": [
                str(item)
                for item in missing_skills
            ]
        })

    # Highest scores first
    cleaned_matches.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # --------------------------------------------------------
    # STEP 4
    # Senior review
    # --------------------------------------------------------

    if cleaned_matches:

        review_prompt = f"""
You are the senior career advisor.

STUDENT PROFILE:
{json.dumps(profile, indent=2, default=str)}

CANDIDATE JOB MATCHES:
{json.dumps(cleaned_matches, indent=2, default=str)}

Review the recommendations.

Identify:

1. The best opportunities
2. Why they match
3. Skill gaps
4. What the student should do next

Keep recommendations realistic.

Return ONLY valid JSON:

{{
    "matches": [],
    "summary": "",
    "skill_gaps": [],
    "next_steps": []
}}

The matches should preserve the job_id, title, company,
location, score and reason.

Do not include markdown.
"""

        review_response = ask_smart(
            review_prompt
        )

        final_result = safe_json_loads(
            review_response,
            {}
        )

    else:

        final_result = {
            "matches": [],
            "summary": (
                "No strong matches were found. "
                "Try adding more skills, education or "
                "career goals to your profile."
            ),
            "skill_gaps": [],
            "next_steps": [
                "Add more technical or transferable skills.",
                "Add your education or qualifications.",
                "Add your previous experience.",
                "Add clearer career goals."
            ]
        }

    # --------------------------------------------------------
    # STEP 5
    # Ensure response structure
    # --------------------------------------------------------

    final_matches = final_result.get(
        "matches",
        cleaned_matches
    )

    if not isinstance(final_matches, list):
        final_matches = cleaned_matches

    return {
        "success": True,
        "iterations": 2,
        "matches": final_matches,
        "summary": str(
            final_result.get(
                "summary",
                ""
            )
        ),
        "skill_gaps": final_result.get(
            "skill_gaps",
            []
        ),
        "next_steps": final_result.get(
            "next_steps",
            []
        )
    }