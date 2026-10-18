"""Student 3: resource evidence validation helpers."""


def valid_references(evidence):
    """Return valid resource IDs from supplied database evidence."""
    return {
        str(record["resource_id"])
        for record in evidence
        if isinstance(record, dict)
        and record.get("resource_id") is not None
        and not isinstance(record["resource_id"], bool)
    }


def valid_attribution(result, evidence):
    """Ensure the Worker references only real resource records."""
    references = result.get("evidence_used", [])

    if not isinstance(references, list):
        return False

    allowed = valid_references(evidence)

    if not all(
        isinstance(reference, str) and reference in allowed
        for reference in references
    ):
        return False

    if evidence and result.get("answer", "").strip():
        return bool(references)

    return not references


def normalize_evidence(evidence):
    """Keep only valid resource records with unique IDs."""
    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a list")

    normalized = []
    seen = set()

    for record in evidence:
        if not isinstance(record, dict):
            continue

        resource_id = record.get("resource_id")

        if resource_id is None or isinstance(resource_id, bool):
            continue

        identifier = str(resource_id).strip()

        if not identifier or identifier in seen:
            continue

        normalized.append({**record, "resource_id": identifier})
        seen.add(identifier)

    return normalized
