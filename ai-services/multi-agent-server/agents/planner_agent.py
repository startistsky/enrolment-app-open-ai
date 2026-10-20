import re

from agents.course_request import deterministic_completion, normalise, request_parts, requested_values
from llm_client import ModelError, generate


class PlannerResult(dict):
    """Source metadata is internal; public JSON retains its two fields."""
    def __init__(self, result, completion_source):
        super().__init__(result)
        self.completion_source = completion_source


def _fields(text):
    text = normalise(text)
    patterns = {'course_name': r'\b(?:course[ _])?name\b',
                'course_code': r'\b(?:course[ _])?code\b',
                'course_id': r'\b(?:course[ _])?(?:id|identifier)\b',
                'lecturer': r'\blecturer\b', 'semester': r'\bsemester\b',
                'credit_points': r'\bcredit[ _]points\b',
                'course_description': r'\b(?:course[ _])?description\b'}
    return {field for field, pattern in patterns.items() if re.search(pattern, text)}


def _aligned(result, requested, values):
    required = set(requested)
    if not result['plan'].strip() or _fields(result['plan']) != required:
        return False
    fields = set()
    for entry in result['evidence_required']:
        if isinstance(entry, str):
            identified = _fields(entry)
            if not identified:
                return False
            fields.update(identified)
        elif isinstance(entry, dict):
            if not entry or any(key not in required for key in entry):
                return False
            for key, value in entry.items():
                if key not in values or normalise(value) != normalise(values[key]):
                    return False
            fields.update(entry)
        else:
            return False
    return fields == required


def run(user_request, evidence):
    requested, targets = request_parts(user_request, evidence)
    values = requested_values(user_request, evidence)
    context = {'user_request': user_request, 'evidence': evidence,
               'explicit_requested_fields': requested}
    fields = {'plan': str, 'evidence_required': list}
    result = generate('planner', context, fields)
    # Generic tasks retain existing planning; field checks apply to explicit lookups.
    if not requested:
        return PlannerResult(result, 'model')
    unique_target = not evidence or len(targets) == 1
    if unique_target and _aligned(result, requested, values):
        return PlannerResult(result, 'model')
    context['previous_planner_result'] = result
    context['correction_instruction'] = (
        'Align plan and evidence_required exactly with explicit_requested_fields: '
        + ', '.join(requested) + '. Do not substitute or add course_id unless '
        'explicitly requested. Mention each requested field in plan and require '
        'each field in evidence_required; do not invent evidence values. Keep the '
        'same JSON schema. Review only the supplied evidence.'
    )
    result = generate('planner', context, fields)
    if unique_target and _aligned(result, requested, values):
        return PlannerResult(result, 'corrective_retry')
    # Reuse the existing conservative single-record/simple-request fallback guard.
    if deterministic_completion(user_request, evidence) is None:
        raise ModelError('Invalid planner request-field alignment after one corrective retry')
    fallback = {'plan': 'Identify ' + ' and '.join(field.replace('_', ' ') for field in requested)
                       + ' using the matched supplied course record.',
                'evidence_required': [{field: values[field] for field in requested}]}
    if not _aligned(fallback, requested, values):
        raise ModelError('Invalid planner request-field alignment after one corrective retry')
    return PlannerResult(fallback, 'deterministic_evidence_fallback')


