
from llm_client import generate


def run(user_request, evidence):
    """Plan an event analysis using database evidence."""

    context = {
        "feature": "event_management",
        "user_request": user_request,
        "evidence": evidence,
        "available_fields": [
            "id", "title", "category", "date",
            "location", "description", "emoji"
        ]
    }

    return generate(
        role="planner",
        context=context,
        required_fields={
            "plan": str,
            "evidence_required": list
        },
        prompt_name="event_planner"
    )
