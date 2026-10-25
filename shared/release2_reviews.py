"""Deterministic local report reviews; inputs are data, never executable content."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re

MODES = ('multi-agent-review', 'testing-review', 'cloud-review')
STUDENT_FEATURES = {
    '1': ('course_management',),
    '2': ('assignment_management',),
    '3': ('resource_management',),
    '4': ('event_management',),
    '5': ('career_management', 'careermanagement'),
}
FEATURE_STUDENTS = {
    feature: student
    for student, features in STUDENT_FEATURES.items()
    for feature in features
}
STUDENT_ENDPOINTS = {
    '1': (
        'POST /api/multi-agent/course-workflow',
        'POST /api/multi-agent/course-workflow/<workflow_id>/decision',
    ),
    '2': (
        'POST /api/multi-agent/assignment-workflow',
        'POST /api/multi-agent/assignment-workflow/<workflow_id>/decision',
    ),
    '3': (
        'POST /api/multi-agent/resource',
        'POST /api/multi-agent/<workflow_id>/decision',
    ),
    '4': (
        'POST /api/multi-agent/event-workflow',
        'POST /api/multi-agent/event-workflow/<workflow_id>/decision',
    ),
    '5': (
        'POST /api/workflow/career',
        'POST /api/workflow/<workflow_id>/decision',
    ),
}
ENDPOINTS = tuple(
    endpoint
    for student_endpoints in STUDENT_ENDPOINTS.values()
    for endpoint in student_endpoints
)
TESTING_ENDPOINTS = STUDENT_ENDPOINTS['1']
STUDENT_TEST_STEPS = {
    '1': 'Post-commit endpoint tests',
    '2': 'Run Student 2 endpoint and Multi-Agent tests',
    '3': 'Run Student 3 Resource Workflow tests',
    '4': 'Run Student 4 tests',
    '5': 'Run Student 5 Career Workflow tests',
}
STUDENT_OPTIONAL_STEPS = {
    '1': (
        'Run Student 1 tests',
        'Build Student 1 database image',
        'Build Student 1 backend image',
        'Build Student 1 frontend image',
    ),
    '2': ('Build Student 2 containers',),
    '3': (
        'Build Student 3 database',
        'Build Student 3 backend',
        'Build Student 3 frontend',
    ),
    '4': ('Build Student 4 Docker images',),
    '5': ('Build Student 5 Docker services',),
}
STUDENT_CLOUD_FIELDS = (
    'frontend_access', 'backend_api_access', 'database_connectivity', 'crud_validation',
    'persistence_validation',
)
STEPS = ('started', 'planner_completed', 'worker_completed', 'reviewer_completed',
         'human_review_pending', 'human_decision')


def _jsonl(path):
    rows, gaps = [], []
    try:
        text = Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return [], ['Evidence file missing or unreadable']
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError
            rows.append(row)
        except (ValueError, TypeError):
            gaps.append('Malformed JSONL record excluded')
    if not rows:
        gaps.append('No usable JSONL evidence')
    return rows, gaps


def _report(path):
    """Read a JSON object or one explicitly labelled Markdown evidence block."""
    try:
        text = Path(path).read_text(encoding='utf-8')
        if text.lstrip().startswith('{'):
            data = json.loads(text)
        else:
            blocks = re.findall(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
            data = next((json.loads(block) for block in blocks
                         if '"review_evidence"' in block), None)
        data = data.get('review_evidence', data) if isinstance(data, dict) else None
        if not isinstance(data, dict) or not data:
            raise ValueError
        return data, []
    except (OSError, UnicodeError, ValueError, TypeError):
        return {}, ['Missing, empty, malformed or unstructured report evidence']


def _completed(snapshot, audit):
    if not isinstance(snapshot.get('workflow_id'), str) or not snapshot['workflow_id']:
        return False
    human = snapshot.get('human_review')
    if snapshot.get('status') != 'completed' or not isinstance(human, dict):
        return False
    if (human.get('required') is not True or human.get('status') != 'completed'
            or human.get('decision') not in ('Accept', 'Partially Accept', 'Reject')):
        return False
    feature = snapshot.get('feature')
    if feature not in FEATURE_STUDENTS:
        return False
    for role in ('planner', 'worker', 'reviewer'):
        if not isinstance(snapshot.get(f'{role}_result'), dict) or not snapshot[f'{role}_result']:
            return False
    count = snapshot.get('evidence_count')
    references = snapshot['worker_result'].get('evidence_used')
    if (not isinstance(count, int) or isinstance(count, bool) or count < 0
            or not isinstance(references, list)):
        return False
    if count and not references:
        return False
    if any(not isinstance(ref, (str, int)) or isinstance(ref, bool) or not str(ref).strip()
           for ref in references):
        return False
    records = [row for row in audit if row.get('workflow_id') == snapshot.get('workflow_id')]
    if any(row.get('feature') not in (None, feature) for row in records):
        return False
    events = [row.get('event') for row in records]
    try:
        positions = [events.index(step) for step in STEPS]
        if positions != sorted(positions):
            return False
        selected = [records[position] for position in positions]
        timestamps = [datetime.fromisoformat(row['timestamp']) for row in selected]
        if timestamps != sorted(timestamps):
            return False
        for role, row in zip(('planner', 'worker', 'reviewer'), selected[1:4]):
            if row.get(f'{role}_status') != 'completed':
                return False
        final = selected[-1]
        return (final.get('human_decision') == human['decision']
                and final.get('human_review_status') == 'completed'
                and final.get('status') == 'completed')
    except (ValueError, KeyError, TypeError):
        return False


def multi_agent_review(history_path, audit_path, student='all'):
    if student not in ('all', *STUDENT_FEATURES):
        raise ValueError('student must be all or a student number from 1 to 5')
    history, history_gaps = _jsonl(history_path)
    audit, audit_gaps = _jsonl(audit_path)
    valid = [row for row in history if _completed(row, audit)]
    valid_by_student = {
        student_number: [
            row for row in valid
            if FEATURE_STUDENTS.get(row.get('feature')) == student_number
        ]
        for student_number in STUDENT_FEATURES
    }
    ids = {row.get('workflow_id') for row in history + audit if isinstance(row.get('workflow_id'), str)}
    complete_ids = {row['workflow_id'] for row in valid}
    failed_ids = {row['workflow_id'] for row in history + audit
                  if row.get('status') == 'failed' and isinstance(row.get('workflow_id'), str)} - complete_ids
    observations = [
        f'{len(complete_ids)} completed workflows have full agent results, attribution, human decision and ordered audit evidence.',
        f'{len(ids - complete_ids)} historical workflows lack a complete valid final snapshot.',
        f'{len(failed_ids)} failed attempts; {len(ids - complete_ids - failed_ids)} pending, incomplete or legacy attempts.',
    ]
    gaps = history_gaps + audit_gaps
    students_to_check = (student,) if student != 'all' else tuple(STUDENT_FEATURES)
    for student_number in students_to_check:
        count = len(valid_by_student[student_number])
        observations.append(f'Student {student_number}: {count} complete valid workflow(s).')
        if not count:
            gaps.append(
                f'Student {student_number} has no complete workflow with agent results, '
                'attribution, human decision and ordered audit evidence.'
            )
    observations.append(
        'Evidence reference presence is checked for all students; source records are not '
        'logged, so reference grounding cannot be independently rechecked.'
    )
    passed = not gaps and all(valid_by_student[number] for number in students_to_check)
    return observations, gaps, [], passed


def _student_evidence(data, student, label):
    students = data.get('students')
    if isinstance(students, dict):
        selected = students.get(student)
        if not isinstance(selected, dict):
            return {}, [f'{label} evidence missing for Student {student}']
        return selected, []
    if data.get('scope') in ('all', 'all students', 'repository'):
        return data, []
    declared_student = data.get('student')
    if declared_student in (student, int(student)):
        return data, []
    if student == '1' and declared_student is None:
        return data, []
    return {}, [f'{label} must include a students map for Student {student}']


def _validate_security_report(security, student):
    gaps, observations, warnings = [], [], []
    for control in ('ruff', 'detect_secrets', 'pip_audit_gate'):
        if security.get(control) != 'PASS':
            gaps.append(f'Student {student} security control missing or failed: {control}')
        else:
            observations.append(f'Student {student} security control passed: {control}')
    findings = security.get('unresolved_findings', [])
    if not isinstance(findings, list):
        gaps.append(f'Student {student} unresolved findings must be explicitly listed')
    elif findings:
        warnings.append(f'Student {student} has documented accepted vulnerabilities that remain unresolved')
        for finding in findings:
            if (not isinstance(finding, dict) or finding.get('resolved') is not False
                    or finding.get('accepted') is not True or not finding.get('advisory_id')
                    or not finding.get('rationale') or not finding.get('mitigation')):
                gaps.append(
                    f'Student {student} unresolved vulnerability acceptance is missing '
                    'or incorrectly labelled resolved'
                )
    if security.get('pip_audit_raw') not in ('PASS', 'FAIL'):
        gaps.append(f'Student {student} raw dependency audit status missing')
    elif security['pip_audit_raw'] == 'FAIL' and not findings:
        gaps.append(f'Student {student} raw vulnerability failure has no documented acceptance')
    return observations, gaps, warnings


def _validate_ci_report(ci, student):
    gaps, observations, warnings = [], [], []
    endpoints = ci.get('endpoint_tests')
    for endpoint in STUDENT_ENDPOINTS[student]:
        if not isinstance(endpoints, dict) or endpoints.get(endpoint) != 'PASS':
            gaps.append(f'Student {student} endpoint evidence missing or failed: {endpoint}')
    if ci.get('workflow_result') != 'succeeded' or not ci.get('run_url') or not ci.get('commit'):
        gaps.append(f'Student {student} successful CI run evidence missing')
    else:
        observations.append(
            f'Student {student} successful CI run is documented; this review does not independently query GitHub'
        )
    steps = ci.get('steps', {})
    required_step = STUDENT_TEST_STEPS[student]
    if not isinstance(steps, dict) or steps.get(required_step) != 'succeeded':
        gaps.append(f'Student {student} required CI test step missing or failed: {required_step}')
    for step in STUDENT_OPTIONAL_STEPS[student]:
        value = steps.get(step) if isinstance(steps, dict) else None
        if value is None:
            warnings.append(f'Optional Student {student} CI evidence not documented: {step}')
        elif value != 'succeeded':
            gaps.append(f'Student {student} CI step failed: {step}')
        else:
            observations.append(f'Student {student} CI step succeeded: {step}')
    return observations, gaps, warnings


def testing_review(security_path, ci_path, student='1'):
    if student not in ('all', *STUDENT_FEATURES):
        raise ValueError('student must be all or a student number from 1 to 5')
    security, security_gaps = _report(security_path)
    ci, ci_gaps = _report(ci_path)
    gaps = security_gaps + ci_gaps
    observations, warnings = [], []
    students_to_check = tuple(STUDENT_FEATURES) if student == 'all' else (student,)

    for student_number in students_to_check:
        student_security, student_security_gaps = _student_evidence(
            security, student_number, 'Security',
        )
        student_ci, student_ci_gaps = _student_evidence(ci, student_number, 'CI')
        gaps.extend(student_security_gaps + student_ci_gaps)
        if student_security:
            found, missing, accepted = _validate_security_report(
                student_security, student_number,
            )
            observations.extend(found)
            gaps.extend(missing)
            warnings.extend(accepted)
        if student_ci:
            found, missing, accepted = _validate_ci_report(student_ci, student_number)
            observations.extend(found)
            gaps.extend(missing)
            warnings.extend(accepted)
    return observations, gaps, warnings, not gaps


def cloud_review(report_path, student='1'):
    if student not in ('all', *STUDENT_FEATURES):
        raise ValueError('student must be all or a student number from 1 to 5')
    report, gaps = _report(report_path)
    observations = []
    students = report.get('students')
    students_to_check = tuple(STUDENT_FEATURES) if student == 'all' else (student,)
    for student_number in students_to_check:
        if isinstance(students, dict):
            student_report = students.get(student_number)
            if not isinstance(student_report, dict):
                gaps.append(f'Cloud evidence missing for Student {student_number}')
                continue
        elif student_number == '1':
            declared_student = report.get('student')
            if declared_student not in (None, '1', 1):
                gaps.append('Cloud evidence is not scoped to Student 1')
                continue
            student_report = report
        else:
            gaps.append(
                f'Cloud report must include a students map for Student {student_number}'
            )
            continue
        for field in STUDENT_CLOUD_FIELDS:
            if student_report.get(field) != 'PASS':
                gaps.append(f'Student {student_number} cloud validation missing or failed: {field}')
            else:
                observations.append(f'Student {student_number} cloud validation passed: {field}')
    if report.get('platform') not in ('Azure', 'AWS'):
        gaps.append('Azure or AWS platform evidence missing')
    if report.get('deployment_workflow_result') != 'succeeded' or not report.get('deployment_run_url'):
        gaps.append('Successful deployment workflow run evidence missing')
    if report.get('workflow_file') != '.github/workflows/cloud-deployment.yml':
        gaps.append('cloud-deployment.yml evidence missing')
    services = report.get('disabled_by_default')
    for service in ('ai_mode', 'mcp', 'rag', 'multi_agent'):
        if not isinstance(services, dict) or services.get(service) is not True:
            gaps.append('Service must be documented disabled by default: ' + service)
    if report.get('human_release_decision') != 'Accept' or not report.get('human_review_completed_at'):
        gaps.append('Final human approval evidence missing or release not accepted')
    return observations, gaps, [], not gaps


def execute_review(mode, paths, log_dir, output=None, student=None):
    if student is None:
        student = 'all' if mode == 'multi-agent-review' else '1'
    print('PLAN: Validate supplied evidence for ' + mode)
    print('ACT: Read local plain-text/JSON evidence without executing it')
    if mode == 'multi-agent-review':
        observations, gaps, warnings, valid = multi_agent_review(*paths, student=student)
    elif mode == 'testing-review':
        observations, gaps, warnings, valid = testing_review(*paths, student=student)
    else:
        observations, gaps, warnings, valid = cloud_review(*paths, student=student)
    status = 'FAIL' if not valid else ('PASS_WITH_WARNINGS' if gaps or warnings else 'PASS')
    result = {'timestamp': datetime.now(timezone.utc).isoformat(), 'review_mode': mode,
              'evidence_paths': [str(path) for path in paths],
              'evidence_reviewed': [str(path) for path in paths],
              'observations': observations, 'risks_or_gaps': gaps + warnings,
              'recommendations': ['Supply or correct missing evidence and rerun.'] if gaps else
                                 (['Track accepted risks and review before release/deployment.'] if warnings else ['Retain verified evidence for the assessment report.']),
              'validation_status': status}
    if mode in ('multi-agent-review', 'testing-review', 'cloud-review'):
        result['student_scope'] = student
    # Log only generated checks/paths, never copy source reports, requests or credentials.
    print('OBSERVE: ' + json.dumps(observations))
    print('REVIEW: ' + status)
    print('ADAPT: ' + ' '.join(result['recommendations']))
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (mode + '.jsonl')).open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(result) + '\n')
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return result