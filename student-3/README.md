# Student 3 – Campus Resource Management

**Release:** 2

Campus Resource Management is part of the SmartCampus AI application. It allows users to view, search, create, update and delete campus resources, check availability and capacity, and request AI-assisted resource recommendations.

## Microservices

The feature uses three Dockerised microservices:

- **Frontend:** HTML, CSS, JavaScript and Nginx.
- **Backend/API:** Flask API for resource CRUD, validation and AI integrations.
- **Database:** Flask database API backed by resource data storage.

The frontend communicates with the backend, and the backend communicates with the database API. The frontend does not access the database directly.

## Resource functionality

- View and search campus resources.
- View individual resource details.
- Create, update and delete resources.
- Check resource availability and capacity.
- Request AI-assisted resource recommendations.

## AI Resource Assistant

The backend provides `POST /recommend` and is configured to use the shared Ollama service. AI features require the relevant model and service to be running.

## MCP and RAG Integration

Release 2 adds Model Context Protocol (MCP) and Retrieval-Augmented Generation (RAG) integration for resource information and evidence-grounded recommendations.

The backend exposes:

- `GET /api/mcp/resource-count`
- `GET /api/mcp/resource-by-type/<resource_type>`
- `POST /rag/recommend`

The backend is configured to access separate MCP and RAG services; these are not part of the three Student 3 Docker Compose services.

## Resource Multi-Agent Workflow

Release 2 includes a Resource Management workflow:

**Planner → Worker → Reviewer → Human Decision**

- **Planner:** Interprets the request and prepares a plan.
- **Worker:** Selects resources using available evidence.
- **Reviewer:** Evaluates recommendations for evidence gaps and errors.
- **Human Reviewer:** Chooses **Accept**, **Partially Accept** or **Reject**.

The Student 3 backend exposes `POST /api/multi-agent/resource`, which integrates with the Multi-Agent Server's `POST /workflow/resource`. Workflows remain pending human review until a decision is recorded. The coordination service stores workflow history and audit events in JSONL files.

## Docker and ports

| Service | Host port |
|---|---:|
| Student 3 Frontend | 8083 |
| Student 3 Backend/API | 8003 |
| Student 3 Database | 5004 |
| Shared Ollama | 11434 |
| Shared SmartCampus Homepage | 8888 |

The backend is configured to connect to separately hosted MCP (`9001`), RAG (`9101`) and Multi-Agent (`9201`) services via `host.docker.internal`. These services are **not** started by the Student 3 Docker Compose services.

## Start with Docker Compose

From the repository root:

```bash
docker compose up -d --build shared-frontend student3-frontend student3-backend student3-database ollama
```

Open the shared homepage at <http://localhost:8888>, or open Campus Resource Management directly at <http://localhost:8083>.

Resource CRUD requires the Student 3 frontend, backend and database services. AI features additionally require their corresponding model and supporting services to be available.

## Resource API endpoints

| Method | Backend endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health |
| GET | `/resources` | List resources |
| GET | `/resources/<resource_id>` | Get resource details |
| POST | `/resources` | Create a resource |
| PUT | `/resources/<resource_id>` | Update a resource |
| DELETE | `/resources/<resource_id>` | Delete a resource |
| POST | `/recommend` | AI resource recommendation |
| GET | `/api/mcp/resource-count` | MCP resource count |
| GET | `/api/mcp/resource-by-type/<resource_type>` | MCP resources by type |
| POST | `/rag/recommend` | RAG recommendation |
| POST | `/api/multi-agent/resource` | Resource Multi-Agent workflow |

The backend is available locally at <http://localhost:8003> when the Docker Compose service is running.

## Automated tests

Student 3 maintains tests for its resource functionality and integrations. Install Student 3 test dependencies from the repository root:

```bash
python -m pip install -r student-3/tests/requirements.txt
```
Run the MCP and RAG integration tests:

```bash
python -m pytest student-3/tests/test_mcp_integration.py student-3/tests/test_rag_integration.py -v
```

The following tests are also available for the running application:

- `student-3/tests/test_database.py`
- `student-3/tests/test_backend.py`
- `student-3/tests/test_ai.py`

These tests use HTTP requests and require the relevant application services to be running.

Run the eight Resource Agent regression tests:

```bash
PYTHONPATH=ai-services/multi-agent-server python -m unittest discover -s ai-services/multi-agent-server/tests -p 'test_resource_agents.py' -v
```

Run the nine Resource Workflow API tests:

```bash
PYTHONPATH=ai-services/multi-agent-server python -m pytest ai-services/multi-agent-server/tests/test_student3_resource_workflow.py -v
```

The 17 tests cover resource matching, evidence grounding, reviewer validation, agent execution order, human decisions, invalid requests and audit persistence. The workflow API tests use mocked agents; they do not require a live Ollama model.

## Continuous integration

Student 3's GitHub Actions workflow is at `.github/workflows/student-3.yml`. It runs resource multi-agent regression and workflow tests, includes MCP/RAG validation, checks Docker Compose and builds Student 3 Docker images.

A successful GitHub Actions run, including all 17 Multi-Agent tests, is recorded at:

<https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39006775584>

## Release 2 evidence

See [Release 2 Evidence Report](docs/release2-evidence.md) for live workflow IDs, human decisions, JSONL audit events, testing results and CI evidence.
