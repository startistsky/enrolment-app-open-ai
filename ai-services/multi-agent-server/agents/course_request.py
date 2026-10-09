"""Conservative exact-field checks for explicit Course Management questions."""
import re


FIELDS = ('course_name', 'course_code', 'course_id')


def normalise(value):
    return ' '.join(str(value).casefold().split())


def contains(text, value):
    return bool(re.search(r'(?<!\w)' + re.escape(normalise(value)) + r'(?!\w)', normalise(text)))


def request_parts(user_request, evidence):
    request = normalise(user_request)
    patterns = {
        'course_name': r'\bcourse[ _]name\b|\bname of\b|\bname (?:the |this |that |a )?course\b|\bwhat\b.*\bname\b',
        'course_code': r'\bcourse[ _]code\b|\bsupporting code\b',
        'course_id': r'\bcourse[ _](?:id|identifier)\b|\bid of\b',
    }
    requested = [field for field, pattern in patterns.items() if re.search(pattern, request)]
    if re.search(r'\b(?:lecturer|instructor|teacher)\b', request) and not re.search(
        r'\bcourse[ _]name\b|\bname of (?:the )?(?:course|[a-z]*[0-9][\w-]*)\b', request
    ):
        requested = [field for field in requested if field != 'course_name']
    # A code/name explicitly identifying a record takes priority over attribution.
    targets = [row for row in evidence if any(
        isinstance(row.get(field), str) and row[field].strip() and contains(request, row[field])
        for field in ('course_code', 'course_name')
    )]
    if not targets:
        targets = [row for row in evidence if re.search(r'\bcourse[ _]id\b', request)
                   and isinstance(row.get('course_id'), (str, int))
                   and not isinstance(row['course_id'], bool) and contains(request, row['course_id'])]
    if not targets and len(evidence) == 1:
        targets = evidence
    return requested, targets


def requested_values(user_request, evidence):
    requested, targets = request_parts(user_request, evidence)
    if len(targets) != 1:
        return {}
    record = targets[0]
    return {field: record[field] for field in requested
            if isinstance(record.get(field), (str, int)) and not isinstance(record[field], bool)
            and str(record[field]).strip()}


def missing_fields(answer, expected):
    return [field for field, value in expected.items() if not contains(answer, value)]


def completion_requirements(user_request, evidence):
    """Keep recognized fields missing when no unique available value exists."""
    requested, _ = request_parts(user_request, evidence)
    # Empty evidence can still legitimately report unavailable context.
    return requested if evidence else []


def deterministic_completion(user_request, evidence):
    """Complete simple field lookups only; refuse unsupported request wording."""
    requested, targets = request_parts(user_request, evidence)
    if not requested or len(targets) != 1:
        return None
    record = targets[0]
    values = requested_values(user_request, evidence)
    if any(field not in values for field in requested):
        return None
    # A conservative grammar excludes other field/task requests even when a
    # supported field is mentioned too. Unknown wording fails, never guesses.
    text = normalise(user_request)
    for field in FIELDS:
        value = record.get(field)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            text = re.sub(r'(?<!\w)' + re.escape(normalise(value)) + r'(?!\w)', ' ', text)
    allowed_words = set('what is are the a an of for this that course name code id identifier '
                        'supporting identify please tell me give show return which and with '
                        'also its it name course_name course_code course_id'.split())
    if any(word not in allowed_words for word in re.findall(r'\w+', text)):
        return None
    reference = record.get('course_code')
    if not isinstance(reference, str) or not reference.strip():
        reference = record.get('course_id')
    if not isinstance(reference, (str, int)) or isinstance(reference, bool) or not str(reference).strip():
        return None
    if requested == ['course_name', 'course_code']:
        answer = f"{values['course_name']} ({values['course_code']})"
    elif len(requested) == 1:
        answer = str(values[requested[0]])
    else:
        answer = '. '.join(field.replace('_', ' ').capitalize() + ': ' + str(values[field])
                           for field in requested)
    if missing_fields(answer, values):
        return None
    return {'answer': answer, 'evidence_used': [reference], 'missing_evidence': []}
