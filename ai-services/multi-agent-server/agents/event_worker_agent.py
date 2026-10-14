
from llm_client import generate, ModelError



def valid_attribution(result, evidence):
    """Validate and normalize event evidence references."""

    valid_ids = {
        str(event["id"])
        for event in evidence
        if isinstance(event, dict)
        and isinstance(event.get("id"), (str, int))
        and not isinstance(event["id"], bool)
    }

    references = result.get("evidence_used", [])

    if not isinstance(references, list):
        return False

    normalized_references = []

    for reference in references:
        # Ollama may return an event object instead of only its ID.
        if isinstance(reference, dict):
            reference = reference.get("id")

        if (
            not isinstance(reference, (str, int))
            or isinstance(reference, bool)
            or str(reference) not in valid_ids
        ):
            return False

        normalized_references.append(reference)

    # A non-empty answer must cite at least one event when evidence exists.
    if evidence and result.get("answer", "").strip() and not normalized_references:
        return False

    # Normalize into the ID-only format expected by the system.
    result["evidence_used"] = normalized_references

    return True



def run(user_request, evidence, planner_result):
    """Execute an event analysis with one corrective retry."""

    context = {
        "feature": "event_management",
        "user_request": user_request,
        "evidence": evidence,
        "planner_result": planner_result
    }

    fields = {
        "answer": str,
        "evidence_used": list,
        "missing_evidence": list
    }

    result = generate(
        role="worker",
        context=context,
        required_fields=fields,
        prompt_name="event_worker"
    )


    if valid_attribution(result, evidence):
        return result

    # One corrective retry for invalid evidence references.
    context["previous_worker_result"] = result
    context["correction_instruction"] = (
        "The previous evidence_used field contained invalid or "
        "missing event IDs. Correct the attribution. "
        "Use only exact event IDs from the supplied evidence. "
        "Do not invent events or references. "
        "Return the same JSON structure."
    )

    corrected = generate(
        role="worker",
        context=context,
        required_fields=fields,
        prompt_name="event_worker"
    )

    if not valid_attribution(corrected, evidence):
        raise ModelError(
            "Worker evidence attribution invalid after corrective retry."
        )

    return corrected
