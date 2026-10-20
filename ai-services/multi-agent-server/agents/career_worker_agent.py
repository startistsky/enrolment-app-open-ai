from llm_client import generate, ModelError

# worker agent
def run(user_request, evidence, planner_result):
    """Analyse the selected job using supplied job data only."""

    print("CAREER WORKER FILE:", __file__)

    if not isinstance(evidence, dict):
        raise ModelError("Career evidence must be a dictionary")

    job = evidence.get("selected_job")

    if not isinstance(job, dict):
        raise ModelError("Selected job record is missing")

    context = {
        "user_request": user_request,
        "selected_job": job,
        "career_details": evidence.get("career_details", {}),
        "evidence": evidence,
        "planner_result": planner_result,
    }

    fields = {
        "result": str,
        "evidence_used": list,
        "missing_information": list,
    }

    response = generate("career_worker", context, fields)

    if not isinstance(response, dict):
        raise ModelError("Career Worker returned an invalid response")

    answer = response.get("result")

    if not isinstance(answer, str) or not answer.strip():
        raise ModelError("Career Worker returned an empty result")

    # Build missing-information output deterministically.
    missing = response.get("missing_information", [])

    if not isinstance(missing, list):
        missing = []

    missing = [
        item.strip()
        for item in missing
        if isinstance(item, str) and item.strip()
    ]

    description = str(job.get("description") or "").strip()
    requirements = str(job.get("requirements") or "").strip()

    if not description:
        missing.append("The job description is not provided.")

    if not requirements:
        missing.append("The job requirements are not provided.")

    if not job.get("location"):
        missing.append("The job location is not specified.")

    if not job.get("salary"):
        missing.append("Salary information is not specified.")

    job_text = f"{description} {requirements}".casefold()

    if not any(term in job_text for term in (
        "degree", "education", "bachelor", "master",
        "qualification", "equivalent experience",
    )):
        missing.append(
            "Specific education and qualification requirements "
            "are not stated."
        )

    if not any(term in job_text for term in (
        "years of experience", "experience required",
        "previous experience", "equivalent experience",
    )):
        missing.append(
            "The required duration of experience is not specified."
        )

    if not evidence.get("career_details"):
        missing.append(
            "No candidate profile is available. Personal suitability "
            "cannot be assessed."
        )

    return {
        "result": answer.strip(),
        "evidence_used": ["selected_job"],
        "missing_information": list(dict.fromkeys(missing)),
    }
