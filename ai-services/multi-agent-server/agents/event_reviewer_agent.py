
from llm_client import generate, ModelError


def run(user_request, evidence, planner_result, worker_result):
    """Review the Worker output against event database evidence."""

    valid_ids = {
        str(event["id"])
        for event in evidence
        if isinstance(event, dict) and "id" in event
    }

    references = worker_result.get("evidence_used", [])

    for reference in references:
        if (
            not isinstance(reference, (str, int))
            or isinstance(reference, bool)
            or str(reference) not in valid_ids
        ):
            raise ModelError(
                "Reviewer found an invalid event evidence reference."
            )

    context = {
        "feature": "event_management",
        "user_request": user_request,
        "evidence": evidence,
        "planner_result": planner_result,
        "worker_result": worker_result,
        "review_instructions": (
            "Verify the Worker answer against the supplied event "
            "records. Identify unsupported claims, missing evidence "
            "and deviations from the Planner's plan."
        )
    }

    return generate(
        role="reviewer",
        context=context,
        required_fields={
            "risk": str,
            "unsupported_claims": list,
            "correction": str,
            "recommendation": str
        },
        prompt_name="event_reviewer"
    )
