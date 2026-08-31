# Student 2 - Assignment Management

Assignment Management is Juncheng Pu's Release 0 feature. It provides an independent frontend, backend/API, and SQLite database service, plus local Ollama AI recommendations.

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
- Seed the assignments table with 10 records.

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
