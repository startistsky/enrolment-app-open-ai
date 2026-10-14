"""Student 3 Resource Reviewer Agent."""

from agents.resource_request import normalize_evidence
from agents.resource_worker_agent import matching_resources
from llm_client import generate


def run(user_request, evidence, planner_result, worker_result):
    records = normalize_evidence(evidence)
    matches = matching_resources(user_request, records)

    valid_ids = {record["resource_id"] for record in records}
    matching_ids = {record["resource_id"] for record in matches}

    references = worker_result.get("evidence_used", [])

    cited_ids = {
        str(reference)
        for reference in references
        if isinstance(reference, (str, int))
        and not isinstance(reference, bool)
    } if isinstance(references, list) else set()

    invalid_ids = sorted(cited_ids - valid_ids)
    nonmatching_ids = sorted(cited_ids - matching_ids)

    findings = []

    if not isinstance(references, list):
        findings.append("Worker evidence_used must be a list.")

    if invalid_ids:
        findings.append(
            "Invalid resource IDs: " + ", ".join(invalid_ids)
        )

    if nonmatching_ids:
        findings.append(
            "Cited resources do not satisfy the request: "
            + ", ".join(nonmatching_ids)
        )

    if matches and not cited_ids:
        findings.append("Worker did not cite matching resources.")

    if not matches and cited_ids:
        findings.append("Worker cited resources despite no matching evidence.")

    verified_checks = {
        "matching_resource_ids": sorted(matching_ids),
        "cited_resource_ids": sorted(cited_ids),
        "validation_findings": findings,
    }

    context = {
        "user_request": user_request,
        "matching_evidence": matches,
        "worker_result": worker_result,
        "verified_checks": verified_checks,
        "instruction": (
            "Review only the supplied matching evidence and worker answer. "
            "Do not claim that availability or capacity is missing when "
            "it is explicitly present in the evidence or worker answer."
        ),
    }

    fields = {
        "risk": str,
        "unsupported_claims": list,
        "correction": str,
        "recommendation": str,
    }

    result = generate(
        "worker",
        context,
        fields,
        prompt_name="resource_reviewer",
    )

    if not findings and cited_ids:
        cited_records = [
            record for record in matches
            if record["resource_id"] in cited_ids
        ]

        has_capacity = all(
            record.get("capacity") is not None
            for record in cited_records
        )

        has_availability = all(
            record.get("availability_status")
            for record in cited_records
        )

        risk_text = result["risk"].casefold()

        missing_claim = (
            "do not provide any information" in risk_text
            or "missing availability" in risk_text
            or "missing capacity" in risk_text
        )

        if (
            cited_records
            and has_capacity
            and has_availability
            and missing_claim
        ):
            result["risk"] = (
                "No missing capacity or availability evidence "
                "was identified for the cited resources."
            )
            result["correction"] = (
                "No correction required for capacity or availability."
            )
            result["recommendation"] = (
                "Proceed to human review with verified resource evidence."
            )

    if findings:
        result["unsupported_claims"].extend(findings)
        result["risk"] = "Evidence validation failed: " + "; ".join(findings)
        result["correction"] = (
            "Correct the Worker response using matching resource evidence."
        )
        result["recommendation"] = (
            "Do not accept until evidence validation passes."
        )

    return result
