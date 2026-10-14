"""Deterministic local report reviews; inputs are data, never executable content."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re


MODES = ('multi-agent-review', 'testing-review', 'cloud-review')
ENDPOINTS = ('POST /api/multi-agent/course-workflow',
             'POST /api/multi-agent/course-workflow/<workflow_id>/decision')
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
    if snapshot.get('feature') != 'course_management':
        return False
    for role in ('planner', 'worker', 'reviewer'):
        if not isinstance(snapshot.get(f'{role}_result'), dict) or not snapshot[f'{role}_result']:
            return False
    count = snapshot.get('evidence_count')
    references = snapshot['worker_result'].get('evidence_used')
    if not isinstance(count, int) or isinstance(count, bool) or count < 0 or not isinstance(references, list):
        return False
    if count and not references:
        return False
    if any(not isinstance(ref, (str, int)) or isinstance(ref, bool) or not str(ref).strip() for ref in references):
        return False
    records = [row for row in audit if row.get('workflow_id') == snapshot.get('workflow_id')]
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


def multi_agent_review(history_path, audit_path):
    history, history_gaps = _jsonl(history_path)
    audit, audit_gaps = _jsonl(audit_path)
    valid = [row for row in history if _completed(row, audit)]
    ids = {row.get('workflow_id') for row in history + audit if isinstance(row.get('workflow_id'), str)}
    complete_ids = {row['workflow_id'] for row in valid}
    failed_ids = {row['workflow_id'] for row in history + audit
                  if row.get('status') == 'failed' and isinstance(row.get('workflow_id'), str)} - complete_ids
    observations = [f'{len(complete_ids)} completed workflows have full agent results, attribution, human decision and ordered audit evidence.',
                    f'{len(ids - complete_ids)} historical workflows lack a complete valid final snapshot.',
                    f'{len(failed_ids)} failed attempts; {len(ids - complete_ids - failed_ids)} pending, incomplete or legacy attempts.']
    gaps = history_gaps + audit_gaps
    if not valid:
        gaps.append('No complete valid workflow with a final human decision and matching audit trail')
    observations.append('Attribution presence is checked; raw course records are not logged, so reference grounding cannot be independently rechecked here.')
    return observations, gaps, [], bool(valid)


def testing_review(security_path, ci_path):
    security, gaps = _report(security_path)
    ci, ci_gaps = _report(ci_path)
    gaps += ci_gaps
    observations, warnings = [], []
    for control in ('ruff', 'detect_secrets', 'pip_audit_gate'):
        if security.get(control) != 'PASS':
            gaps.append(f'Security control missing or failed: {control}')
        else:
            observations.append(f'Security control passed: {control}')
    findings = security.get('unresolved_findings', [])
    if not isinstance(findings, list):
        gaps.append('Unresolved findings must be explicitly listed')
    elif findings:
        warnings.append('Documented accepted vulnerabilities remain unresolved')
        for finding in findings:
            if (not isinstance(finding, dict) or finding.get('resolved') is not False
                    or finding.get('accepted') is not True or not finding.get('advisory_id')
                    or not finding.get('rationale') or not finding.get('mitigation')):
                gaps.append('Unresolved vulnerability acceptance is missing or incorrectly labelled resolved')
    if security.get('pip_audit_raw') not in ('PASS', 'FAIL'):
        gaps.append('Raw dependency audit status missing')
    elif security['pip_audit_raw'] == 'FAIL' and not findings:
        gaps.append('Raw vulnerability failure has no documented acceptance')
    endpoints = ci.get('endpoint_tests')
    for endpoint in ENDPOINTS:
        if not isinstance(endpoints, dict) or endpoints.get(endpoint) != 'PASS':
            gaps.append('Required explicit endpoint evidence missing or failed: ' + endpoint)
    if ci.get('workflow_result') != 'succeeded' or not ci.get('run_url') or not ci.get('commit'):
        gaps.append('Successful GitHub Actions run evidence missing')
    else:
        observations.append('Successful CI run is documented; this review does not independently query GitHub')
    steps = ci.get('steps', {})
    if not isinstance(steps, dict) or steps.get('Post-commit endpoint tests') != 'succeeded':
        gaps.append('Explicit CI endpoint test step missing or failed')
    for step in ('Run Student 1 tests', 'Build Student 1 database image', 'Build Student 1 backend image', 'Build Student 1 frontend image'):
        value = steps.get(step) if isinstance(steps, dict) else None
        if value is None:
            warnings.append('Optional detailed CI evidence not documented: ' + step)
        elif value != 'succeeded':
            gaps.append('CI step failed: ' + step)
        else:
            observations.append('CI step succeeded: ' + step)
    return observations, gaps, warnings, not gaps


def cloud_review(report_path):
    report, gaps = _report(report_path)
    observations = []
    if report.get('platform') not in ('Azure', 'AWS'):
        gaps.append('Azure or AWS platform evidence missing')
    for field in ('frontend_access', 'backend_api_access', 'database_connectivity', 'crud_validation'):
        if report.get(field) != 'PASS':
            gaps.append('Cloud validation missing or failed: ' + field)
        else:
            observations.append('Cloud validation passed: ' + field)
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


def execute_review(mode, paths, log_dir, output=None):
    print('PLAN: Validate supplied evidence for ' + mode)
    print('ACT: Read local plain-text/JSON evidence without executing it')
    if mode == 'multi-agent-review':
        observations, gaps, warnings, valid = multi_agent_review(*paths)
    elif mode == 'testing-review':
        observations, gaps, warnings, valid = testing_review(*paths)
    else:
        observations, gaps, warnings, valid = cloud_review(*paths)
    status = 'FAIL' if not valid else ('PASS_WITH_WARNINGS' if gaps or warnings else 'PASS')
    result = {'timestamp': datetime.now(timezone.utc).isoformat(), 'review_mode': mode,
              'evidence_paths': [str(path) for path in paths],
              'evidence_reviewed': [str(path) for path in paths],
              'observations': observations, 'risks_or_gaps': gaps + warnings,
              'recommendations': ['Supply or correct missing evidence and rerun.'] if gaps else
                                 (['Track accepted risks and review before release/deployment.'] if warnings else ['Retain verified evidence for the assessment report.']),
              'validation_status': status}
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
