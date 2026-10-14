from agents.assignment_request import valid_attribution, valid_references
from llm_client import generate


def run(user_request, evidence, planner_result, worker_result):
    validation = {
        "evidence_attribution_valid": valid_attribution(worker_result, evidence),
        "allowed_evidence_references": sorted(valid_references(evidence)),
        "worker_references": worker_result.get("evidence_used", []),
    }
    context = {
        "user_request": user_request,
        "evidence": evidence,
        "planner_result": planner_result,
        "worker_result": worker_result,
        "deterministic_validation": validation,
    }
    return generate(
        "reviewer",
        context,
        {
            "risk": str,
            "unsupported_claims": list,
            "correction": str,
            "recommendation": str,
        },
        prompt_name="assignment_reviewer",
    )
