from llm_client import generate, ModelError

# planner agent
def run(user_request, evidence):
    """Plan a career task using the selected job record."""

    if not isinstance(evidence, dict):
        raise ModelError("Career evidence must be a dictionary")

    selected_job = evidence.get("selected_job")

    if not isinstance(selected_job, dict):
        raise ModelError("Selected job record is missing")

    context = {
        "user_request": user_request,
        "selected_job": selected_job,
        "evidence": evidence,
    }

    fields = {
        "plan": str,
        "evidence_required": list,
    }

    result = generate("career_planner", context, fields)

    if not isinstance(result, dict):
        raise ModelError("Career Planner returned an invalid response")

    plan = result.get("plan")
    requirements = result.get("evidence_required")

    if not isinstance(plan, str) or not plan.strip():
        raise ModelError("Career Planner returned an empty plan")

    if not isinstance(requirements, list):
        raise ModelError(
            "Career Planner returned invalid evidence requirements"
        )

    return {
        "plan": plan.strip(),
        "evidence_required": requirements,
    }