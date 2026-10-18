import re

from agents.course_request import completion_requirements, deterministic_completion, missing_fields, requested_values
from llm_client import ModelError, generate

class WorkerResult(dict):
    """Keep source metadata off the public JSON dictionary/schema."""
    def __init__(self, result, completion_source="model"):
        super().__init__(result)
        self.completion_source = completion_source

def _valid_attribution(result, evidence):
    """Check record identifiers, never infer citations from answer text."""
    identifiers = {
        str(record[field])
        for record in evidence
        for field in ("course_code", "course_id")
        if isinstance(record.get(field), (str, int))
        and not isinstance(record[field], bool) and str(record[field]).strip()
    }
    references = result["evidence_used"]
    if any(
        not isinstance(value, (str, int)) or isinstance(value, bool)
        or str(value) not in identifiers
        for value in references
    ):
        return False
    # Conservatively require attribution for every nonblank answer with records.
    return bool(references) or not evidence or not result["answer"].strip()


def _resolve_provenance(answer, evidence):
    """Resolve only a unique record with an exact, bounded value in the answer."""
    normalised_answer = " ".join(answer.casefold().split())
    matches = []
    for record in evidence:
        values = {
            field: value for field in ("course_code", "course_name", "course_id")
            if isinstance(value := record.get(field), (str, int))
            and not isinstance(value, bool) and str(value).strip()
        }
        if any(
            re.search(r"(?<!\w)" + re.escape(" ".join(str(value).casefold().split())) + r"(?!\w)",
                      normalised_answer)
            for value in values.values()
        ):
            matches.append(values)
    # Multiple matching records (including shared names) remain ambiguous.
    if len(matches) != 1:
        return []
    reference = matches[0].get("course_code", matches[0].get("course_id"))
    return [reference] if reference is not None else []


def run(user_request, evidence, planner_result, selectedJob):
    context = {"user_request": user_request, "evidence": evidence,
               "planner_result": planner_result}
    fields = {"answer": str, "evidence_used": list, "missing_evidence": list}
    expected = requested_values(user_request, evidence)
    context["requested_field_values"] = expected
    result = generate("worker", context, fields)
    required = completion_requirements(user_request, evidence)
    missing = list(dict.fromkeys(missing_fields(result["answer"], expected)
                                + [field for field in required if field not in expected]))
    if _valid_attribution(result, evidence) and not missing:
        return WorkerResult(result)
    context["previous_worker_result"] = result
    context["correction_instruction"] = (
        "Correct the evidence attribution. For a nonblank answer with supplied "
        "records, evidence_used must contain at least one exact course_code from "
        "the supplied evidence supporting the answer (course_id if no code is "
        "available). Every reference must identify a supplied record. Do not "
        "invent references or automatically cite all records. Return the same "
        "JSON schema; use [] for evidence_used only with empty evidence or a "
        "blank answer."
    )
    if missing:
        context["correction_instruction"] += (
            " The answer is incomplete. Include these requested factual fields in "
            "the answer itself: " + ", ".join(missing) + ". Use only the exact "
            "supplied requested_field_values; evidence_used alone is not an answer."
        )
    result = generate("worker", context, fields)
    if missing_fields(result["answer"], expected) or any(field not in expected for field in required):
        completed = deterministic_completion(user_request, evidence)
        if completed is None or not _valid_attribution(completed, evidence):
            raise ModelError("Incomplete worker answer after one corrective retry")
        return WorkerResult(completed, "deterministic_evidence_fallback")
    if not _valid_attribution(result, evidence):
        references = _resolve_provenance(result["answer"], evidence)
        if not references:
            raise ModelError("Invalid worker evidence attribution after one corrective retry")
        result = {**result, "evidence_used": references}
    return WorkerResult(result)


# student 5 
def run_career(user_request, selected_job, career_details=None, planner_result= None, revision_feedback = None):
    """Run a career task using the selected job and career details as evidence."""

    # validation
    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("user_request is required")

    if not isinstance(selected_job, dict):
        raise ValueError("selected_job must be a dictionary")

    career_details = career_details or {}

    if not isinstance(career_details, dict):
        raise ValueError("career_details must be a dictionary")

    if planner_result is not None and not isinstance(planner_result, dict): 
        raise ValueError("planner_result must be a dictionary")

    if revision_feedback is not None and not isinstance(revision_feedback, str):
        raise ValueError("revision_feedback must be a string")

    planner_result = planner_result or {}

    context = {
        "user_request": user_request.strip(),
        "selected_job": selected_job,
        "career_details": career_details,
        "plan": planner_result.get("plan", ""), 
        "evidencerequired": planner_result.get("evidencerequired", []),
        "revisionfeedback": revision_feedback or "", 
    }

    fields = {
        "result": str,
        "evidence_used": list,
        "missing_information": list,
    }

    result = generate("career_worker", context, fields)

    if not result["result"].strip(): 
        raise ModelError("Career Worker returned an empty result")

    if not all( isinstance(item, str) and item.strip() for item in result["evidence_used"] ): 
        raise ModelError( "Career Worker returned invalid evidence references" )

    if not all( isinstance(item, str) and item.strip() for item in result["missing_information"] ): 
        raise ModelError( "Career Worker returned invalid missing information" )

    valid_references = {
    f"job_id: {selected_job['id']}",
    "selected_job",
    "career_details",
    }

    if any(ref not in valid_references for ref in result["evidence_used"]):
        raise ModelError("Career Worker returned an unknown evidence reference")

    return WorkerResult(result, "model")