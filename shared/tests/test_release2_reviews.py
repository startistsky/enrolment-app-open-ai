import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

SHARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED))
import release2_reviews as reviews


def write(path, data):
    path.write_text(json.dumps(data))
    return path


def workflow_files(tmp_path, completed=True, failed=False, feature='course_management'):
    tmp_path.mkdir(parents=True, exist_ok=True)
    workflow_id = f'test-{feature}'
    snapshot = {'workflow_id': workflow_id, 'feature': feature,
                'status': 'completed' if completed else 'pending_human_review', 'evidence_count': 1,
                'planner_result': {'plan': 'Name course'},
                'worker_result': {'answer': 'Database Systems', 'evidence_used': ['COMP3311']},
                'reviewer_result': {'risk': 'low'},
                'human_review': {'required': True, 'status': 'completed' if completed else 'pending', 'decision': 'Accept'}}
    history = tmp_path / 'history.jsonl'
    history.write_text(json.dumps(snapshot) + '\n')
    if failed:
        with history.open('a') as stream:
            stream.write(json.dumps({'workflow_id': 'old', 'status': 'failed'})+'\n')
    audit = tmp_path / 'audit.jsonl'
    rows = [{'workflow_id': workflow_id, 'feature': feature,
             'event': event, 'timestamp': f'2026-10-07T00:00:0{i}+00:00',
             'planner_status': 'completed', 'worker_status': 'completed', 'reviewer_status': 'completed',
             'human_decision': 'Accept', 'human_review_status': 'completed', 'status': 'completed'}
            for i,event in enumerate(reviews.STEPS)]
    audit.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
    return history, audit, snapshot


def test_valid_multi_agent(tmp_path):
    history,audit,_ = workflow_files(tmp_path)
    result=reviews.execute_review(
        'multi-agent-review', (history, audit), tmp_path/'logs',
        tmp_path/'output.json', student='1',
    )
    assert result['validation_status']=='PASS'
    assert json.loads((tmp_path/'output.json').read_text())==result
    assert json.loads((tmp_path/'logs/multi-agent-review.jsonl').read_text())==result


def test_failed_history_does_not_block_valid(tmp_path):
    history,audit,_=workflow_files(tmp_path,failed=True)
    observations,gaps,_,valid=reviews.multi_agent_review(history,audit,student='1')
    assert valid and not gaps
    assert any('1 historical' in text for text in observations)


@pytest.mark.parametrize(('student', 'feature'), [
    ('1', 'course_management'),
    ('2', 'assignment_management'),
    ('3', 'resource_management'),
    ('4', 'event_management'),
    ('5', 'career_management'),
    ('5', 'careermanagement'),
])
def test_multi_agent_review_supports_all_students(tmp_path, student, feature):
    history, audit, _ = workflow_files(tmp_path, feature=feature)

    observations, gaps, _, passed = reviews.multi_agent_review(
        history, audit, student=student,
    )

    assert passed and not gaps
    assert any(f'Student {student}: 1 complete valid workflow' in item
               for item in observations)


def test_all_students_scope_requires_a_valid_workflow_for_each(tmp_path):
    paths = [
        workflow_files(tmp_path / student, feature=feature)[:2]
        for student, feature in (
            ('student1', 'course_management'),
            ('student2', 'assignment_management'),
            ('student3', 'resource_management'),
            ('student4', 'event_management'),
            ('student5', 'career_management'),
        )
    ]
    history = tmp_path / 'all-history.jsonl'
    audit = tmp_path / 'all-audit.jsonl'
    history.write_text(''.join(path[0].read_text() for path in paths))
    audit.write_text(''.join(path[1].read_text() for path in paths))

    observations, gaps, _, passed = reviews.multi_agent_review(history, audit)

    assert passed and not gaps
    assert all(any(f'Student {student}: 1 complete valid workflow' in item
                   for item in observations)
               for student in ('1', '2', '3', '4', '5'))


def test_all_students_scope_reports_students_without_workflow(tmp_path):
    history, audit, _ = workflow_files(tmp_path, feature='career_management')

    observations, gaps, _, passed = reviews.multi_agent_review(history, audit)

    assert not passed
    assert any('Student 1 has no complete workflow' in gap for gap in gaps)
    assert any('Student 5: 1 complete valid workflow' in item for item in observations)


def test_multi_agent_review_rejects_unknown_student(tmp_path):
    history, audit, _ = workflow_files(tmp_path)
    with pytest.raises(ValueError, match='student must be all'):
        reviews.multi_agent_review(history, audit, student='6')


def test_endpoint_inventory_covers_all_student_workflows_and_decisions():
    assert reviews.STUDENT_ENDPOINTS == {
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
    assert len(reviews.ENDPOINTS) == 10
    assert reviews.TESTING_ENDPOINTS == reviews.STUDENT_ENDPOINTS['1']


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


def security():
    return {'ruff':'PASS','detect_secrets':'PASS','pip_audit_raw':'PASS','pip_audit_gate':'PASS','unresolved_findings':[]}  # pragma: allowlist secret -- scanner status fixture, not a credential.


def ci():
    return {'commit':'verified-commit','run_url':'https://example.invalid/run','workflow_result':'succeeded',
            'endpoint_tests':{endpoint:'PASS' for endpoint in reviews.STUDENT_ENDPOINTS['1']},
            'steps':{step:'succeeded' for step in ('Post-commit endpoint tests','Run Student 1 tests',
                     'Build Student 1 database image','Build Student 1 backend image','Build Student 1 frontend image')}}


def student_security():
    data = security()
    return {
        student: {**data, 'student': student}
        for student in reviews.STUDENT_FEATURES
    }


def student_ci(student):
    return {
        'student': student,
        'commit': f'verified-student-{student}',
        'run_url': f'https://example.invalid/student-{student}',
        'workflow_result': 'succeeded',
        'endpoint_tests': {
            endpoint: 'PASS'
            for endpoint in reviews.STUDENT_ENDPOINTS[student]
        },
        'steps': {
            reviews.STUDENT_TEST_STEPS[student]: 'succeeded',
            **{step: 'succeeded' for step in reviews.STUDENT_OPTIONAL_STEPS[student]},
        },
    }


def test_testing_pass(tmp_path):
    result=reviews.execute_review('testing-review',(write(tmp_path/'security.json',security()),write(tmp_path/'ci.json',ci())),tmp_path/'logs')
    assert result['validation_status']=='PASS'


@pytest.mark.parametrize('student', ['1', '2', '3', '4', '5'])
def test_testing_review_supports_each_student(tmp_path, student):
    security_data = student_security()[student]
    ci_data = student_ci(student)

    observations, gaps, warnings, valid = reviews.testing_review(
        write(tmp_path/'security.json', security_data),
        write(tmp_path/'ci.json', ci_data),
        student=student,
    )

    assert valid and not gaps and not warnings
    assert any(f'Student {student} successful CI run' in item for item in observations)


def test_testing_review_all_students_requires_all_ci_and_security_evidence(tmp_path):
    security_report = write(
        tmp_path/'security.json',
        {'students': student_security()},
    )
    ci_report = write(
        tmp_path/'ci.json',
        {'students': {student: student_ci(student) for student in reviews.STUDENT_FEATURES}},
    )

    observations, gaps, warnings, valid = reviews.testing_review(
        security_report, ci_report, student='all',
    )

    assert valid and not gaps and not warnings
    assert all(any(f'Student {student} successful CI run' in item for item in observations)
               for student in reviews.STUDENT_FEATURES)


def test_testing_review_all_students_accepts_repository_scoped_security_evidence(tmp_path):
    security_report = {
        **security(),
        'scope': 'all students',
    }
    ci_report = {
        'students': {student: student_ci(student) for student in reviews.STUDENT_FEATURES},
    }

    _, gaps, warnings, valid = reviews.testing_review(
        write(tmp_path/'security.json', security_report),
        write(tmp_path/'ci.json', ci_report),
        student='all',
    )

    assert valid and not gaps and not warnings


def test_testing_review_all_students_fails_for_missing_student_evidence(tmp_path):
    security_report = write(
        tmp_path/'security.json',
        {'students': student_security()},
    )
    ci_students = {student: student_ci(student) for student in reviews.STUDENT_FEATURES}
    del ci_students['4']

    _, gaps, _, valid = reviews.testing_review(
        security_report,
        write(tmp_path/'ci.json', {'students': ci_students}),
        student='all',
    )

    assert not valid
    assert 'CI evidence missing for Student 4' in gaps


def test_testing_review_requires_selected_student_endpoints(tmp_path):
    ci_report = student_ci('3')
    ci_report['endpoint_tests'].pop(reviews.STUDENT_ENDPOINTS['3'][1])

    _, gaps, _, valid = reviews.testing_review(
        write(tmp_path/'security.json', student_security()['3']),
        write(tmp_path/'ci.json', ci_report),
        student='3',
    )

    assert not valid
    assert any(reviews.STUDENT_ENDPOINTS['3'][1] in gap for gap in gaps)


def test_accepted_vulnerability_stays_unresolved(tmp_path):
    data=security();data.update(pip_audit_raw='FAIL',unresolved_findings=[{'advisory_id':'GHSA-example','accepted':True,'resolved':False,'rationale':'No fix','mitigation':'Local embedded use'}])
    result=reviews.execute_review('testing-review',(write(tmp_path/'s.json',data),write(tmp_path/'c.json',ci())),tmp_path/'logs')
    assert result['validation_status']=='PASS_WITH_WARNINGS'
    assert any('remain unresolved' in text for text in result['risks_or_gaps'])


@pytest.mark.parametrize('change',['endpoint','failed-ci','hidden-findings','resolved-findings'])
def test_testing_missing_or_failed_evidence(tmp_path,change):
    s,c=security(),ci()
    if change=='endpoint':c['endpoint_tests'].pop(reviews.ENDPOINTS[0])
    if change=='failed-ci':c['workflow_result']='failed'
    if change=='hidden-findings':s['pip_audit_raw']='FAIL'
    if change=='resolved-findings':s.update(pip_audit_raw='FAIL',unresolved_findings=[{'resolved':True}])
    assert reviews.testing_review(write(tmp_path/'s.json',s),write(tmp_path/'c.json',c))[3] is False


def cloud():
    return {'platform':'AWS','frontend_access':'PASS','backend_api_access':'PASS','database_connectivity':'PASS',
            'crud_validation':'PASS','persistence_validation':'PASS',
            'deployment_workflow_result':'succeeded','deployment_run_url':'https://example.invalid/run',
            'workflow_file':'.github/workflows/cloud-deployment.yml',
            'disabled_by_default':{s:True for s in ('ai_mode','mcp','rag','multi_agent')},
            'human_release_decision':'Accept','human_review_completed_at':'2026-10-07T00:00:00Z'}


def test_future_cloud_fixture(tmp_path):
    assert reviews.cloud_review(write(tmp_path/'cloud.json',cloud()))[3] is True


def test_cloud_review_supports_each_student_and_all_scope(tmp_path):
    report = cloud()
    report['students'] = {
        student: {field: 'PASS' for field in reviews.STUDENT_CLOUD_FIELDS}
        for student in reviews.STUDENT_FEATURES
    }

    for student in reviews.STUDENT_FEATURES:
        _, gaps, _, valid = reviews.cloud_review(
            write(tmp_path/f'cloud-{student}.json', report),
            student=student,
        )
        assert valid and not gaps

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path/'cloud-all.json', report),
        student='all',
    )
    assert valid and not gaps


def test_cloud_review_all_scope_requires_each_student(tmp_path):
    report = cloud()
    report['students'] = {
        student: {field: 'PASS' for field in reviews.STUDENT_CLOUD_FIELDS}
        for student in reviews.STUDENT_FEATURES
    }
    del report['students']['2']

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path/'cloud.json', report),
        student='all',
    )

    assert not valid
    assert 'Cloud evidence missing for Student 2' in gaps


@pytest.mark.parametrize('change',['missing-controls','enabled-ai','failed-deployment','human-reject'])
def test_cloud_gaps(tmp_path,change):
    data=cloud()
    if change=='missing-controls':data.pop('database_connectivity')
    if change=='enabled-ai':data['disabled_by_default']['ai_mode']=False
    if change=='failed-deployment':data['deployment_workflow_result']='failed'
    if change=='human-reject':data['human_release_decision']='Reject'
    assert reviews.cloud_review(write(tmp_path/'cloud.json',data))[3] is False


def test_cloud_review_requires_persistence_validation(tmp_path):
    report = cloud()
    del report['persistence_validation']

    _, gaps, _, valid = reviews.cloud_review(
        write(tmp_path/'cloud.json', report),
        student='1',
    )

    assert not valid
    assert 'Student 1 cloud validation missing or failed: persistence_validation' in gaps


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


@pytest.mark.parametrize(
    ('mode', 'student_args', 'expected_student', 'expected_paths'),
    [
        ('testing-review', ['--student', '5'], '5', (
            'reports/testing-review-security-report.json',
            'reports/testing-review-ci-report.json',
        )),
        ('testing-review', ['--student', 'all'], 'all', (
            'reports/testing-review-security-report.json',
            'reports/testing-review-ci-report.json',
        )),
        ('cloud-review', ['--student', 'all'], 'all', (
            'reports/cloud-deployment-report.md',
        )),
        ('multi-agent-review', [], 'all', (
            'ai-services/multi-agent-server/workflow_history.jsonl',
            'ai-services/multi-agent-server/coordination_audit.jsonl',
        )),
    ],
)
def test_review_cli_student_scope_and_default_paths(
    monkeypatch, mode, student_args, expected_student, expected_paths,
):
    import agentic_loop

    monkeypatch.setattr(sys, 'argv', ['agentic_loop.py', '--mode', mode, *student_args])
    execute = Mock(return_value={'validation_status': 'PASS'})
    monkeypatch.setattr(reviews, 'execute_review', execute)

    assert agentic_loop.main() == 0
    assert execute.call_args.args[0:2] == (mode, expected_paths)
    assert execute.call_args.kwargs['student'] == expected_student


def test_testing_report_paths_fall_back_to_student_reports(tmp_path):
    import agentic_loop

    assert agentic_loop.testing_report_paths('4', tmp_path) == (
        str(tmp_path/'student-4-pre-commit-security-report.md'),
        str(tmp_path/'student-4-post-commit-ci-report.md'),
    )


def test_testing_report_paths_use_combined_reports_when_available(tmp_path):
    import agentic_loop

    (tmp_path/'testing-review-security-report.json').write_text('{}')
    (tmp_path/'testing-review-ci-report.json').write_text('{}')

    assert agentic_loop.testing_report_paths('4', tmp_path) == (
        str(tmp_path/'testing-review-security-report.json'),
        str(tmp_path/'testing-review-ci-report.json'),
    )
