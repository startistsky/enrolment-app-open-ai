"""Student 3 Resource Worker Agent."""

import re

from agents.resource_request import normalize_evidence
from llm_client import ModelError, generate


def matching_resources(user_request, evidence):
    """Filter resources using explicit user requirements."""
    records = normalize_evidence(evidence)
    request = user_request.casefold()

    capacity_match = re.search(
        r"(?:for|at least|minimum)\s+(\d+)\s+"
        r"(?:students?|people|persons?)",
        request,
    )
    minimum_capacity = (
        int(capacity_match.group(1)) if capacity_match else None
    )

    needs_available = "available" in request

    needs_study_room = bool(
        re.search(r"\bstudy\s+rooms?\b", request)
    )

    matches = []

    for record in records:
        if needs_study_room:
            resource_type = str(
                record.get("resource_type", "")
            ).casefold()

            if "study room" not in resource_type:
                continue

        if minimum_capacity is not None:
            try:
                capacity = int(record.get("capacity"))
            except (TypeError, ValueError):
                continue

            if capacity < minimum_capacity:
                continue

        if needs_available:
            status = str(
                record.get("availability_status", "")
            ).strip().casefold()

            if status != "available":
                continue

        matches.append(record)

    return matches


def run(user_request, evidence, planner_result):
    matches = matching_resources(user_request, evidence)

    if not matches:
        return {
            "answer": "No matching campus resource was found in the supplied evidence.",
            "evidence_used": [],
            "missing_evidence": [],
        }

    context = {
        "user_request": user_request,
        "evidence": matches,
        "planner_result": planner_result,
        "instruction": (
            "Answer using only these matching resources. "
            "Do not add unsupported factual details."
        ),
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
        prompt_name="resource_worker",
    )

    allowed_ids = {
        record["resource_id"] for record in matches
    }

    cited_ids = {
        str(reference)
        for reference in result["evidence_used"]
        if isinstance(reference, (str, int))
        and not isinstance(reference, bool)
    }

    if not result["answer"].strip():
        raise ModelError("Resource Worker returned an empty answer")

    if cited_ids != allowed_ids:
        # A valid evidence-based fallback is safer than invented citations.
        descriptions = [
            (
                f'{record.get("resource_name", "Resource")} '
                f'(ID: {record["resource_id"]}, '
                f'capacity: {record.get("capacity", "unknown")}, '
                f'status: {record.get("availability_status", "unknown")})'
            )
            for record in matches
        ]

        return {
            "answer": "Matching campus resources: " + "; ".join(descriptions),
            "evidence_used": sorted(allowed_ids),
            "missing_evidence": [],
        }

    return result
