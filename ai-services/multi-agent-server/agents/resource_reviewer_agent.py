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

        has_capacity = bool(cited_records) and all(
            record.get("capacity") is not None
            for record in cited_records
        )

        has_availability = bool(cited_records) and all(
            record.get("availability_status")
            for record in cited_records
        )

        import re

        worker_answer = str(worker_result.get("answer", ""))
        ids_in_answer = set(
            re.findall(r"\bID\s*:\s*(\d+)\b", worker_answer, re.I)
        )
        ids_verified_in_answer = bool(cited_ids) and cited_ids.issubset(
            ids_in_answer
        )

        def contradicts_verified_evidence(value):
            if isinstance(value, dict):
                text = " ".join(str(v) for v in value.values()).casefold()
            else:
                text = str(value).casefold()

            missing_ids = ids_verified_in_answer and (
                "missing resource id" in text
                or "no resource id" in text
                or "did not provide resource id" in text
                or "does not provide resource id" in text
                or ("does not specify" in text and "resource id" in text)
                or ("should specify" in text and "resource id" in text)
                or ("should provide" in text and "resource id" in text)
                or ("does not provide" in text and "resource id" in text)
                or "did not cite" in text
                or "no citations" in text
            )

            missing_capacity = has_capacity and (
                "missing capacity" in text
                or "no capacity information" in text
                or "capacity is not provided" in text
            )

            missing_availability = has_availability and (
                "missing availability" in text
                or "no availability information" in text
                or "availability is not provided" in text
            )

            return (
                missing_ids
                or missing_capacity
                or missing_availability
            )

        result["unsupported_claims"] = [
            claim
            for claim in result["unsupported_claims"]
            if not contradicts_verified_evidence(claim)
        ]

        for field in ("risk", "correction", "recommendation"):
            if contradicts_verified_evidence(result[field]):
                result[field] = {
                    "risk": (
                        "No unsupported resource ID, capacity or "
                        "availability claim was verified."
                    ),
                    "correction": (
                        "Use the verified resource evidence."
                    ),
                    "recommendation": (
                        "Proceed to human review."
                    ),
                }[field]

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
