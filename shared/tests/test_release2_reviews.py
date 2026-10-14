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


def workflow_files(tmp_path, completed=True, failed=False):
    snapshot = {'workflow_id': 'test-workflow', 'feature': 'course_management',
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
    rows = [{'workflow_id': 'test-workflow', 'event': event, 'timestamp': f'2026-10-07T00:00:0{i}+00:00',
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


def security():
    return {'ruff':'PASS','detect_secrets':'PASS','pip_audit_raw':'PASS','pip_audit_gate':'PASS','unresolved_findings':[]}  # pragma: allowlist secret -- scanner status fixture, not a credential.


def ci():
    return {'commit':'verified-commit','run_url':'https://example.invalid/run','workflow_result':'succeeded',
            'endpoint_tests':{endpoint:'PASS' for endpoint in reviews.ENDPOINTS},
            'steps':{step:'succeeded' for step in ('Post-commit endpoint tests','Run Student 1 tests',
                     'Build Student 1 database image','Build Student 1 backend image','Build Student 1 frontend image')}}


def test_testing_pass(tmp_path):
    result=reviews.execute_review('testing-review',(write(tmp_path/'security.json',security()),write(tmp_path/'ci.json',ci())),tmp_path/'logs')
    assert result['validation_status']=='PASS'


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
            'crud_validation':'PASS','deployment_workflow_result':'succeeded','deployment_run_url':'https://example.invalid/run',
            'workflow_file':'.github/workflows/cloud-deployment.yml',
            'disabled_by_default':{s:True for s in ('ai_mode','mcp','rag','multi_agent')},
            'human_release_decision':'Accept','human_review_completed_at':'2026-10-07T00:00:00Z'}


def test_future_cloud_fixture(tmp_path):
    assert reviews.cloud_review(write(tmp_path/'cloud.json',cloud()))[3] is True


@pytest.mark.parametrize('change',['missing-controls','enabled-ai','failed-deployment','human-reject'])
def test_cloud_gaps(tmp_path,change):
    data=cloud()
    if change=='missing-controls':data.pop('database_connectivity')
    if change=='enabled-ai':data['disabled_by_default']['ai_mode']=False
    if change=='failed-deployment':data['deployment_workflow_result']='failed'
    if change=='human-reject':data['human_release_decision']='Reject'
    assert reviews.cloud_review(write(tmp_path/'cloud.json',data))[3] is False


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
