"""Deterministic local report reviews; inputs are data, never executable content."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urlsplit

MODES = ('multi-agent-review', 'testing-review', 'cloud-review')
# Unqualified structured CI reports retain the existing Student 1 contract.
ENDPOINTS = ('POST /api/multi-agent/course-workflow',
             'POST /api/multi-agent/course-workflow/<workflow_id>/decision',
             )
WORKFLOW_FEATURES = (
    'course_management',
    'assignment_management',
    'resource_management',
    'event_management',
    'career_management',
)
FEATURE_ENDPOINTS = {
    'course_management': (
        'POST /api/multi-agent/course-workflow',
        'POST /api/multi-agent/course-workflow/<workflow_id>/decision',
    ),
    'assignment_management': (
        'POST /api/multi-agent/assignment-workflow',
        'POST /api/multi-agent/assignment-workflow/<workflow_id>/decision',
    ),
    'resource_management': (
        'POST /api/multi-agent/resource',
        'POST /api/multi-agent/<workflow_id>/decision',
    ),
    'event_management': (
        'POST /api/multi-agent/event-workflow',
        'POST /api/multi-agent/event-workflow/<workflow_id>/decision',
    ),
    'career_management': (
        'POST /api/workflow/career',
        'POST /api/workflow/<workflow_id>/decision',
    ),
}
FEATURE_CI_STEPS = {
    'course_management': ('Post-commit endpoint tests',),
    'assignment_management': (
        'Run Student 2 endpoint and Multi-Agent tests',
    ),
    'resource_management': (
        'Run Student 3 R2 Multi-Agent tests',
        'Run Student 3 Resource Workflow tests',
    ),
    'event_management': (
        'Release 2 Post-commit AI-assisted Unit Testing',
        'Test Multi-Agent Server',
        'Run Student 4 tests',
    ),
    'career_management': ('Run Student 5 Career Workflow tests',),
}
BONUS_SERVICE_URLS = {
    'ollama': 'http://ollama:11434/api/generate',
    'mcp': 'http://mcp-server:9001/mcp',
    'rag': 'http://rag-server:9101',
    'multi_agent': 'http://multi-agent-server:9201',
}
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


def _http_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme in ('http', 'https')
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
    )


def _valid_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return False
    return timestamp.tzinfo is not None and timestamp.utcoffset() is not None


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
    if feature not in WORKFLOW_FEATURES:
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
        if any(row.get('feature') != feature for row in selected):
            return False
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
    observations.append('Attribution presence is checked; raw source evidence is not logged, so reference grounding cannot be independently rechecked here.')
    return observations, gaps, [], bool(valid)


def testing_review(security_path, ci_path, feature_override=None):
    security, gaps = _report(security_path)
    ci, ci_gaps = _report(ci_path)
    gaps += ci_gaps
    observations, warnings = [], []
    scan_status = security.get('sensitive_data_scan')
    legacy_scan_status = security.get('detect' + '_secrets')
    if (scan_status is not None and legacy_scan_status is not None
            and scan_status != legacy_scan_status):
        gaps.append('Conflicting sensitive data scan status fields')
    scan_status = scan_status if scan_status is not None else legacy_scan_status
    for control, status in (
        ('ruff', security.get('ruff')),
        ('sensitive data scan', scan_status),
        ('pip_audit_gate', security.get('pip_audit_gate')),
    ):
        if status != 'PASS':
            gaps.append(f'Security control missing or failed: {control}')
        else:
            observations.append(f'Security control passed: {control}')
    findings = security.get('unresolved_findings')
    if not isinstance(findings, list):
        gaps.append('Unresolved findings must be explicitly listed')
        findings = []
    elif findings:
        warnings.append('Documented accepted vulnerabilities remain unresolved')
    raw_audit = security.get('pip_audit_raw')
    if raw_audit not in ('PASS', 'FAIL'):
        gaps.append('Raw dependency audit status missing')
    elif raw_audit == 'PASS' and findings:
        gaps.append('Raw dependency audit passed but unresolved findings are listed')
    elif raw_audit == 'FAIL' and not findings:
        gaps.append('Raw vulnerability failure has no documented findings')

    if findings and raw_audit == 'FAIL':
        observations.append('Raw dependency audit failed; listed findings remain unresolved')
    for finding in findings:
        if (not isinstance(finding, dict)
                or not isinstance(finding.get('advisory_id'), str)
                or not finding['advisory_id'].strip()
                or finding.get('resolved') is not False
                or finding.get('accepted') is not True
                or not isinstance(finding.get('rationale'), str)
                or not finding['rationale'].strip()
                or not isinstance(finding.get('mitigation'), str)
                or not finding['mitigation'].strip()):
            gaps.append('Unresolved vulnerability acceptance is missing or incorrectly labelled resolved')

    has_feature = feature_override is not None or 'feature' in ci
    feature = feature_override if feature_override is not None else ci.get('feature')
    if (feature_override is not None and 'feature' in ci
            and ci.get('feature') != feature_override):
        gaps.append('CLI feature selection conflicts with CI report feature')
    if not has_feature:
        endpoints_required = ENDPOINTS
        required_steps = ('Post-commit endpoint tests',)
    elif not isinstance(feature, str) or feature not in FEATURE_ENDPOINTS:
        endpoints_required = ()
        required_steps = ()
        gaps.append('Unsupported CI feature; expected one of: '
                    + ', '.join(WORKFLOW_FEATURES))
    else:
        endpoints_required = FEATURE_ENDPOINTS[feature]
        required_steps = FEATURE_CI_STEPS[feature]
        observations.append(f'Feature-specific CI profile selected: {feature}')

    endpoints = ci.get('endpoint_tests')
    for endpoint in endpoints_required:
        if not isinstance(endpoints, dict) or endpoints.get(endpoint) != 'PASS':
            gaps.append('Required explicit endpoint evidence missing or failed: ' + endpoint)
    if (ci.get('workflow_result') != 'succeeded'
            or not _http_url(ci.get('run_url'))
            or not isinstance(ci.get('commit'), str) or not ci['commit'].strip()):
        gaps.append('Successful GitHub Actions run evidence missing')
    else:
        observations.append('Successful CI run is documented; this review does not independently query GitHub')
    steps = ci.get('steps', {})
    if not isinstance(steps, dict):
        gaps.append('CI step results must be an explicit mapping')
    else:
        for step in required_steps:
            if steps.get(step) != 'succeeded':
                gaps.append('Required CI step missing or failed: ' + step)
            else:
                observations.append('CI step succeeded: ' + step)
        if not has_feature:
            for step in ('Run Student 1 tests', 'Build Student 1 database image',
                         'Build Student 1 backend image', 'Build Student 1 frontend image'):
                value = steps.get(step)
                if value is None:
                    warnings.append('Optional detailed CI evidence not documented: ' + step)
                elif value != 'succeeded':
                    gaps.append('CI step failed: ' + step)
                else:
                    observations.append('CI step succeeded: ' + step)
    return observations, gaps, warnings, not gaps


def cloud_review(report_path, profile_override=None):
    report, gaps = _report(report_path)
    observations = []
    profile = (
        profile_override
        if profile_override is not None
        else report.get('deployment_profile', 'baseline')
    )
    if (profile_override is not None and 'deployment_profile' in report
            and report.get('deployment_profile') != profile_override):
        gaps.append('CLI deployment profile conflicts with cloud report profile')
    if profile not in ('baseline', 'bonus'):
        gaps.append('Unsupported deployment profile; expected baseline or bonus')
        return observations, gaps, [], False
    observations.append(f'Deployment profile selected: {profile}')
    if report.get('platform') not in ('Azure', 'AWS'):
        gaps.append('Azure or AWS platform evidence missing')
    for field in ('frontend_access', 'backend_api_access', 'database_connectivity'):
        if report.get(field) != 'PASS':
            gaps.append('Cloud validation missing or failed: ' + field)
        else:
            observations.append('Cloud validation passed: ' + field)
    if (report.get('deployment_workflow_result') != 'succeeded'
            or not _http_url(report.get('deployment_run_url'))):
        gaps.append('Successful deployment workflow run evidence missing')

    warnings = []
    if profile == 'baseline':
        if report.get('workflow_file') != '.github/workflows/cloud-deployment.yml':
            gaps.append('cloud-deployment.yml evidence missing')
        for field in ('crud_validation', 'persistence_configuration',
                      'persistence_validation'):
            if report.get(field) != 'PASS':
                gaps.append('Baseline cloud validation missing or failed: ' + field)
            else:
                observations.append('Baseline cloud validation passed: ' + field)
        services = report.get('disabled_by_default')
        for service in ('ai_mode', 'mcp', 'rag', 'multi_agent'):
            if not isinstance(services, dict) or services.get(service) is not True:
                gaps.append('Service must be documented disabled by default: ' + service)
        decision = report.get('human_release_decision')
        completed_at = report.get('human_review_completed_at')
        if decision != 'Accept' or not completed_at:
            gaps.append('Final human approval evidence missing or release not accepted')
        elif not _valid_timestamp(completed_at):
            gaps.append('Final human approval timestamp is invalid')
    else:
        if report.get('platform') != 'Azure':
            gaps.append('The BONUS deployment profile requires Azure evidence')
        if report.get('workflow_file') != '.github/workflows/azure-bonus-deployment.yml':
            gaps.append('Azure BONUS deployment workflow evidence missing')

        services = report.get('bonus_services')
        for service in ('ollama', 'mcp', 'rag', 'multi_agent'):
            if not isinstance(services, dict) or services.get(service) != 'PASS':
                gaps.append('BONUS functional evidence missing or failed: ' + service)
            else:
                observations.append('BONUS service passed: ' + service)

        configuration = report.get('bonus_configuration')
        if not isinstance(configuration, dict):
            gaps.append('BONUS environment configuration evidence missing')
        else:
            if configuration.get('ai_services_enabled') is not True:
                gaps.append('BONUS AI_SERVICES_ENABLED must be explicitly true')
            if configuration.get('ollama_model') != 'qwen2.5:0.5b':
                gaps.append('BONUS Ollama model evidence must identify qwen2.5:0.5b')
            urls = configuration.get('service_urls')
            for service, expected_url in BONUS_SERVICE_URLS.items():
                value = urls.get(service) if isinstance(urls, dict) else None
                if not _http_url(value) or value != expected_url:
                    gaps.append('BONUS service URL missing or invalid: ' + service)

        for field in ('crud_validation', 'persistence_configuration',
                      'persistence_validation'):
            value = report.get(field)
            if value == 'FAIL' or value is False:
                gaps.append('BONUS core cloud validation failed: ' + field)
            elif value != 'PASS':
                warnings.append('BONUS report does not establish: ' + field)
            else:
                observations.append('BONUS core cloud validation passed: ' + field)
        decision = report.get('human_release_decision')
        completed_at = report.get('human_review_completed_at')
        if decision and decision != 'Accept':
            gaps.append('Human release review was not accepted')
        elif decision == 'Accept' and completed_at:
            if not _valid_timestamp(completed_at):
                gaps.append('Final human approval timestamp is invalid')
        else:
            warnings.append('BONUS deployment evidence does not establish final human release approval')
    return observations, gaps, warnings, not gaps


def execute_review(
    mode, paths, log_dir, output=None, feature=None, deployment_profile=None
):
    print('PLAN: Validate supplied evidence for ' + mode)
    print('ACT: Read local plain-text/JSON evidence without executing it')
    if mode == 'multi-agent-review':
        observations, gaps, warnings, valid = multi_agent_review(*paths)
    elif mode == 'testing-review':
        observations, gaps, warnings, valid = testing_review(
            *paths, feature_override=feature
        )
    else:
        observations, gaps, warnings, valid = cloud_review(
            *paths, profile_override=deployment_profile
        )
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