import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests


SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
spec = importlib.util.spec_from_file_location('multi_agent_app', SERVER / 'app.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
from agents import planner_agent, worker_agent, reviewer_agent
from llm_client import ModelError
import llm_client


@pytest.fixture
def setup(tmp_path, monkeypatch):
    calls = []
    outputs = {
        'planner': {'plan': 'Summarise records', 'evidence_required': ['course_code']},
        'worker': {'answer': 'COMP1001', 'evidence_used': ['COMP1001'], 'missing_evidence': []},
        'reviewer': {'risk': 'low', 'unsupported_claims': [], 'correction': '', 'recommendation': 'Human review required'},
    }
    def stage(role):
        def run(*args):
            assert calls == ['planner', 'worker', 'reviewer'][:len(calls)]
            if role != 'planner':
                assert args[2] == outputs['planner']
            if role == 'reviewer':
                assert args[3] == outputs['worker']
            calls.append(role)
            return outputs[role]
        return run
    for role, agent in [('planner', planner_agent), ('worker', worker_agent), ('reviewer', reviewer_agent)]:
        monkeypatch.setattr(agent, 'run', stage(role))
    app = server.create_app(tmp_path / 'history.jsonl', tmp_path / 'audit.jsonl')
    app.config['TESTING'] = True
    return app.test_client(), app.extensions['coordinator'], calls, tmp_path


def payload():
    return {'user_request': 'Summarise', 'feature': 'course_management',
            'evidence': [{'course_code': 'COMP1001'}]}


def test_health(setup):
    assert setup[0].get('/health').get_json()['status'] == 'ok'


def test_order_pending_and_audit(setup):
    client, coordinator, calls, directory = setup
    response = client.post('/workflow/course', json=payload())
    assert response.status_code == 200
    body = response.get_json()
    assert calls == ['planner', 'worker', 'reviewer']
    assert body['human_review']['status'] == 'pending'
    assert 'decision' not in body['human_review']
    assert client.get('/workflow/status').get_json()['workflows'][0]['workflow_id'] == body['workflow_id']
    rows = [json.loads(line) for line in (directory / 'audit.jsonl').read_text().splitlines()]
    assert [r['event'] for r in rows] == ['started', 'planner_completed', 'worker_completed', 'reviewer_completed', 'human_review_pending']
    assert rows[-1]['evidence_count'] == 1
    assert rows[-1]['reviewer_status'] == 'completed'
    assert 'COMP1001' not in (directory / 'audit.jsonl').read_text()
    snapshots = [json.loads(line) for line in (directory / 'history.jsonl').read_text().splitlines()]
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot['user_request'] == 'Summarise'
    assert snapshot['status'] == 'pending_human_review'
    assert snapshot['timestamp']
    for key in ('workflow_id', 'feature', 'evidence_count', 'planner_result', 'worker_result', 'reviewer_result', 'human_review'):
        assert snapshot[key] == body[key]
    assert 'event' not in snapshot



@pytest.mark.parametrize('decision', server.DECISIONS)
def test_human_decision(setup, decision):
    client, _, _, directory = setup
    workflow_id = client.post('/workflow/course', json=payload()).get_json()['workflow_id']
    response = client.post(f'/workflow/{workflow_id}/decision', json={'decision': decision, 'reason': 'Checked personally'})
    assert response.status_code == 200
    assert response.get_json()['human_review']['decision'] == decision
    assert response.get_json()['human_review']['reason'] == 'Checked personally'
    row = json.loads((directory / 'audit.jsonl').read_text().splitlines()[-1])
    assert row['human_decision'] == decision
    assert row['human_review_status'] == 'completed'
    assert 'Checked personally' not in (directory / 'audit.jsonl').read_text()
    snapshots = [json.loads(line) for line in (directory / 'history.jsonl').read_text().splitlines()]
    assert len(snapshots) == 2
    assert snapshots[0]['human_review']['status'] == 'pending'
    assert snapshots[-1]['status'] == 'completed'
    assert snapshots[-1]['human_review'] == response.get_json()['human_review']
    for role in ('planner', 'worker', 'reviewer'):
        assert snapshots[-1][f'{role}_result'] == response.get_json()[f'{role}_result']
    assert client.post(f'/workflow/{workflow_id}/decision', json={'decision': 'Reject'}).status_code == 409


@pytest.mark.parametrize('body', [{'decision': 'approve'}, {'decision': ['Accept']}, {'decision': 'Accept', 'reason': 3}, {}])
def test_invalid_decision(setup, body):
    assert setup[0].post('/workflow/unknown/decision', json=body).status_code == 400


def test_unknown_workflow(setup):
    assert setup[0].post('/workflow/unknown/decision', json={'decision': 'Accept'}).status_code == 404


@pytest.mark.parametrize('body', [{}, {'user_request': ' '}, {**payload(), 'feature': 'other'}, {**payload(), 'evidence': [3]}])
def test_invalid_input(setup, body):
    assert setup[0].post('/workflow/course', json=body).status_code == 400
    assert setup[2] == []


@pytest.mark.parametrize('role, expected_calls', [('planner', []), ('worker', ['planner']), ('reviewer', ['planner', 'worker'])])
def test_model_failure_stops_sequence(setup, monkeypatch, role, expected_calls):
    monkeypatch.setattr({'planner': planner_agent, 'worker': worker_agent, 'reviewer': reviewer_agent}[role], 'run', Mock(side_effect=ModelError('Ollama unavailable', 503)))
    response = setup[0].post('/workflow/course', json=payload())
    assert response.status_code == 503
    body = response.get_json()
    assert body['failed_agent'] == role
    assert setup[2] == expected_calls
    assert body['human_review']['status'] == 'unavailable'
    assert setup[0].post(f"/workflow/{body['workflow_id']}/decision", json={'decision': 'Accept'}).status_code == 409


def test_early_decision_blocked(setup):
    coordinator = setup[1]
    coordinator.workflows['running'] = {'status': 'running', 'reviewer_status': 'pending'}
    assert setup[0].post('/workflow/running/decision', json={'decision': 'Accept'}).status_code == 409


def test_empty_evidence(setup):
    assert setup[0].post('/workflow/course', json={**payload(), 'evidence': []}).status_code == 200


@pytest.mark.parametrize('reply', [[], {}, {'response': 'not JSON'}, {'response': '{}'}])
def test_invalid_model_output(monkeypatch, reply):
    monkeypatch.setattr(llm_client.requests, 'post', Mock(return_value=Mock(ok=True, json=Mock(return_value=reply))))
    with pytest.raises(ModelError):
        llm_client.generate('planner', {}, {'plan': str, 'evidence_required': list})


def test_model_configuration(monkeypatch):
    monkeypatch.setenv('OLLAMA_REVIEW_MODEL', 'custom-reviewer')
    monkeypatch.setenv('OLLAMA_URL', 'http://example.invalid/api/generate')
    post = Mock(return_value=Mock(ok=True, json=Mock(return_value={'response': '{"risk": "low"}'})))
    monkeypatch.setattr(llm_client.requests, 'post', post)
    assert llm_client.generate('reviewer', {}, {'risk': str}) == {'risk': 'low'}
    assert post.call_args.args[0] == 'http://example.invalid/api/generate'
    assert post.call_args.kwargs['json']['model'] == 'custom-reviewer'
    assert post.call_args.kwargs['json']['options']['temperature'] == 0


def test_model_unavailable(monkeypatch):
    monkeypatch.setattr(llm_client.requests, 'post', Mock(side_effect=requests.ConnectionError()))
    with pytest.raises(ModelError) as error:
        llm_client.generate('planner', {}, {'plan': str})
    assert error.value.status == 503


def test_worker_schema_and_valid_output(monkeypatch):
    output = {'answer': 'COMP1001', 'evidence_used': ['COMP1001'], 'missing_evidence': []}
    post = Mock(return_value=Mock(ok=True, json=Mock(return_value={'response': json.dumps(output)})))
    monkeypatch.setattr(llm_client.requests, 'post', post)
    assert worker_agent.run('Summarise', [{'course_code': 'COMP1001'}], {'plan': 'Summarise'}) == output
    assert post.call_args.kwargs['json']['format'] == {
        'type': 'object',
        'properties': {
            'answer': {'type': 'string'},
            'evidence_used': {'type': 'array', 'items': {}},
            'missing_evidence': {'type': 'array', 'items': {}},
        },
        'required': ['answer', 'evidence_used', 'missing_evidence'],
        'additionalProperties': False,
    }


@pytest.mark.parametrize('response', [
    json.dumps({'answer': 'Course', 'evidence_used': 'COMP1001', 'missing_evidence': []}),
    json.dumps({'answer': 'Course', 'evidence_used': [], 'missing_evidence': 'None'}),
    json.dumps({'answer': [], 'evidence_used': [], 'missing_evidence': []}),
    'not JSON',
])
def test_invalid_worker_output_still_rejected(monkeypatch, response):
    monkeypatch.setattr(llm_client.requests, 'post', Mock(
        return_value=Mock(ok=True, json=Mock(return_value={'response': response}))))
    with pytest.raises(ModelError):
        worker_agent.run('Summarise', [], {'plan': 'Summarise'})


def test_schema_supports_required_python_types(monkeypatch):
    output = {'text': 'value', 'array': [], 'object': {}, 'flag': True, 'count': 1, 'number': 1.5}
    fields = {'text': str, 'array': list, 'object': dict, 'flag': bool, 'count': int, 'number': float}
    post = Mock(return_value=Mock(ok=True, json=Mock(return_value={'response': json.dumps(output)})))
    monkeypatch.setattr(llm_client.requests, 'post', post)
    assert llm_client.generate('worker', {}, fields) == output
    schema = post.call_args.kwargs['json']['format']
    assert schema['properties'] == {
        'text': {'type': 'string'}, 'array': {'type': 'array', 'items': {}},
        'object': {'type': 'object'}, 'flag': {'type': 'boolean'},
        'count': {'type': 'integer'}, 'number': {'type': 'number'},
    }
    assert schema['required'] == list(fields)
    assert schema['additionalProperties'] is False


def test_worker_valid_attribution(monkeypatch):
    output = {'answer': 'Database Systems', 'evidence_used': ['COMP3311'], 'missing_evidence': []}
    generate = Mock(return_value=output)
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Name the course', [{'course_code': 'COMP3311'}], {}) == output
    assert generate.call_count == 1


def test_worker_missing_attribution_retried_once(monkeypatch):
    missing = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    corrected = {**missing, 'evidence_used': ['COMP3311']}
    generate = Mock(side_effect=[missing, corrected])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Name the course', [{'course_code': 'COMP3311'}], {}) == corrected
    assert generate.call_count == 2
    context = generate.call_args.args[1]
    assert context['previous_worker_result'] == missing
    assert 'exact course_code' in context['correction_instruction']


@pytest.mark.parametrize('references', [[], ['INVENTED'], [{'course_code': 'COMP3311'}], [True], ['COMP3311', 'INVENTED']])
def test_worker_invalid_attribution_fails_after_one_retry(monkeypatch, references):
    output = {'answer': 'Database Systems', 'evidence_used': references, 'missing_evidence': []}
    generate = Mock(return_value=output)
    monkeypatch.setattr(worker_agent, 'generate', generate)
    with pytest.raises(ModelError, match='evidence attribution after one corrective retry'):
        worker_agent.run('Name the course', [{'course_code': 'COMP3311'}], {})
    assert generate.call_count == 2
    assert output['evidence_used'] == references


def test_worker_empty_evidence_allows_empty_attribution(monkeypatch):
    output = {'answer': 'Insufficient evidence', 'evidence_used': [], 'missing_evidence': ['Course records']}
    generate = Mock(return_value=output)
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Name the course', [], {}) == output
    assert generate.call_count == 1


def test_worker_course_id_attribution(monkeypatch):
    output = {'answer': 'Database Systems', 'evidence_used': [12], 'missing_evidence': []}
    monkeypatch.setattr(worker_agent, 'generate', Mock(return_value=output))
    assert worker_agent.run('Name the course', [{'course_id': 12}], {}) == output


def test_worker_attribution_failure_is_structured(setup, monkeypatch):
    # Use the actual Worker implementation rather than the fixture's stage stub.
    spec = importlib.util.spec_from_file_location('actual_worker', SERVER / 'agents' / 'worker_agent.py')
    actual_worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual_worker)
    generate = Mock(return_value={'answer': 'Course', 'evidence_used': [], 'missing_evidence': []})
    monkeypatch.setattr(actual_worker, 'generate', generate)
    monkeypatch.setattr(worker_agent, 'run', actual_worker.run)
    response = setup[0].post('/workflow/course', json=payload())
    assert response.status_code == 502
    assert response.get_json()['failed_agent'] == 'worker'
    assert response.get_json()['human_review']['status'] == 'unavailable'
    assert setup[2] == ['planner']
    assert generate.call_count == 2
    audit = [json.loads(line) for line in (setup[3] / 'audit.jsonl').read_text().splitlines()]
    assert audit[-1]['worker_status'] == 'failed'
    assert not (setup[3] / 'history.jsonl').exists()


@pytest.mark.parametrize('answer,evidence,expected', [
    ('Database Systems', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], ['COMP3311']),
    ('The course is COMP3311.', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], ['COMP3311']),
    ('  database \n SYSTEMS  ', [{'course_code': 'COMP3311', 'course_name': 'Database   Systems'}], ['COMP3311']),
    ('comp3311', [{'course_code': 'COMP3311'}], ['COMP3311']),
    ('Database Systems', [{'course_code': 'COMP1001', 'course_name': 'Programming'},
                          {'course_code': 'COMP3311', 'course_name': 'Database Systems'}], ['COMP3311']),
    ('Database Systems', [{'course_id': 12, 'course_name': 'Database Systems'}], [12]),
    ('Course ID: 12.', [{'course_id': 12}], [12]),
])
def test_worker_exact_provenance_fallback(monkeypatch, answer, evidence, expected):
    output = {'answer': answer, 'evidence_used': [], 'missing_evidence': []}
    generate = Mock(side_effect=[output, output])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Name the course', evidence, {})['evidence_used'] == expected
    assert generate.call_count == 2
    assert 'correction_instruction' in generate.call_args.args[1]
    assert output['evidence_used'] == []


@pytest.mark.parametrize('answer,evidence', [
    ('Database Systems', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'},
                          {'course_code': 'COMP9999', 'course_name': 'Database Systems'}]),
    ('COMP3311 and COMP1001', [{'course_code': 'COMP3311'}, {'course_code': 'COMP1001'}]),
    ('Relational data course', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}]),
    ('COMP33110', [{'course_code': 'COMP3311'}]),
    ('Database Systems', [{'course_name': 'Database Systems'}]),
])
def test_worker_ambiguous_or_unmatched_fallback_fails(monkeypatch, answer, evidence):
    generate = Mock(return_value={'answer': answer, 'evidence_used': [], 'missing_evidence': []})
    monkeypatch.setattr(worker_agent, 'generate', generate)
    with pytest.raises(ModelError, match='evidence attribution after one corrective retry'):
        worker_agent.run('Name the course', evidence, {})
    assert generate.call_count == 2


def test_model_attribution_preferred_over_fallback(monkeypatch):
    output = {'answer': 'Database Systems', 'evidence_used': ['COMP3311'], 'missing_evidence': []}
    generate = Mock(return_value=output)
    resolve = Mock(side_effect=AssertionError('Fallback must not run'))
    monkeypatch.setattr(worker_agent, 'generate', generate)
    monkeypatch.setattr(worker_agent, '_resolve_provenance', resolve)
    assert worker_agent.run('Name the course', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}) == output
    assert generate.call_count == 1
    resolve.assert_not_called()


def test_retry_attribution_preferred_over_fallback(monkeypatch):
    missing = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    corrected = {**missing, 'evidence_used': ['COMP3311']}
    monkeypatch.setattr(worker_agent, 'generate', Mock(side_effect=[missing, corrected]))
    resolve = Mock(side_effect=AssertionError('Fallback must not run'))
    monkeypatch.setattr(worker_agent, '_resolve_provenance', resolve)
    assert worker_agent.run('Name the course', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}) == corrected
    resolve.assert_not_called()


def test_fallback_uses_retry_answer_and_replaces_invalid_references(monkeypatch):
    first = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    retry = {'answer': 'Programming', 'evidence_used': ['INVENTED'], 'missing_evidence': []}
    generate = Mock(side_effect=[first, retry])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    evidence = [{'course_code': 'COMP3311', 'course_name': 'Database Systems'},
                {'course_code': 'COMP1001', 'course_name': 'Programming'}]
    result = worker_agent.run('Name the course', evidence, {})
    assert result == {**retry, 'evidence_used': ['COMP1001']}
    assert generate.call_count == 2


def review_output(**updates):
    return {'risk': 'low', 'unsupported_claims': [], 'correction': '',
            'recommendation': 'Human review required', **updates}


def worker_output(answer='Database Systems', references=None):
    return {'answer': answer, 'evidence_used': ['COMP3311'] if references is None else references,
            'missing_evidence': []}


@pytest.mark.parametrize('answer', ['Database Systems', ' database \n SYSTEMS ', 'COMP3311', 'The course is comp3311.'])
def test_reviewer_verified_support_context(monkeypatch, answer):
    generate = Mock(return_value=review_output())
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    planner = {'plan': 'Name the course'}
    reviewer_agent.run('Name it', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], planner, worker_output(answer))
    facts = generate.call_args.args[1]['verified_support_facts']
    assert facts['worker_answer_supported'] is True
    assert facts['validated_evidence_used'] == ['COMP3311']
    assert facts['plan_to_review_separately'] == planner
    assert generate.call_count == 1


def test_reviewer_support_requires_matching_valid_reference(monkeypatch):
    generate = Mock(return_value=review_output(unsupported_claims=['Database Systems']))
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    evidence = [{'course_code': 'COMP3311', 'course_name': 'Database Systems'},
                {'course_code': 'COMP1001', 'course_name': 'Programming'}]
    reviewer_agent.run('Name it', evidence, {}, worker_output(references=['COMP1001']))
    facts = generate.call_args.args[1]['verified_support_facts']
    assert facts['worker_answer_supported'] is False
    assert facts['validated_evidence_used'] == ['COMP1001']
    assert generate.call_count == 1


def test_reviewer_genuine_unsupported_claim_remains(monkeypatch):
    output = review_output(risk='Unsupported credits', unsupported_claims=['The course has 12 credit points'])
    generate = Mock(return_value=output)
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('Describe it', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {},
        worker_output('Database Systems has 12 credit points')) == output
    assert generate.call_count == 1


def test_reviewer_plan_issue_is_separate(monkeypatch):
    output = review_output(risk='Incomplete plan compliance', correction='Include the requested lecturer or flag it missing')
    generate = Mock(return_value=output)
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('Name and lecturer', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}],
        {'plan': 'Name and lecturer'}, worker_output()) == output
    assert generate.call_count == 1


@pytest.mark.parametrize('contradiction', [
    review_output(unsupported_claims=['Database Systems']),
    review_output(unsupported_claims=['Database Systems is not supported by evidence']),
    review_output(risk='Unsupported factual claim'),
    review_output(unsupported_claims=['Worker answer is unsupported']),
    review_output(unsupported_claims=['Does not follow the plan']),
])
def test_reviewer_contradiction_retries_once(monkeypatch, contradiction):
    corrected = review_output()
    generate = Mock(side_effect=[contradiction, corrected])
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('Name it', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}, worker_output()) == corrected
    assert generate.call_count == 2
    context = generate.call_args.args[1]
    assert context['verified_support_facts']['worker_answer_supported'] is True
    assert context['previous_reviewer_result'] == contradiction
    assert 'contradicts' in context['correction_instruction']


def test_reviewer_second_contradiction_fails(monkeypatch):
    generate = Mock(return_value=review_output(unsupported_claims=['Database Systems']))
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    with pytest.raises(ModelError, match='reviewer evidence consistency after one corrective retry'):
        reviewer_agent.run('Name it', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}, worker_output())
    assert generate.call_count == 2


def test_reviewer_no_unsupported_risk_is_valid(monkeypatch):
    output = review_output(risk='No unsupported claims found')
    generate = Mock(return_value=output)
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('Name it', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}, worker_output()) == output
    assert generate.call_count == 1


def test_reviewer_consistency_failure_is_structured(setup, monkeypatch):
    spec = importlib.util.spec_from_file_location('actual_reviewer', SERVER / 'agents' / 'reviewer_agent.py')
    actual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual)
    generate = Mock(return_value=review_output(unsupported_claims=['COMP1001']))
    monkeypatch.setattr(actual, 'generate', generate)
    monkeypatch.setattr(reviewer_agent, 'run', actual.run)
    response = setup[0].post('/workflow/course', json=payload())
    assert response.status_code == 502
    assert response.get_json()['failed_agent'] == 'reviewer'
    assert response.get_json()['reviewer_status'] == 'failed'
    assert response.get_json()['human_review']['status'] == 'unavailable'
    assert generate.call_count == 2
