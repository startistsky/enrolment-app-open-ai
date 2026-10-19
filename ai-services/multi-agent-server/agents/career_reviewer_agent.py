from llm_client import generate, ModelError

# reviewer agent
def run(
    user_request,
    evidence,
    planner_result,
    worker_result,
    revision_feedback="",
):
    """Review the job analysis against the supplied job record."""

    if not isinstance(evidence, dict):
        raise ModelError("Career evidence must be a dictionary")

    selected_job = evidence.get("selected_job")

    if not isinstance(selected_job, dict):
        raise ModelError("Selected job record is missing")

    context = {
        "user_request": user_request,
        "selected_job": selected_job,
        "evidence": evidence,
        "planner_result": planner_result,
        "worker_result": worker_result,
        "revision_feedback": revision_feedback,
        "review_requirements": {
            "check_job_relevance": True,
            "check_factual_support": True,
            "check_completeness": True,
            "check_missing_information": True,
            "check_plan_compliance": True,
            "do_not_infer_candidate_qualifications": True,
            "do_not_invent_job_requirements": True,
        },
    }

    fields = {
        "risk": str,
        "unsupported_claims": list,
        "correction": str,
        "recommendation": str,
    }

    result = generate("career_reviewer", context, fields)

    if not isinstance(result, dict):
        raise ModelError("Career Reviewer returned an invalid response")

    for field in ("risk", "correction", "recommendation"):
        if not isinstance(result.get(field), str):
            raise ModelError(
                f"Career Reviewer returned invalid {field}"
            )

    if not result["risk"].strip():
        raise ModelError("Career Reviewer returned an empty risk assessment")

    if not result["recommendation"].strip():
        raise ModelError(
            "Career Reviewer returned an empty recommendation"
        )

    claims = result.get("unsupported_claims")

    if not isinstance(claims, list) or not all(
        isinstance(item, str) for item in claims
    ):
        raise ModelError(
            "Career Reviewer returned invalid unsupported claims"
        )

    return {
        "risk": result["risk"].strip(),
        "unsupported_claims": claims,
        "correction": result["correction"].strip(),
        "recommendation": result["recommendation"].strip(),
    }