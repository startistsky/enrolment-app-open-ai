# Student 2 - Assignment Management

Assignment Management is Juncheng Pu's feature. Release 2 preserves the independent frontend, backend/API and SQLite database service, and adds a local Planner → Worker → Reviewer workflow with mandatory human review.

## Structure

```text
student-2/
├── frontend/        Static HTML/CSS/JavaScript UI served by Nginx
├── backend/         Flask REST API and Ollama integration
├── database/        Flask database service, SQLite schema and 10 seed records
└── docker-compose.yml
```

## Implemented functions

- Dashboard totals, upcoming deadlines, active work, and average progress.
- Create, read, update, and delete assignments.
- Filter by student, status, and priority; sort by deadline, priority, progress, or creation time.
- Update Not Started, In Progress, and Completed states and 0-100% progress.
- Validate required fields, priority, status, and progress in the database service.
- Generate workload recommendations with Ollama/Qwen using Plan -> Act -> Observe -> Adapt.
- Run a grounded Assignment Management Multi-Agent workflow using current database records.
- Review Planner, Worker and Reviewer output before selecting Accept, Partially Accept or Reject.
- Seed the assignments table with 10 records.

## Run the Release 2 workflow locally

From the repository root, start the required containers:

```bash
docker compose up -d --build student2-database student2-backend student2-frontend ollama ollama-init
docker compose exec ollama ollama pull llama3.1:8b
```

In a separate terminal, install and start the shared non-containerised server:

```bash
python -m venv .venv-multi-agent
.venv-multi-agent/Scripts/python -m pip install -r ai-services/multi-agent-server/requirements.txt
.venv-multi-agent/Scripts/python ai-services/multi-agent-server/app.py
```

On macOS/Linux, replace `.venv-multi-agent/Scripts/python` with
`.venv-multi-agent/bin/python`. Keep the server terminal open and visit
`http://localhost:8082`.

## Run with Docker

From the repository root:

```bash
docker compose -f student-2/docker-compose.yml up --build
```

Open `http://localhost:8082`. The backend API is available at `http://localhost:8002`, and the database service at `http://localhost:5004`.

Install the configured model once if needed:

```bash
docker compose -f student-2/docker-compose.yml exec ollama ollama pull qwen2.5:0.5b
```

Stop the services with:

```bash
docker compose -f student-2/docker-compose.yml down
```

Use `down -v` only when you intentionally want to delete the persisted assignment data and reseed it.

## API summary

- `GET /api/assignments`
- `GET /api/assignments/<id>`
- `POST /api/assignments`
- `PUT /api/assignments/<id>`
- `DELETE /api/assignments/<id>`
- `POST /api/ai/recommendations`
- `POST /api/multi-agent/assignment-workflow`
- `POST /api/multi-agent/assignment-workflow/<workflow_id>/decision`
