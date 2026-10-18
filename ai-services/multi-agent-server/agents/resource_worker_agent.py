"""Student 3 Resource Worker Agent."""

import re

from agents.resource_request import normalize_evidence
from llm_client import ModelError, generate


def matching_resources(user_request, evidence):
    """Filter resources using explicit user requirements."""
    records = normalize_evidence(evidence)
    request = user_request.casefold()

    capacity_match = re.search(
        r"(?:for\s+|at least\s+|minimum\s+)?"
        r"(\d+)\s+(?:students?|people|persons?)\b",
        request,
    )

    minimum_capacity = (
        int(capacity_match.group(1)) if capacity_match else None
    )

    needs_available = bool(
        re.search(r"\bavailable\b", request)
    ) and not bool(
        re.search(r"\bunavailable\b", request)
    )

    type_patterns = {
        "study room": r"\bstudy\s+rooms?\b",
        "study space": r"\b(?:study\s+spaces?|quiet\s+study\s+areas?)\b",
        "printer": r"\b(?:printers?|printing)\b",
        "library": r"\blibrar(?:y|ies)\b",
    }

    requested_types = [
        resource_type
        for resource_type, pattern in type_patterns.items()
        if re.search(pattern, request)
    ]

    matches = []

    for record in records:
        resource_type = str(
            record.get("resource_type", "")
        ).casefold()

        resource_name = str(
            record.get("resource_name", "")
        ).casefold()

        combined_type = resource_type

        if requested_types:
            type_matches = {
                "study room": "study room" in combined_type,
                "study space": (
                    "study space" in combined_type
                    or "quiet study area" in combined_type
                ),
                "printer": (
                    "printer" in combined_type
                    or "printing" in combined_type
                ),
                "library": "library" in combined_type,
            }

            if not any(
                type_matches[requested_type]
                for requested_type in requested_types
            ):
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

    if not cited_ids or not cited_ids.issubset(allowed_ids):
        selected = matches
    else:
        selected = [
            record for record in matches
            if record["resource_id"] in cited_ids
        ]

    descriptions = [
        (
            f'{record.get("resource_name", "Resource")} '
            f'(ID: {record["resource_id"]}, '
            f'capacity: {record.get("capacity", "unknown")}, '
            f'status: {record.get("availability_status", "unknown")})'
        )
        for record in selected
    ]

    return {
        "answer": "Matching campus resources: " + "; ".join(descriptions),
        "evidence_used": sorted(
            record["resource_id"] for record in selected
        ),
        "missing_evidence": [],
    }

