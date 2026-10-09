"""Exercise cloud route guards in isolated processes to avoid app/module collisions."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('student', [1, 2, 3, 4, 5])
def test_cloud_guards_preserve_crud_and_block_all_ai_routes(student, tmp_path):
    code = '''
import os
from pathlib import Path
from unittest.mock import patch
import app
server = app.app
client = server.test_client()
assert client.get('/health').status_code == 200
crud_paths = {1:'/api/courses',2:'/api/assignments',3:'/resources',4:'/api/events',5:'/api/jobs'}
student = int(os.environ['TEST_STUDENT'])
with server.test_request_context(crud_paths[student]):
    assert server.preprocess_request() is None
# Discover every existing AI endpoint, including parameterised routes.
def ai_route(rule):
    path = rule.rule
    return (path.startswith(('/api/mcp/', '/api/rag/', '/api/multi-agent/', '/api/agentic/', '/api/ai', '/rag/', '/recommend'))
            or path.endswith('/recommendation') or rule.endpoint.startswith(('ai.', 'ai_routes.')))
with patch('requests.sessions.Session.request', side_effect=AssertionError('Unexpected network request')):
    rules = [rule for rule in server.url_map.iter_rules() if ai_route(rule)]
    assert rules
    for rule in rules:
        import re
        path = re.sub(r'<[^>]+>', '1', rule.rule)
        method = next(m for m in rule.methods if m not in ('OPTIONS','HEAD'))
        response = client.open(path, method=method, json={})
        assert response.status_code == 503, (student,path,response.status_code)
        assert 'disabled' in response.get_json()['error']
# Toggle off the guard to prove existing local routes remain available to handlers.
os.environ['AI_SERVICES_ENABLED'] = 'true'
with server.test_request_context(rules[0].rule, method=next(m for m in rules[0].methods if m not in ('OPTIONS','HEAD'))):
    assert server.preprocess_request() is None
if student == 5:
    from model.database import DATABASE
    assert DATABASE == Path(os.environ['DATABASE_PATH'])
    assert DATABASE.is_file()
    response = client.get('/api/jobs')
    assert response.status_code == 200
'''
    result = subprocess.run(  # noqa: S603 -- fixed Python executable and internal test program, no shell.
        [sys.executable, '-c', code], cwd=ROOT / f'student-{student}/backend',
        env=os.environ | {'AI_SERVICES_ENABLED': 'false', 'TEST_STUDENT': str(student),
                          'DATABASE_PATH': str(tmp_path / 'career.db')},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_rendered_cloud_compose_architecture():
    result = subprocess.run(  # noqa: S603,S607 -- fixed read-only Compose config command.
        [shutil.which('docker'), 'compose', '-f', 'docker-compose.cloud.yml', 'config', '--format', 'json'],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    config = json.loads(result.stdout)
    services = config['services']
    assert len(services) == 16
    assert not any(name in services for name in ('ollama', 'ollama-init', 'mcp-server', 'rag-server', 'multi-agent-server'))
    assert 'host.docker.internal' not in result.stdout
    for name in ('student1-backend', 'student2-backend', 'student3-backend', 'backend', 'student5-backend'):
        environment = services[name]['environment']
        assert environment['AI_SERVICES_ENABLED'] == 'false'
        assert environment['FLASK_DEBUG'] == 'false'
        for key in ('AI_SERVICE_URL','OLLAMA_URL','MCP_SERVER_URL','RAG_SERVER_URL','MULTI_AGENT_SERVER_URL'):
            assert environment[key] == ''
        assert all(port['host_ip'] == '127.0.0.1' for port in services[name]['ports'])
    for name in ('student1-database','student2-database','student3-database','database','student5-database'):
        assert 'ports' not in services[name]
        assert any(volume['type'] == 'volume' and volume['target'] == '/data' for volume in services[name]['volumes'])
    assert services['student5-backend']['depends_on']['student5-database']['condition'] == 'service_completed_successfully'


def test_private_source_archive_excludes_credentials_and_preserves_checkout(tmp_path):
    import importlib.util
    import tarfile

    spec = importlib.util.spec_from_file_location('package_source', ROOT / 'scripts/cloud/package_source.py')
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    source = tmp_path / 'source'
    source.mkdir()
    for command in ([shutil.which('git'), 'init', '-q'],
                    [shutil.which('git'), '-c', 'user.name=Cloud Test', '-c', 'user.email=cloud@example.invalid',
                     'commit', '--allow-empty', '-qm', 'fixture']):
        subprocess.run(command, cwd=source, check=True)  # noqa: S603 -- fixed Git commands in temporary fixture.
    contents = {
        'docker-compose.cloud.yml': 'services: {}',
        'scripts/cloud/health-check.sh': '# fixture health script',
        'student-2/backend/app.py': '# current uncommitted application source',
        'student-5/frontend/js/api.js': 'const API_URL = "/api";',
        'student-2/.env': 'fixture local environment, excluded',
        'student-2/.env.example': '# safe example configuration',
        'student-5/database/career.db': 'fixture runtime database, excluded',
        'student-3/backend/__pycache__/app.pyc': 'fixture bytecode, excluded',
        'student-4/deployment.pem': 'fixture local key path, excluded',
        'unrelated-private-notes.txt': 'outside application scope, excluded',
    }
    for name, value in contents.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    output = tmp_path / 'source.tar.gz'
    packager.package(source, output)
    with tarfile.open(output) as archive:
        names = set(archive.getnames())
        assert names == {'docker-compose.cloud.yml', 'scripts/cloud/health-check.sh',
                         'student-2/backend/app.py', 'student-2/.env.example',
                         'student-5/frontend/js/api.js', 'deployment-source.json'}
        assert archive.extractfile('student-2/backend/app.py').read().decode() == contents['student-2/backend/app.py']
        assert json.load(archive.extractfile('deployment-source.json'))['working_tree_modified'] is True
    (source / 'student-2/backend/linked.py').symlink_to(tmp_path / 'outside.py')
    with pytest.raises(ValueError, match='non-regular'):
        packager.package(source, output)


def test_selected_region_and_managed_identity_oidc_configuration():
    import re
    import yaml

    script = (ROOT / 'scripts/cloud/deploy-azure-vm.sh').read_text()
    workflow = yaml.safe_load((ROOT / '.github/workflows/cloud-deployment.yml').read_text())
    documentation = (ROOT / 'docs/AZURE_DEPLOYMENT.md').read_text()
    assert 'LOCATION=${LOCATION:-eastasia}' in script
    # PyYAML's YAML 1.1 loader interprets the GitHub 'on' key as boolean True.
    assert workflow.get('on', workflow.get(True)).keys() == {'workflow_dispatch'}
    assert workflow['permissions'] == {'contents': 'read', 'id-token': 'write'}
    job = workflow['jobs']['deploy']
    assert job['environment'] == 'azure-assessment'
    login_steps = [step for step in job['steps'] if step.get('uses') == 'azure/login@v2']
    assert len(login_steps) == 1
    assert login_steps[0]['with'] == {
        'client-id': '${{ secrets.AZURE_CLIENT_ID }}',
        'tenant-id': '${{ secrets.AZURE_TENANT_ID }}',
        'subscription-id': '${{ secrets.AZURE_SUBSCRIPTION_ID }}',
    }
    deploy_step = next(step for step in job['steps'] if 'SSH_PRIVATE_KEY' in step.get('env', {}))
    assert deploy_step['env']['LOCATION'] == 'eastasia'
    assert deploy_step['env']['RESOURCE_GROUP'] == 'asd-group5-rg'
    workflow_text = (ROOT / '.github/workflows/cloud-deployment.yml').read_text().lower()
    assert 'client-secret' not in workflow_text and 'azure_credentials' not in workflow_text
    assert 'asd-group5-github-oidc-mi' in documentation
    assert 'repo:startistsky/enrolment-app-open-ai:environment:azure-assessment' in documentation
    assert 'Contributor scoped only to `asd-group5-rg`' in documentation
    # Historical region mentions must describe resource-group metadata, never deployment.
    metadata_region = 'australia' + 'east'
    matching_lines = [line for line in documentation.splitlines() if metadata_region in line.lower()]
    assert matching_lines and all('resource-group metadata location' in line for line in matching_lines)
    assert 'australia' + ' east' not in documentation.lower()
    cloud_files = [ROOT / 'docker-compose.cloud.yml', ROOT / '.github/workflows/cloud-deployment.yml',
                   *list((ROOT / 'scripts/cloud').glob('*.sh')), *list((ROOT / 'scripts/cloud').glob('*.py'))]
    for path in cloud_files:
        content = path.read_text().lower()
        assert metadata_region not in content, path
        assert 'az ad app create' not in content, path
    for line in documentation.splitlines():
        if re.match(r'export LOCATION=', line):
            assert line == 'export LOCATION=eastasia'
