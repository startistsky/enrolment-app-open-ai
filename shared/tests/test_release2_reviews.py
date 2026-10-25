import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

SHARED = Path(__file__).resolve().parents[1]
REPOSITORY = SHARED.parent
sys.path.insert(0, str(SHARED))
import release2_reviews as reviews


def write(path, data):
    path.write_text(json.dumps(data))
    return path


def workflow_files(tmp_path, completed=True, failed=False, feature='course_management'):
    snapshot = {'workflow_id': 'test-workflow', 'feature': 'course_management',
                'status': 'completed' if completed else 'pending_human_review', 'evidence_count': 1,
                'planner_result': {'plan': 'Name course'},
                'worker_result': {'answer': 'Database Systems', 'evidence_used': ['COMP3311']},
                'reviewer_result': {'risk': 'low'},
                'human_review': {'required': True, 'status': 'completed' if completed else 'pending', 'decision': 'Accept'}}
    snapshot['feature'] = feature
    history = tmp_path / 'history.jsonl'
    history.write_text(json.dumps(snapshot) + '\n')
    if failed:
        with history.open('a') as stream:
            stream.write(json.dumps({'workflow_id': 'old', 'status': 'failed'})+'\n')
    audit = tmp_path / 'audit.jsonl'
    rows = [{'workflow_id': 'test-workflow', 'event': event, 'timestamp': f'2026-10-07T00:00:0{i}+00:00',
             'feature': feature,
             'planner_status': 'completed', 'worker_status': 'completed', 'reviewer_status': 'completed',
             'human_decision': 'Accept', 'human_review_status': 'completed', 'status': 'completed'}
            for i,event in enumerate(reviews.STEPS)]
    audit.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    return history, audit, snapshot


def test_valid_multi_agent(tmp_path):
    history,audit,_ = workflow_files(tmp_path)
    result=reviews.execute_review('multi-agent-review',(history,audit),tmp_path/'logs',tmp_path/'output.json')
    assert result['validation_status']=='PASS'
    assert json.loads((tmp_path/'output.json').read_text())==result
    assert json.loads((tmp_path/'logs/multi-agent-review.jsonl').read_text())==result


@pytest.mark.parametrize('feature', reviews.WORKFLOW_FEATURES)
def test_valid_multi_agent_for_each_student_feature(tmp_path, feature):
    history, audit, _ = workflow_files(tmp_path, feature=feature)

    observations, gaps, _, valid = reviews.multi_agent_review(history, audit)

    assert valid
    assert not gaps
    assert any('1 completed workflows' in text for text in observations)


def test_failed_history_does_not_block_valid(tmp_path):
    history,audit,_=workflow_files(tmp_path,failed=True)
    observations,gaps,_,valid=reviews.multi_agent_review(history,audit)
    assert valid and not gaps
    assert any('1 historical' in text for text in observations)


@pytest.mark.parametrize('change',['pending','decision','attribution','order','malformed','unexpected'])
def test_invalid_multi_agent(tmp_path,change):
    history,audit,snapshot=workflow_files(tmp_path,completed=change!='pending')
    if change=='decision': snapshot['human_review'].pop('decision')
    if change=='attribution': snapshot['worker_result']['evidence_used']=[]
    if change=='unexpected': snapshot['workflow_id']=[]
    if change in ('decision','attribution','unexpected'):history.write_text(json.dumps(snapshot)+'\n')
    if change=='order':audit.write_text('\n'.join(reversed(audit.read_text().splitlines())))
    if change=='malformed':history.write_text('broken\n[]\n')
    assert reviews.multi_agent_review(history,audit)[3] is False


def test_multi_agent_rejects_unknown_feature(tmp_path):
    history, audit, snapshot = workflow_files(tmp_path, feature='unknown')
    history.write_text(json.dumps(snapshot) + '\n')

    assert reviews.multi_agent_review(history, audit)[3] is False


def test_multi_agent_rejects_audit_feature_mismatch(tmp_path):
    history, audit, _ = workflow_files(tmp_path, feature='resource_management')
    rows = [json.loads(line) for line in audit.read_text().splitlines()]
    rows[2]['feature'] = 'course_management'
    audit.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')

    assert reviews.multi_agent_review(history, audit)[3] is False


def security():
    return {'ruff':'PASS','sensitive_data_scan':'PASS','pip_audit_raw':'PASS','pip_audit_gate':'PASS','unresolved_findings':[]}


def ci():
    return {'commit':'verified-commit','run_url':'https://example.invalid/run','workflow_result':'succeeded',
            'endpoint_tests':{endpoint:'PASS' for endpoint in reviews.ENDPOINTS},
            'steps':{step:'succeeded' for step in ('Post-commit endpoint tests','Run Student 1 tests',
                     'Build Student 1 database image','Build Student 1 backend image','Build Student 1 frontend image')}}


def feature_ci(feature):
    steps = {
        'course_management': ('Post-commit endpoint tests',),
        'assignment_management': ('Run Student 2 endpoint and Multi-Agent tests',),
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
    }[feature]
    return {
        'feature': feature,
        'commit': 'verified-commit',
        'run_url': 'https://example.invalid/run',
        'workflow_result': 'succeeded',
        'endpoint_tests': {
            endpoint: 'PASS'
            for endpoint in reviews.FEATURE_ENDPOINTS[feature]
        },
        'steps': {step: 'succeeded' for step in steps},
    }


def test_testing_pass(tmp_path):
    result=reviews.execute_review('testing-review',(write(tmp_path/'security.json',security()),write(tmp_path/'ci.json',ci())),tmp_path/'logs')
    assert result['validation_status']=='PASS'


def test_testing_review_accepts_legacy_scan_field(tmp_path):
    evidence = security()
    legacy_field = ''.join(('detect', '_secrets'))
    evidence[legacy_field] = evidence.pop('sensitive_data_scan')

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', evidence),
        write(tmp_path / 'ci.json', ci()),
    )

    assert valid
    assert not gaps


def test_testing_review_rejects_conflicting_sensitive_data_scan_fields(tmp_path):
    evidence = security()
    legacy_field = ''.join(('detect', '_secrets'))
    evidence[legacy_field] = 'FAIL'

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', evidence),
        write(tmp_path / 'ci.json', ci()),
    )

    assert not valid
    assert 'Conflicting sensitive data scan status fields' in gaps


def test_existing_student1_reports_remain_compatible():
    _, gaps, _, valid = reviews.testing_review(
        REPOSITORY / 'reports/student-1-pre-commit-security-report.md',
        REPOSITORY / 'reports/student-1-post-commit-ci-report.md',
    )

    assert valid
    assert not gaps


@pytest.mark.parametrize('feature', reviews.WORKFLOW_FEATURES)
def test_testing_review_uses_actual_feature_routes_and_ci_steps(tmp_path, feature):
    result = reviews.execute_review(
        'testing-review',
        (
            write(tmp_path / 'security.json', security()),
            write(tmp_path / 'ci.json', feature_ci(feature)),
        ),
        tmp_path / 'logs',
    )

    assert result['validation_status'] == 'PASS'
    assert any(
        f'Feature-specific CI profile selected: {feature}' in item
        for item in result['observations']
    )


@pytest.mark.parametrize(
    ('feature', 'endpoint'),
    [
        ('course_management', 'POST /api/multi-agent/course-workflow'),
        ('assignment_management', 'POST /api/multi-agent/assignment-workflow'),
        ('resource_management', 'POST /api/multi-agent/resource'),
        ('event_management', 'POST /api/multi-agent/event-workflow'),
        ('career_management', 'POST /api/workflow/career'),
    ],
)
def test_feature_endpoints_match_backend_routes(feature, endpoint):
    assert endpoint in reviews.FEATURE_ENDPOINTS[feature]


def test_feature_testing_review_rejects_missing_endpoint_or_step(tmp_path):
    evidence = feature_ci('resource_management')
    evidence['endpoint_tests'].pop('POST /api/multi-agent/resource')
    evidence['steps'].pop('Run Student 3 Resource Workflow tests')

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', security()),
        write(tmp_path / 'ci.json', evidence),
    )

    assert not valid
    assert any('POST /api/multi-agent/resource' in gap for gap in gaps)
    assert any('Run Student 3 Resource Workflow tests' in gap for gap in gaps)


def test_testing_review_rejects_conflicting_cli_feature(tmp_path):
    evidence = feature_ci('resource_management')
    evidence['feature'] = 'course_management'

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', security()),
        write(tmp_path / 'ci.json', evidence),
        feature_override='resource_management',
    )

    assert not valid
    assert 'CLI feature selection conflicts with CI report feature' in gaps


def test_testing_review_rejects_unknown_feature(tmp_path):
    evidence = feature_ci('resource_management')
    evidence['feature'] = []

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', security()),
        write(tmp_path / 'ci.json', evidence),
    )

    assert not valid
    assert any('Unsupported CI feature' in gap for gap in gaps)


def test_accepted_vulnerability_stays_unresolved(tmp_path):
    data=security();data.update(pip_audit_raw='FAIL',unresolved_findings=[{'advisory_id':'GHSA-example','accepted':True,'resolved':False,'rationale':'No fix','mitigation':'Local embedded use'}])
    result=reviews.execute_review('testing-review',(write(tmp_path/'s.json',data),write(tmp_path/'c.json',ci())),tmp_path/'logs')
    assert result['validation_status']=='PASS_WITH_WARNINGS'
    assert any('remain unresolved' in text for text in result['risks_or_gaps'])


@pytest.mark.parametrize(
    ('raw_status', 'findings', 'expected_gap'),
    [
        (
            'PASS',
            [{
                'advisory_id': 'GHSA-example',
                'accepted': True,
                'resolved': False,
                'rationale': 'No fix',
                'mitigation': 'Embedded use',
            }],
            'Raw dependency audit passed but unresolved findings are listed',
        ),
        ('FAIL', [], 'Raw vulnerability failure has no documented findings'),
    ],
)
def test_testing_review_rejects_inconsistent_raw_audit_findings(
    tmp_path, raw_status, findings, expected_gap
):
    evidence = security()
    evidence.update(pip_audit_raw=raw_status, unresolved_findings=findings)

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', evidence),
        write(tmp_path / 'ci.json', ci()),
    )

    assert not valid
    assert expected_gap in gaps


def test_testing_review_requires_explicit_findings_array(tmp_path):
    evidence = security()
    evidence.pop('unresolved_findings')

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', evidence),
        write(tmp_path / 'ci.json', ci()),
    )

    assert not valid
    assert 'Unresolved findings must be explicitly listed' in gaps


def test_testing_review_requires_complete_accepted_findings(tmp_path):
    evidence = security()
    evidence.update(
        pip_audit_raw='FAIL',
        unresolved_findings=[{
            'advisory_id': 'GHSA-example',
            'accepted': False,
            'resolved': False,
            'rationale': 'No fix',
            'mitigation': 'Embedded use',
        }],
    )

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path / 'security.json', evidence),
        write(tmp_path / 'ci.json', ci()),
    )

    assert not valid
    assert any('acceptance is missing' in gap for gap in gaps)


@pytest.mark.parametrize(
    'change',
    ['endpoint', 'failed-ci', 'hidden-findings', 'resolved-findings', 'invalid-run-url'],
)
def test_testing_missing_or_failed_evidence(tmp_path,change):
    s,c=security(),ci()
    if change=='endpoint':c['endpoint_tests'].pop(reviews.ENDPOINTS[0])
    if change=='failed-ci':c['workflow_result']='failed'
    if change=='hidden-findings':s['pip_audit_raw']='FAIL'
    if change=='resolved-findings':s.update(pip_audit_raw='FAIL',unresolved_findings=[{'resolved':True}])
    if change=='invalid-run-url':c['run_url']='not-a-url'
    assert reviews.testing_review(write(tmp_path/'s.json',s),write(tmp_path/'c.json',c))[3] is False


def cloud():
    return {'platform':'AWS','frontend_access':'PASS','backend_api_access':'PASS','database_connectivity':'PASS',
            'crud_validation':'PASS','deployment_workflow_result':'succeeded','deployment_run_url':'https://example.invalid/run',
            'workflow_file':'.github/workflows/cloud-deployment.yml',
            'persistence_configuration':'PASS','persistence_validation':'PASS',
            'disabled_by_default':{s:True for s in ('ai_mode','mcp','rag','multi_agent')},
            'human_release_decision':'Accept','human_review_completed_at':'2026-10-07T00:00:00Z'}


def bonus_cloud():
    return {
        'deployment_profile': 'bonus',
        'platform': 'Azure',
        'frontend_access': 'PASS',
        'backend_api_access': 'PASS',
        'database_connectivity': 'PASS',
        'deployment_workflow_result': 'succeeded',
        'deployment_run_url': 'https://example.invalid/bonus-run',
        'workflow_file': '.github/workflows/azure-bonus-deployment.yml',
        'bonus_services': {
            service: 'PASS'
            for service in ('ollama', 'mcp', 'rag', 'multi_agent')
        },
        'bonus_configuration': {
            'ai_services_enabled': True,
            'ollama_model': 'qwen2.5:0.5b',
            'service_urls': {
                'ollama': 'http://ollama:11434/api/generate',
                'mcp': 'http://mcp-server:9001/mcp',
                'rag': 'http://rag-server:9101',
                'multi_agent': 'http://multi-agent-server:9201',
            },
        },
    }


def test_future_cloud_fixture(tmp_path):
    assert reviews.cloud_review(write(tmp_path/'cloud.json',cloud()))[3] is True


def test_bonus_cloud_profile_allows_enabled_ai_and_reports_gaps_as_warnings(tmp_path):
    observations, gaps, warnings, valid = reviews.cloud_review(
        write(tmp_path / 'bonus.json', bonus_cloud())
    )

    assert valid
    assert not gaps
    assert any('BONUS service passed: multi_agent' in item for item in observations)
    assert any('does not establish: persistence_validation' in item for item in warnings)
    assert any('final human release approval' in item for item in warnings)


def test_cloud_review_rejects_conflicting_cli_profile(tmp_path):
    report = cloud()
    report['deployment_profile'] = 'baseline'
    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path / 'cloud.json', report),
        profile_override='bonus',
    )

    assert not valid
    assert 'CLI deployment profile conflicts with cloud report profile' in gaps


@pytest.mark.parametrize(
    ('change', 'expected_gap'),
    [
        ('missing-service', 'BONUS functional evidence missing or failed: rag'),
        ('wrong-model', 'BONUS Ollama model evidence must identify qwen2.5:0.5b'),
        ('missing-url', 'BONUS service URL missing or invalid: multi_agent'),
        ('credentials-in-url', 'BONUS service URL missing or invalid: ollama'),
        ('wrong-url', 'BONUS service URL missing or invalid: rag'),
        ('disabled', 'BONUS AI_SERVICES_ENABLED must be explicitly true'),
        ('wrong-workflow', 'Azure BONUS deployment workflow evidence missing'),
    ],
)
def test_bonus_cloud_profile_rejects_missing_or_invalid_evidence(
    tmp_path, change, expected_gap
):
    report = bonus_cloud()
    if change == 'missing-service':
        report['bonus_services'].pop('rag')
    elif change == 'wrong-model':
        report['bonus_configuration']['ollama_model'] = 'other-model'
    elif change == 'missing-url':
        report['bonus_configuration']['service_urls'].pop('multi_agent')
    elif change == 'credentials-in-url':
        report['bonus_configuration']['service_urls']['ollama'] = (
            'http://user@ollama:11434/api/generate'
        )
    elif change == 'wrong-url':
        report['bonus_configuration']['service_urls']['rag'] = 'http://wrong-service:9101'
    elif change == 'disabled':
        report['bonus_configuration']['ai_services_enabled'] = False
    elif change == 'wrong-workflow':
        report['workflow_file'] = '.github/workflows/cloud-deployment.yml'

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path / 'bonus.json', report)
    )

    assert not valid
    assert expected_gap in gaps


@pytest.mark.parametrize('change',['missing-controls','enabled-ai','failed-deployment','human-reject'])
def test_cloud_gaps(tmp_path,change):
    data=cloud()
    if change=='missing-controls':data.pop('database_connectivity')
    if change=='enabled-ai':data['disabled_by_default']['ai_mode']=False
    if change=='failed-deployment':data['deployment_workflow_result']='failed'
    if change=='human-reject':data['human_release_decision']='Reject'
    assert reviews.cloud_review(write(tmp_path/'cloud.json',data))[3] is False


def test_baseline_cloud_requires_persistence_evidence(tmp_path):
    report = cloud()
    report.pop('persistence_validation')

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path / 'cloud.json', report)
    )

    assert not valid
    assert 'Baseline cloud validation missing or failed: persistence_validation' in gaps


@pytest.mark.parametrize(
    ('timestamp', 'expected_valid'),
    [
        ('2026-10-07T00:00:00Z', True),
        (None, False),
        ('not-a-timestamp', False),
        ('2026-10-07T00:00:00', False),
    ],
)
def test_baseline_cloud_requires_valid_release_approval_timestamp(
    tmp_path, timestamp, expected_valid
):
    report = cloud()
    if timestamp is None:
        report.pop('human_review_completed_at')
    else:
        report['human_review_completed_at'] = timestamp

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path / 'cloud.json', report)
    )

    assert valid is expected_valid
    if not expected_valid:
        assert any(
            'human approval' in gap.lower() or 'timestamp is invalid' in gap.lower()
            for gap in gaps
        )


@pytest.mark.parametrize(
    ('decision', 'timestamp', 'expected_gap', 'expected_warning'),
    [
        ('Accept', '2026-10-07T00:00:00Z', False, False),
        (None, None, False, True),
        (None, 'not-a-timestamp', False, True),
        ('Accept', 'not-a-timestamp', True, False),
    ],
)
def test_bonus_cloud_distinguishes_missing_and_invalid_release_timestamp(
    tmp_path, decision, timestamp, expected_gap, expected_warning
):
    report = bonus_cloud()
    if decision is not None:
        report['human_release_decision'] = decision
    if timestamp is not None:
        report['human_review_completed_at'] = timestamp

    _, gaps, warnings, valid = reviews.cloud_review(
        write(tmp_path / 'bonus.json', report)
    )

    assert valid is not expected_gap
    assert ('Final human approval timestamp is invalid' in gaps) is expected_gap
    assert any('final human release approval' in warning for warning in warnings) is (
        expected_warning
    )


def test_cloud_review_rejects_invalid_deployment_run_url(tmp_path):
    report = cloud()
    report['deployment_run_url'] = 'not-a-url'

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path / 'cloud.json', report)
    )

    assert not valid
    assert 'Successful deployment workflow run evidence missing' in gaps


def test_missing_files_fail(tmp_path):
    missing=tmp_path/'missing'
    assert reviews.multi_agent_review(missing,missing)[3] is False
    assert reviews.testing_review(missing,missing)[3] is False
    assert reviews.cloud_review(missing)[3] is False


def test_release1_all_still_only_runs_mcp_rag(monkeypatch):
    import agentic_loop
    monkeypatch.setattr(sys,'argv',['agentic_loop.py','--mode','all'])
    async def mcp():return True
    monkeypatch.setattr(agentic_loop,'validate_mcp',mcp)
    rag=Mock(return_value=True);monkeypatch.setattr(agentic_loop,'validate_rag',rag)
    assert agentic_loop.main()==0
    rag.assert_called_once()


def test_multi_agent_cli_does_not_require_release1_service_dependencies(
    tmp_path, monkeypatch
):
    import builtins

    history, audit, _ = workflow_files(tmp_path)
    spec = importlib.util.spec_from_file_location(
        'review_cli_without_service_dependencies',
        SHARED / 'agentic_loop.py',
    )
    cli = importlib.util.module_from_spec(spec)
    original_import = builtins.__import__

    def reject_optional_dependencies(name, *args, **kwargs):
        if name == 'requests' or name == 'mcp' or name.startswith('mcp.'):
            raise ModuleNotFoundError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', reject_optional_dependencies)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'agentic_loop.py',
            '--mode',
            'multi-agent-review',
            '--workflow-history',
            str(history),
            '--coordination-audit',
            str(audit),
            '--feature',
            'resource_management',
            '--log-dir',
            str(tmp_path / 'logs'),
        ],
    )
    spec.loader.exec_module(cli)

    assert cli.main() == 0
