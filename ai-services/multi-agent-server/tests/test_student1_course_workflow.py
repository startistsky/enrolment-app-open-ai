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
    post = Mock(return_value=Mock(ok=True, json=Mock(return_value=reply)))
    monkeypatch.setattr(llm_client.requests, 'post', post)
    with pytest.raises(ModelError, match='after 2 attempts'):
        llm_client.generate('planner', {}, {'plan': str, 'evidence_required': list})
    assert post.call_count == 2


def test_malformed_output_retried_and_validated(monkeypatch):
    valid = {'plan': 'Use matching resources', 'evidence_required': ['resource_id']}
    post = Mock(side_effect=[
        Mock(ok=True, json=Mock(return_value={
            'response': '{"plan": "unfinished',
            'done_reason': 'stop',
            'eval_count': 18,
            'prompt_eval_count': 240,
        })),
        Mock(ok=True, json=Mock(return_value={'response': json.dumps(valid)})),
    ])
    monkeypatch.setattr(llm_client.requests, 'post', post)

    assert llm_client.generate(
        'planner', {}, {'plan': str, 'evidence_required': list}
    ) == valid
    assert [call.kwargs['json']['options']['seed'] for call in post.call_args_list] == [42, 43]


def test_incomplete_output_retried_and_validated(monkeypatch):
    valid = {'plan': 'Use matching resources', 'evidence_required': ['resource_id']}
    post = Mock(side_effect=[
        Mock(ok=True, json=Mock(return_value={
            'response': json.dumps({'plan': 'Use matching resources'}),
            'done_reason': 'length',
            'eval_count': 128,
            'prompt_eval_count': 240,
        })),
        Mock(ok=True, json=Mock(return_value={'response': json.dumps(valid)})),
    ])
    monkeypatch.setattr(llm_client.requests, 'post', post)

    assert llm_client.generate(
        'planner', {}, {'plan': str, 'evidence_required': list}
    ) == valid
    assert post.call_count == 2


def test_persistent_malformed_output_fails_with_completion_metadata(monkeypatch):
    post = Mock(return_value=Mock(ok=True, json=Mock(return_value={
        'response': '{"plan": "unfinished',
        'done_reason': 'length',
        'eval_count': 128,
        'prompt_eval_count': 240,
    })))
    monkeypatch.setattr(llm_client.requests, 'post', post)

    with pytest.raises(
        ModelError,
        match=r'invalid JSON output after 2 attempts; last completion: '
              r'done_reason=length, eval_count=128, prompt_eval_count=240',
    ):
        llm_client.generate('planner', {}, {'plan': str})
    assert post.call_count == 2


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
    assert worker_agent.run('Describe the supplied course', [{'course_code': 'COMP3311'}], {}) == output
    assert generate.call_count == 1


def test_worker_missing_attribution_retried_once(monkeypatch):
    missing = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    corrected = {**missing, 'evidence_used': ['COMP3311']}
    generate = Mock(side_effect=[missing, corrected])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Describe the supplied course', [{'course_code': 'COMP3311'}], {}) == corrected
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
        worker_agent.run('Describe the supplied course', [{'course_code': 'COMP3311'}], {})
    assert generate.call_count == 2
    assert output['evidence_used'] == references


def test_worker_empty_evidence_allows_empty_attribution(monkeypatch):
    output = {'answer': 'Insufficient evidence', 'evidence_used': [], 'missing_evidence': ['Course records']}
    generate = Mock(return_value=output)
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('Describe the supplied course', [], {}) == output
    assert generate.call_count == 1


def test_worker_course_id_attribution(monkeypatch):
    output = {'answer': 'Database Systems', 'evidence_used': [12], 'missing_evidence': []}
    monkeypatch.setattr(worker_agent, 'generate', Mock(return_value=output))
    assert worker_agent.run('Describe the supplied course', [{'course_id': 12}], {}) == output


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
    assert worker_agent.run('Describe the supplied course', evidence, {})['evidence_used'] == expected
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
        worker_agent.run('Describe the supplied course', evidence, {})
    assert generate.call_count == 2


def test_model_attribution_preferred_over_fallback(monkeypatch):
    output = {'answer': 'Database Systems', 'evidence_used': ['COMP3311'], 'missing_evidence': []}
    generate = Mock(return_value=output)
    resolve = Mock(side_effect=AssertionError('Fallback must not run'))
    monkeypatch.setattr(worker_agent, 'generate', generate)
    monkeypatch.setattr(worker_agent, '_resolve_provenance', resolve)
    assert worker_agent.run('Describe the supplied course', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}) == output
    assert generate.call_count == 1
    resolve.assert_not_called()


def test_retry_attribution_preferred_over_fallback(monkeypatch):
    missing = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    corrected = {**missing, 'evidence_used': ['COMP3311']}
    monkeypatch.setattr(worker_agent, 'generate', Mock(side_effect=[missing, corrected]))
    resolve = Mock(side_effect=AssertionError('Fallback must not run'))
    monkeypatch.setattr(worker_agent, '_resolve_provenance', resolve)
    assert worker_agent.run('Describe the supplied course', [{'course_code': 'COMP3311', 'course_name': 'Database Systems'}], {}) == corrected
    resolve.assert_not_called()


def test_fallback_uses_retry_answer_and_replaces_invalid_references(monkeypatch):
    first = {'answer': 'Database Systems', 'evidence_used': [], 'missing_evidence': []}
    retry = {'answer': 'Programming', 'evidence_used': ['INVENTED'], 'missing_evidence': []}
    generate = Mock(side_effect=[first, retry])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    evidence = [{'course_code': 'COMP3311', 'course_name': 'Database Systems'},
                {'course_code': 'COMP1001', 'course_name': 'Programming'}]
    result = worker_agent.run('Describe the supplied course', evidence, {})
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


COURSE_COMPLETENESS = [{'course_id': 4, 'course_code': 'COMP3311', 'course_name': 'Database Systems'}]


@pytest.mark.parametrize('user_request,answer,valid', [
    ('What is the name of COMP3311?', 'COMP3311', False),
    ('What is the name of COMP3311?', 'Database Systems', True),
    ('What is the name of COMP3311? Identify the supporting course code.', 'Database Systems (COMP3311)', True),
    ('What is the name of COMP3311? Identify the supporting course code.', 'Database Systems', False),
    ('What is the course code?', 'COMP3311', True),
    ('What is the course ID of COMP3311?', '4', True),
    ('What is the course ID of COMP3311?', 'COMP3311', False),
    ('What is the lecturer name for COMP3311?', 'Not supplied', True),
])
def test_worker_requested_field_completeness(monkeypatch, user_request, answer, valid):
    output = worker_output(answer)
    generate = Mock(return_value=output)
    monkeypatch.setattr(worker_agent, 'generate', generate)
    if valid:
        assert worker_agent.run(user_request, COURSE_COMPLETENESS, {}) == output
        assert generate.call_count == 1
    else:
        result = worker_agent.run(user_request, COURSE_COMPLETENESS, {})
        assert result.completion_source == 'deterministic_evidence_fallback'
        from agents.course_request import missing_fields, requested_values
        assert missing_fields(answer, requested_values(user_request, COURSE_COMPLETENESS))
        assert not missing_fields(result['answer'], requested_values(user_request, COURSE_COMPLETENESS))
        assert generate.call_count == 2


def test_worker_completeness_retry_supplies_requested_categories(monkeypatch):
    first = worker_output('COMP3311')
    corrected = worker_output('Database Systems (COMP3311)')
    generate = Mock(side_effect=[first, corrected])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    assert worker_agent.run('What is the name of COMP3311? Identify the supporting course code.', COURSE_COMPLETENESS, {}) == corrected
    assert generate.call_count == 2
    context = generate.call_args.args[1]
    assert context['requested_field_values'] == {'course_name': 'Database Systems', 'course_code': 'COMP3311'}
    assert 'course_name' in context['correction_instruction']
    assert first['answer'] == 'COMP3311'


def test_worker_completeness_failure_is_structured(setup, monkeypatch):
    spec = importlib.util.spec_from_file_location('actual_complete_worker', SERVER / 'agents' / 'worker_agent.py')
    actual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual)
    generate = Mock(return_value=worker_output('COMP3311'))
    monkeypatch.setattr(actual, 'generate', generate)
    monkeypatch.setattr(worker_agent, 'run', actual.run)
    response = setup[0].post('/workflow/course', json={**payload(), 'user_request': 'What is the name of COMP3311?', 'evidence': [{'course_code': 'COMP3311'}]})
    assert response.status_code == 502
    assert response.get_json()['failed_agent'] == 'worker'
    assert 'Incomplete worker answer' in response.get_json()['error']
    assert response.get_json()['human_review']['status'] == 'unavailable'
    assert setup[2] == ['planner']
    assert generate.call_count == 2


@pytest.mark.parametrize('claim', [
    'Worker correctly identified course ID 4 and course name Database Systems.',
    'Worker provided Database Systems.',
    'Worker correctly answered the course name.',
    'Worker correctly answered the question.',
])
def test_reviewer_cannot_credit_absent_values(monkeypatch, claim):
    bad = review_output(recommendation=claim)
    good = review_output(risk='Incomplete answer', correction='Include the missing course name Database Systems.')
    generate = Mock(side_effect=[bad, good])
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('What is the name of COMP3311?', COURSE_COMPLETENESS, {}, worker_output('COMP3311')) == good
    assert generate.call_count == 2
    facts = generate.call_args.args[1]['verified_completeness_facts']
    assert facts['worker_answer_complete'] is False
    assert facts['missing_requested_fields'] == ['course_name']


def test_reviewer_repeated_absent_value_claim_fails(monkeypatch):
    generate = Mock(return_value=review_output(recommendation='Worker correctly identified course ID 4 and course name Database Systems.'))
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    with pytest.raises(ModelError, match='reviewer evidence consistency after one corrective retry'):
        reviewer_agent.run('What is the name of COMP3311?', COURSE_COMPLETENESS, {}, worker_output('COMP3311'))
    assert generate.call_count == 2


def test_reviewer_may_distinguish_evidence_from_worker_answer(monkeypatch):
    output = review_output(risk='Incomplete answer', correction='Worker did not identify the course name. Evidence contains Database Systems; add the missing name.')
    generate = Mock(return_value=output)
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    assert reviewer_agent.run('What is the name of COMP3311?', COURSE_COMPLETENESS, {}, worker_output('COMP3311')) == output
    assert generate.call_count == 1


@pytest.mark.parametrize('user_request,expected_answer', [
    ('What is the name of COMP3311? Identify the supporting course code.', 'Database Systems (COMP3311)'),
    ('What is the name of COMP3311?', 'Database Systems'),
    ('What is the course code?', 'COMP3311'),
    ('What is the course ID of COMP3311?', '4'),
])
def test_deterministic_completion_after_exactly_one_retry(monkeypatch, user_request, expected_answer):
    generate = Mock(return_value=worker_output(''))
    monkeypatch.setattr(worker_agent, 'generate', generate)
    result = worker_agent.run(user_request, COURSE_COMPLETENESS, {})
    assert result == {'answer': expected_answer, 'evidence_used': ['COMP3311'], 'missing_evidence': []}
    assert result.completion_source == 'deterministic_evidence_fallback'
    assert set(result) == {'answer', 'evidence_used', 'missing_evidence'}
    assert generate.call_count == 2


@pytest.mark.parametrize('user_request,evidence', [
    ('What is the name of COMP3311?', COURSE_COMPLETENESS + [{'course_code': 'COMP3311', 'course_name': 'Other name'}]),
    ('What is the name of COMP3311?', [{'course_code': 'COMP3311'}]),
    ('What is the name of COMP3311 and its lecturer?', COURSE_COMPLETENESS),
    ('What is the name of COMP9999?', COURSE_COMPLETENESS),
    ('What is the course name?', COURSE_COMPLETENESS + [{'course_code': 'COMP1001', 'course_name': 'Programming'}]),
    ('What is the name of COMP3311 and its credit points?', COURSE_COMPLETENESS),
])
def test_deterministic_completion_refuses_ambiguous_missing_or_unsupported(monkeypatch, user_request, evidence):
    generate = Mock(return_value=worker_output('COMP3311'))
    monkeypatch.setattr(worker_agent, 'generate', generate)
    with pytest.raises(ModelError, match='Incomplete worker answer after one corrective retry'):
        worker_agent.run(user_request, evidence, {})
    assert generate.call_count == 2


@pytest.mark.parametrize('retry', [False, True])
def test_complete_model_output_keeps_model_source(monkeypatch, retry):
    complete = worker_output('Database Systems (COMP3311)')
    generate = Mock(side_effect=[worker_output('COMP3311'), complete] if retry else [complete])
    monkeypatch.setattr(worker_agent, 'generate', generate)
    result = worker_agent.run('What is the name of COMP3311? Identify the supporting course code.', COURSE_COMPLETENESS, {})
    assert result == complete
    assert result.completion_source == 'model'
    assert generate.call_count == 2 if retry else generate.call_count == 1


@pytest.mark.parametrize('fallback', [True, False])
def test_workflow_records_completion_source_and_reviews_final_answer(setup, monkeypatch, fallback):
    spec = importlib.util.spec_from_file_location('actual_fallback_worker', SERVER / 'agents' / 'worker_agent.py')
    actual = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(actual)
    answer = 'COMP3311' if fallback else 'Database Systems (COMP3311)'
    generate = Mock(return_value=worker_output(answer))
    monkeypatch.setattr(actual, 'generate', generate)
    monkeypatch.setattr(worker_agent, 'run', actual.run)
    reviewer = Mock(return_value=review_output())
    monkeypatch.setattr(reviewer_agent, 'run', reviewer)
    response = setup[0].post('/workflow/course', json={**payload(),
        'user_request': 'What is the name of COMP3311? Identify the supporting course code.', 'evidence': COURSE_COMPLETENESS})
    assert response.status_code == 200
    body = response.get_json()
    assert body['worker_result']['answer'] == 'Database Systems (COMP3311)'
    assert reviewer.call_args.args[3] == body['worker_result']
    assert '4' not in body['worker_result']['answer']
    source = 'deterministic_evidence_fallback' if fallback else 'model'
    assert 'worker_completion_source' not in body['worker_result']
    for file in ('history.jsonl', 'audit.jsonl'):
        last = json.loads((setup[3] / file).read_text().splitlines()[-1])
        assert last['worker_completion_source'] == source
    setup[0].post(f"/workflow/{body['workflow_id']}/decision", json={'decision': 'Accept'})
    final = json.loads((setup[3] / 'history.jsonl').read_text().splitlines()[-1])
    assert final['worker_completion_source'] == source


def test_reviewer_cannot_invent_id_for_final_completion(monkeypatch):
    correct = review_output(risk='None')
    generate = Mock(side_effect=[review_output(recommendation='Worker identified course ID 4.'), correct])
    monkeypatch.setattr(reviewer_agent, 'generate', generate)
    result = reviewer_agent.run('What is the name of COMP3311? Identify the supporting course code.',
                               COURSE_COMPLETENESS, {}, worker_output('Database Systems (COMP3311)'))
    assert result == correct
    assert generate.call_count == 2
    facts = generate.call_args.args[1]['verified_completeness_facts']
    assert facts['worker_answer_complete'] is True


@pytest.mark.parametrize('user_request,fields', [
    ('What is the name of COMP3311? Identify the supporting course code.', ['course_name', 'course_code']),
    ('What is the name of COMP3311?', ['course_name']),
    ('What is the course code?', ['course_code']),
    ('What is the course ID of COMP3311?', ['course_id']),
])
def test_planner_model_and_fallback_fields(monkeypatch, user_request, fields):
    correct = {'plan': 'Identify ' + ' and '.join(fields), 'evidence_required': fields}
    generate = Mock(return_value=correct)
    monkeypatch.setattr(planner_agent, 'generate', generate)
    result = planner_agent.run(user_request, COURSE_COMPLETENESS)
    assert result == correct
    assert result.completion_source == 'model'
    assert generate.call_count == 1
    generate.reset_mock()
    generate.return_value = {'plan': 'Unrelated task', 'evidence_required': []}
    result = planner_agent.run(user_request, COURSE_COMPLETENESS)
    assert result.completion_source == 'deterministic_evidence_fallback'
    assert generate.call_count == 2
    assert result['evidence_required'] == [{field: COURSE_COMPLETENESS[0][field] for field in fields}]
    assert set(result) == {'plan', 'evidence_required'}
    assert planner_agent._fields(result['plan']) == set(fields)


def test_planner_substituted_id_gets_one_retry(monkeypatch):
    bad = {'plan': 'Identify course ID and course name', 'evidence_required': ['course_id', 'course_name']}
    good = {'plan': 'Identify course name and supporting course code', 'evidence_required': ['course_name', 'course_code']}
    generate = Mock(side_effect=[bad, good])
    monkeypatch.setattr(planner_agent, 'generate', generate)
    result = planner_agent.run('What is the name of COMP3311? Identify the supporting course code.', COURSE_COMPLETENESS)
    assert result == good
    assert result.completion_source == 'corrective_retry'
    assert generate.call_count == 2
    assert generate.call_args.args[1]['explicit_requested_fields'] == ['course_name', 'course_code']


@pytest.mark.parametrize('evidence,user_request', [
    (COURSE_COMPLETENESS + [{'course_code': 'COMP3311', 'course_name': 'Other'}], 'What is the name of COMP3311?'),
    ([{'course_code': 'COMP3311'}], 'What is the name of COMP3311?'),
    (COURSE_COMPLETENESS, 'What is the name of COMP3311 and its lecturer?'),
])
def test_planner_unresolvable_fallback_fails(monkeypatch, evidence, user_request):
    generate = Mock(return_value={'plan': 'Identify course ID', 'evidence_required': ['course_id']})
    monkeypatch.setattr(planner_agent, 'generate', generate)
    with pytest.raises(ModelError, match='planner request-field alignment after one corrective retry'):
        planner_agent.run(user_request, evidence)
    assert generate.call_count == 2


@pytest.mark.parametrize('source', ['model', 'corrective_retry', 'deterministic_evidence_fallback'])
def test_workflow_records_planner_source(setup, monkeypatch, source):
    planner = planner_agent.PlannerResult({'plan': 'Summarise records', 'evidence_required': ['course_code']}, source)
    monkeypatch.setattr(planner_agent, 'run', Mock(return_value=planner))
    monkeypatch.setattr(worker_agent, 'run', Mock(return_value=worker_output('COMP1001', ['COMP1001'])))
    monkeypatch.setattr(reviewer_agent, 'run', Mock(return_value=review_output()))
    response = setup[0].post('/workflow/course', json=payload())
    assert response.status_code == 200
    body = response.get_json()
    assert set(body['planner_result']) == {'plan', 'evidence_required'}
    for file in ('history.jsonl', 'audit.jsonl'):
        row = json.loads((setup[3] / file).read_text().splitlines()[-1])
        assert row['planner_completion_source'] == source
    setup[0].post(f"/workflow/{body['workflow_id']}/decision", json={'decision': 'Accept'})
    assert json.loads((setup[3] / 'history.jsonl').read_text().splitlines()[-1])['planner_completion_source'] == source
