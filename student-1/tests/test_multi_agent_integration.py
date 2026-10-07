from unittest.mock import Mock

import pytest
import requests


URL = '/api/multi-agent/course-workflow'


def workflow():
    return {'workflow_id': 'workflow-1', 'feature': 'course_management',
            'status': 'pending_human_review', 'planner_result': {'plan': 'Summarise'},
            'worker_result': {'answer': 'Course'}, 'reviewer_result': {'risk': 'low'},
            'human_review': {'required': True, 'status': 'pending',
                             'allowed_decisions': ['Accept', 'Partially Accept', 'Reject']}}


@pytest.fixture
def upstream(backend_app, monkeypatch):
    evidence = [{'course_id': 1, 'course_code': 'COMP1001'}]
    database = Mock(return_value=(Mock(status_code=200, json=Mock(return_value=evidence)), None))
    monkeypatch.setattr(backend_app, 'database_request', database)
    post = Mock(return_value=Mock(status_code=200, json=Mock(return_value=workflow())))
    monkeypatch.setattr(backend_app.requests, 'post', post)
    return database, post, evidence


def test_course_workflow_endpoint_proxy(backend_client, backend_app, upstream):
    assert backend_client.post(URL, json={'user_request': ' Summarise '}).status_code == 200
    upstream[0].assert_called_once_with('GET', '/courses')
    upstream[1].assert_called_once_with(f'{backend_app.MULTI_AGENT_SERVER_URL}/workflow/course',
        json={'user_request': 'Summarise', 'feature': 'course_management', 'evidence': upstream[2]},
        timeout=backend_app.MULTI_AGENT_TIMEOUT_SECONDS)


@pytest.mark.parametrize('body', [{}, {'user_request': ''}, {'user_request': 42}, []])
def test_missing_request(backend_client, upstream, body):
    assert backend_client.post(URL, json=body).status_code == 400
    upstream[0].assert_not_called()
    upstream[1].assert_not_called()


@pytest.mark.parametrize('exception', [requests.ConnectionError, requests.Timeout])
def test_unavailable(backend_client, upstream, exception):
    upstream[1].side_effect = exception()
    assert backend_client.post(URL, json={'user_request': 'Summarise'}).status_code == 503


@pytest.mark.parametrize('body', [[], {}, {'error': 'failure'}, {**workflow(), 'reviewer_result': None},
    {**workflow(), 'human_review': {'status': 'pending'}}, {**workflow(), 'status': 'completed'}])
def test_invalid_upstream(backend_client, upstream, body):
    upstream[1].return_value.json.return_value = body
    assert backend_client.post(URL, json={'user_request': 'Summarise'}).status_code == 502


def test_invalid_json(backend_client, upstream):
    upstream[1].return_value.json.side_effect = ValueError()
    assert backend_client.post(URL, json={'user_request': 'Summarise'}).status_code == 502


def test_upstream_error(backend_client, upstream):
    upstream[1].return_value.status_code = 503
    upstream[1].return_value.json.return_value = {'error': 'Ollama unavailable'}
    result = backend_client.post(URL, json={'user_request': 'Summarise'})
    assert result.status_code == 502
    assert result.get_json()['detail'] == 'Ollama unavailable'


def test_course_workflow_decision_endpoint_proxy(backend_client, upstream):
    body = workflow()
    body['status'] = 'completed'
    body['human_review'].update(status='completed', decision='Accept', reason='Checked')
    upstream[1].return_value.json.return_value = body
    response = backend_client.post(URL + '/workflow-1/decision', json={'decision': 'Accept', 'reason': 'Checked'})
    assert response.status_code == 200
    assert upstream[1].call_args.kwargs['json'] == {'decision': 'Accept', 'reason': 'Checked'}
    upstream[0].assert_not_called()


def test_invalid_decision(backend_client, upstream):
    assert backend_client.post(URL + '/workflow-1/decision', json={'decision': 'approve'}).status_code == 400
    upstream[1].assert_not_called()


@pytest.mark.parametrize('evidence', [{}, [3]])
def test_invalid_database_evidence(backend_client, upstream, evidence):
    upstream[0].return_value[0].json.return_value = evidence
    assert backend_client.post(URL, json={'user_request': 'Summarise'}).status_code == 502
    upstream[1].assert_not_called()
