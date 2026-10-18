"""Student 3 Resource Planner Agent."""

from agents.resource_worker_agent import matching_resources
from llm_client import generate


def run(user_request, evidence):
    matches = matching_resources(user_request, evidence)

    context = {
        "user_request": user_request,
        "evidence": matches,
        "available_fields": [
            "resource_id",
            "resource_name",
            "resource_type",
            "building",
            "floor",
            "location",
            "capacity",
            "availability_status",
            "opening_hours",
            "description",
        ],
        "instruction": (
            "Plan only for the user's explicitly requested resource type "
            "and conditions. Do not introduce unrelated resource types. "
            "Only reference the supplied matching evidence."
        ),
    }

    return generate(
        "planner",
        context,
        {
            "plan": str,
            "evidence_required": list,
        },
        prompt_name="resource_planner",
    )
