import re

from agents.worker_agent import _valid_attribution
from llm_client import ModelError, generate


def _normalise(value):
    return " ".join(value.casefold().split())


def _contains(text, value):
    return bool(re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text))


def _support_facts(evidence, planner_result, worker_result):
    """Verify exact values only; matching a name does not validate added claims."""
    answer = _normalise(worker_result["answer"])
    valid_references = _valid_attribution(worker_result, evidence)
    references = worker_result["evidence_used"] if valid_references else []
    values = []
    for record in evidence:
        if not any(str(record.get(field)) == str(reference)
                   for field in ("course_code", "course_id") for reference in references):
            continue
        for field in ("course_code", "course_name"):
            value = record.get(field)
            if isinstance(value, str) and value.strip() and _contains(answer, _normalise(value)):
                values.append(value)
    return {
        "worker_answer_supported": bool(values),
        "validated_evidence_used": references,
        "supported_exact_values": values,
        "whole_answer_exact_match": any(answer == _normalise(value) for value in values),
        "plan_to_review_separately": planner_result,
        "scope": "Only matched exact values are verified; additional factual claims and plan compliance require review.",
    }


def _contradicts(result, facts):
    if not facts["worker_answer_supported"]:
        return False
    # When the entire answer is one verified value, it has no additional
    # factual claim to list as unsupported. Plan findings remain separate.
    if facts["whole_answer_exact_match"] and result["unsupported_claims"]:
        return True
    supported = [_normalise(value) for value in facts["supported_exact_values"]]
    unsupported_cues = ("unsupported", "not supported", "absent from", "not in the evidence", "not grounded")
    for claim in result["unsupported_claims"]:
        if not isinstance(claim, str):
            return True
        text = _normalise(claim)
        if text in supported:
            return True
        # Formatting/completeness/plan findings belong outside factual claims.
        if any(cue in text for cue in ("formatting", "completeness", "plan compliance", "follow the plan", "follow plan")):
            return True
        if any(cue in text for cue in unsupported_cues) and (
            any(_contains(text, value) for value in supported)
            or (facts["whole_answer_exact_match"] and any(word in text for word in ("answer", "worker", "claim")))
        ):
            return True
    # A wholly exact answer cannot carry an unsupported-fact risk, even if the
    # model forgets to list that claim. Other risk categories remain allowed.
    risk = _normalise(result["risk"])
    if any(phrase in risk for phrase in ("no unsupported", "no risk", "not unsupported")):
        return False
    return facts["whole_answer_exact_match"] and any(cue in risk for cue in unsupported_cues)


def run(user_request, evidence, planner_result, worker_result):
    facts = _support_facts(evidence, planner_result, worker_result)
    context = {"user_request": user_request, "evidence": evidence,
               "planner_result": planner_result, "worker_result": worker_result,
               "verified_support_facts": facts}
    fields = {"risk": str, "unsupported_claims": list, "correction": str, "recommendation": str}
    result = generate("reviewer", context, fields)
    if _contradicts(result, facts):
        context["previous_reviewer_result"] = result
        context["correction_instruction"] = (
            "Your review contradicts verified_support_facts. Do not classify verified "
            "exact values as unsupported. Only report genuinely absent factual claims. "
            "Review plan compliance, formatting and completeness separately in risk, "
            "correction or recommendation, never as unsupported factual claims. "
            "Return the same Reviewer JSON schema; do not make a human decision."
        )
        result = generate("reviewer", context, fields)
        if _contradicts(result, facts):
            raise ModelError("Invalid reviewer evidence consistency after one corrective retry")
    return result
