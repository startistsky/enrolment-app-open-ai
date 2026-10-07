import re

from llm_client import ModelError, generate


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


def run(user_request, evidence, planner_result):
    context = {"user_request": user_request, "evidence": evidence,
               "planner_result": planner_result}
    fields = {"answer": str, "evidence_used": list, "missing_evidence": list}
    result = generate("worker", context, fields)
    if _valid_attribution(result, evidence):
        return result
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
    result = generate("worker", context, fields)
    if not _valid_attribution(result, evidence):
        references = _resolve_provenance(result["answer"], evidence)
        if not references:
            raise ModelError("Invalid worker evidence attribution after one corrective retry")
        result = {**result, "evidence_used": references}
    return result
