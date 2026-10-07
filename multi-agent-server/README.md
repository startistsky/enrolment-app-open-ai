# Release 2 local Multi-Agent foundation

Run this Flask service on the host, outside Docker, on port 9201. The browser
uses relative `/api` calls through Student 1's backend. That backend fetches
`GET /courses` from the existing database service and supplies the records as
evidence. Only the database service owns SQLite.

Each synchronous workflow runs Planner, then Worker, then Reviewer. There is
no parallel execution, course mutation or automatic human decision. Worker
attribution failures get at most one corrective retry, then fail explicitly. Missing evidence must be flagged by the Worker; the Reviewer checks
against the original records and plan. Prompts constrain grounding but do not
prove factual correctness: the human review remains required.

## Start locally

From the repository root:

```sh
python -m venv .venv-multi-agent
.venv-multi-agent/bin/python -m pip install -r multi-agent-server/requirements.txt
docker compose up -d --build student1-database student1-backend student1-frontend ollama
docker compose exec ollama ollama pull qwen2.5:0.5b
docker compose exec ollama ollama pull llama3.1:8b
.venv-multi-agent/bin/python multi-agent-server/app.py
```

Leave that terminal running. Open `http://localhost:8081`, add courses if
needed, enter a request in **Release 2 Multi-Agent Course Workflow**, run it,
inspect all three results, then choose Accept, Partially Accept or Reject.
These decisions record review only; they do not change course records.

In another terminal, from the repository root:

```sh
curl -sS http://localhost:9201/health
curl -sS http://localhost:9201/workflow/status
curl -sS --max-time 400 http://localhost:8001/api/multi-agent/course-workflow \
  -H 'Content-Type: application/json' \
  -d '{"user_request":"Summarise the available courses and identify missing evidence."}' \
  > /tmp/student1-workflow.json
python -m json.tool /tmp/student1-workflow.json
workflow_id=$(python -c 'import json; print(json.load(open("/tmp/student1-workflow.json"))["workflow_id"])')
curl -sS "http://localhost:8001/api/multi-agent/course-workflow/$workflow_id/decision" \
  -H 'Content-Type: application/json' \
  -d '{"decision":"Accept","reason":"I checked the supplied course records and reviewer output."}'
```

Submit the decision only after personally reviewing the generated results.
To exercise the server directly without the database (empty evidence):

```sh
curl -sS --max-time 400 http://localhost:9201/workflow/course \
  -H 'Content-Type: application/json' \
  -d '{"user_request":"Summarise courses; flag missing evidence.","feature":"course_management","evidence":[]}'
```

## Configuration and endpoints

- `OLLAMA_URL`: defaults to `http://localhost:11434/api/generate`.
- `OLLAMA_REVIEW_MODEL`: defaults to `llama3.1:8b`; requires that model pulled.
- Planner and Worker use `qwen2.5:0.5b`, temperature 0, seed 42.
- `OLLAMA_TIMEOUT_SECONDS`: 120 per model call.
- Backend `MULTI_AGENT_SERVER_URL`: localhost:9201 for local Python;
  Compose sets `http://host.docker.internal:9201`.
- Backend `MULTI_AGENT_TIMEOUT_SECONDS`: 390 for three sequential calls.
  The frontend workflow proxy allows 400 seconds.
- `WORKFLOW_HISTORY_PATH` / `COORDINATION_AUDIT_PATH`: optional file paths;
  parent directories must already exist.

Server endpoints: `GET /health`, `POST /workflow/course`,
`POST /workflow/<workflow_id>/decision`, `GET /workflow/status`.
Backend endpoints: `POST /api/multi-agent/course-workflow`,
`POST /api/multi-agent/course-workflow/<workflow_id>/decision`.

Model connection/timeouts return structured 503; invalid model output or HTTP
failures return 502. Backend connection/timeouts return 503; malformed or failed
upstream responses return 502. Invalid input returns 400. Decisions for unknown
workflows return 404; decisions before review or repeated decisions return 409.
Health reports service liveness, not Ollama model readiness.

## Evidence and lifecycle

Both JSONL files are ignored by Git and created when first written. The audit
log records metadata for workflow starts, completed stages, model failures,
pending reviews and human decisions: timestamps, IDs, feature, agent statuses,
evidence count and human review status/decision. Workflow history appends full
snapshots at pending human review and final decision, including user_request,
all three agent results, status and human_review (decision and reason when
available). Raw course evidence and service configuration/credentials are not
persisted. Keep requests and reasons free of secrets; snapshots contain their
text and model outputs. Keep these local files as assessment report evidence.

Worker references must identify supplied course codes or IDs. Validation
conservatively requires attribution for any nonblank answer with non-empty
evidence; it never guesses which course supports an answer. Reference validity
does not prove that a course supports each claim; Reviewer and human checks
still assess that. Empty evidence permits an empty attribution list.

Workflow outputs and decision reasons are held in memory in a single process.
Restarting clears reviewable workflows; rerun the request after a restart.
History retains completed snapshots, but this foundation does not reload them
into active workflows. Do not run multiple
WSGI processes against these files. The two log writes are not transactional;
a filesystem failure returns a structured error and can leave partial evidence.

## Verification

Use the existing development Python environment with Student 1 test dependencies:

```sh
python -m pytest student-1/tests rag-server/tests/test_student1_semantic.py -q
python -m pytest multi-agent-server/tests -q
python -m compileall -q multi-agent-server student-1/backend
node --check student-1/frontend/public/js/courses.js
```

Tests mock all model and HTTP calls and use temporary evidence files.
