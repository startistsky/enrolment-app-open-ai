import re

from agents.assignment_request import valid_attribution, valid_references
from llm_client import ModelError, generate


def normalize_evidence_used(result, evidence):
    """
    Convert model-generated evidence references into exact assignment_id strings.

    The model may return:
    - 1
    - "1"
    - "assignment:1"
    - an assignment title
    - {"assignment_id": 1}

    All accepted references are normalised to values such as "1".
    """
    allowed = valid_references(evidence)

    title_to_reference = {
        str(record.get("assignment_title", "")).strip().lower():
        str(record.get("assignment_id"))
        for record in evidence
        if record.get("assignment_id") is not None
        and str(record.get("assignment_title", "")).strip()
    }

    normalized = []

    for reference in result.get("evidence_used", []):
        if isinstance(reference, dict):
            reference = reference.get("assignment_id", "")

        value = str(reference).strip()

        if value in allowed:
            normalized.append(value)
            continue

        title_match = title_to_reference.get(value.lower())
        if title_match in allowed:
            normalized.append(title_match)
            continue

        number_match = re.search(r"\d+", value)
        if number_match and number_match.group() in allowed:
            normalized.append(number_match.group())

    # If the model cited assignment titles inside the answer, recover their IDs.
    answer = str(result.get("answer", "")).lower()

    for title, assignment_id in title_to_reference.items():
        if title and title in answer and assignment_id in allowed:
            normalized.append(assignment_id)

    result["evidence_used"] = list(dict.fromkeys(normalized))
    return result


def run(user_request, evidence, planner_result):
    context = {
        "user_request": user_request,
        "evidence": evidence,
        "planner_result": planner_result,
        "allowed_evidence_references": sorted(valid_references(evidence)),
    }

    fields = {
        "answer": str,
        "evidence_used": list,
        "missing_evidence": list,
    }

    result = generate(
        "worker",
        context,
        fields,
        prompt_name="assignment_worker",
    )

    result = normalize_evidence_used(result, evidence)

    if valid_attribution(result, evidence):
        return result

    context["previous_worker_result"] = result
    context["correction_instruction"] = (
        "Correct evidence_used. It must be a JSON array containing only exact "
        "assignment_id strings from allowed_evidence_references, for example "
        '[\"1\", \"4\"]. Do not use assignment titles, objects, labels or '
        "assignment:id formatting. Do not change the required JSON fields."
    )

    result = generate(
        "worker",
        context,
        fields,
        prompt_name="assignment_worker",
    )

    result = normalize_evidence_used(result, evidence)

    if not valid_attribution(result, evidence):
        raise ModelError(
            "Invalid assignment evidence attribution after one corrective retry"
        )

    return result