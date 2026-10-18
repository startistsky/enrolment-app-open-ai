"""Deterministic evidence helpers for Assignment Management workflows."""


def assignment_reference(record):
    """Return the preferred stable reference for an assignment record."""
    assignment_id = record.get("assignment_id")
    if isinstance(assignment_id, (str, int)) and not isinstance(assignment_id, bool):
        if str(assignment_id).strip():
            return str(assignment_id)
    title = record.get("assignment_title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def valid_references(evidence):
    return {
        reference
        for record in evidence
        if (reference := assignment_reference(record)) is not None
    }


def valid_attribution(result, evidence):
    references = result.get("evidence_used", [])
    if not isinstance(references, list):
        return False
    allowed = valid_references(evidence)
    if any(str(reference) not in allowed for reference in references):
        return False
    answer = result.get("answer", "")
    return bool(references) or not evidence or not str(answer).strip()
