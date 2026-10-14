from llm_client import generate


def run(user_request, evidence):
    context = {
        "user_request": user_request,
        "evidence": evidence,
        "available_fields": [
            "assignment_id",
            "assignment_title",
            "subject_name",
            "due_date",
            "priority",
            "status",
            "progress",
            "description",
        ],
    }
    return generate(
        "planner",
        context,
        {"plan": str, "evidence_required": list},
        prompt_name="assignment_planner",
    )
