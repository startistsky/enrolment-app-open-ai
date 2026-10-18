import re

from agents.course_request import FIELDS, contains, missing_fields, requested_values
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



def _misstates_worker(result, worker_result, evidence, completeness):
    """Reject explicit positive attribution of evidence-only facts to the Worker."""
    text = " ".join([result["risk"], result["correction"], result["recommendation"],
                     *(claim for claim in result["unsupported_claims"] if isinstance(claim, str))])
    if completeness["missing_requested_fields"]:
        normalised = _normalise(text)
        # A supported but incomplete answer must be reviewed as incomplete.
        if not re.search(r"\b(incomplete|incompleteness|missing|omitted|omit|include|provide|add|not answered)\b", normalised):
            return True
        if re.search(r"\b(worker|answer|output|response)\b.*\b(correctly answered|fully answered|fully satisfies)\b", normalised):
            return True
    for sentence in re.split(r"[.!?;]", text):
        sentence = _normalise(sentence)
        if not re.search(r"\b(worker|answer|output|response)\b", sentence):
            continue
        if not re.search(r"\b(identified|provided|returned|answered|included|named|stated|correctly answered)\b", sentence):
            continue
        if re.search(r"\b(not|never|missing|omitted|should|must|needs|fails|failed|doesn't|didn't)\b", sentence):
            continue
        for record in evidence:
            for field in FIELDS:
                value = record.get(field)
                if (isinstance(value, (str, int)) and not isinstance(value, bool)
                        and str(value).strip() and contains(sentence, value)
                        and not contains(worker_result["answer"], value)):
                    return True
        for field in completeness["missing_requested_fields"]:
            label = field.replace("_", " ")
            if contains(sentence, label):
                return True
    return False

def run(user_request, evidence, planner_result, worker_result):
    facts = _support_facts(evidence, planner_result, worker_result)
    expected = requested_values(user_request, evidence)
    completeness = {"requested_field_values": expected,
                    "missing_requested_fields": missing_fields(worker_result["answer"], expected)}
    completeness["worker_answer_complete"] = not completeness["missing_requested_fields"]
    context = {"user_request": user_request, "evidence": evidence,
               "planner_result": planner_result, "worker_result": worker_result,
               "verified_support_facts": facts, "verified_completeness_facts": completeness}
    fields = {"risk": str, "unsupported_claims": list, "correction": str, "recommendation": str}
    result = generate("reviewer", context, fields)
    if _contradicts(result, facts) or _misstates_worker(result, worker_result, evidence, completeness):
        context["previous_reviewer_result"] = result
        context["correction_instruction"] = (
            "Your review contradicts verified_support_facts. Do not classify verified "
            "exact values as unsupported. Only report genuinely absent factual claims. "
            "Review plan compliance, formatting and completeness separately in risk, "
            "correction or recommendation, never as unsupported factual claims. "
            "Use verified_completeness_facts separately from factual support and plan "
            "compliance. Never say the Worker identified a supplied value that is "
            "absent from worker_result.answer. Identify missing requested fields as "
            "incompleteness, not unsupported facts. Return the same Reviewer JSON "
            "schema; do not make a human decision."
        )
        result = generate("reviewer", context, fields)
        if _contradicts(result, facts) or _misstates_worker(result, worker_result, evidence, completeness):
            raise ModelError("Invalid reviewer evidence consistency after one corrective retry")
    return result


# student 5 reviewer workflow
def run_career(user_request, selected_job, career_details, planner_result, worker_result, revision_feedback=None,): 
        """Review a career worker response against the selected job and user evidence."""

        # validate function input 
        if not isinstance(user_request, str) or not user_request.strip():
            raise ValueError("user_request is required")

        if not isinstance(selected_job, dict): 
            raise ValueError("selectedjob must be a dictionary")

        if not isinstance(selected_job.get("id"), int) or isinstance( selected_job.get("id"), bool ): 
            raise ValueError("selected_job must contain an integer job id")

        if not isinstance(career_details, dict): 
            raise ValueError("careerdetails must be a dictionary")

        # validate planner result 
        if not isinstance(planner_result, dict): 
            raise ValueError("plannerresult must be a dictionary")

        # validate worker result
        if not isinstance(worker_result, dict):
            raise ModelError("Career Worker result must be a dictionary")

        if not isinstance(worker_result.get("result"), str):
            raise ModelError("Career Worker result must be a string")

        if not isinstance(worker_result.get("evidence_used"), list):
            raise ModelError("Career Worker evidence_used must be a list")

        if not isinstance(worker_result.get("missing_information"), list):
            raise ModelError("Career Worker missing_information must be a list")

        if not all(
            isinstance(item, str) and item.strip()
            for item in worker_result["evidence_used"]
        ):
            raise ModelError("Career Worker returned invalid evidence references")

        if not all(
            isinstance(item, str) and item.strip()
            for item in worker_result["missing_information"]
        ):
            raise ModelError("Career Worker returned invalid missing information")

        # validate revision 
        if revision_feedback is not None and not isinstance( revision_feedback, str ): 
            raise ValueError("revision_feedback must be a string")

        # context building
        context = {
            "user_request": user_request.strip(),
            "selected_job": selected_job,
            "career_details": career_details,
            "planner_result": planner_result,
            "worker_result": worker_result,
            "revision_feedback": revision_feedback or "",
            "review_requirements": {
                "check_job_relevance": True,
                "check_factual_support": True,
                "check_personal_fact_accuracy": True,
                "check_plan_compliance": True,
                "check_completeness": True,
                "check_evidence_attribution": True,
                "check_missing_information": True,
            },
        }

        fields = { 
            "risk": str, ""
            "unsupported_claims": list, 
            "correction": str, 
            "recommendation": str, 
        }

        result = generate("career_reviewer", context, fields)

        print("DEBUG career reviewer result:", repr(result))
        print("DEBUG unsupported_claims:", repr(result.get("unsupported_claims")))
        print(
            "DEBUG unsupported_claims type:",
            type(result.get("unsupported_claims")),
        )

        # validate unsupported claims
        if not all( isinstance(item, str) for item in result["unsupported_claims"] ): 
            raise ModelError( "Career Reviewer returned invalid unsupported claims" )

        # A review must not approve unsupported claims merely 
        # just because the worker cited the selected job as its source.

        if not result["risk"].strip(): 
            raise ModelError("Career Reviewer returned an empty risk assessment")

        if not result["recommendation"].strip(): 
            raise ModelError("Career Reviewer returned an empty recommendation")

        return result