# Student 1 – Course Management

**Student:** Yifan Dong  
**Release:** 0

Course Management is part of the SmartCampus AI application. It allows users to view, search, create, update, and delete university courses.

## Microservices

The feature uses three separate microservices:

- **Frontend:** HTML, CSS, JavaScript, and Nginx
- **Backend/API:** Flask API that validates requests and communicates with the database and AI services
- **Database:** Flask service with persistent SQLite storage

The frontend communicates with the backend API, and the backend communicates with the database microservice. The frontend never accesses SQLite directly.

## Course functionality

- View and search all courses
- View course details
- Create a course
- Update a course
- Delete a course
- Generate an AI course summary and practical study recommendations

Each course contains:

- `course_id`
- `course_code`
- `course_name`
- `lecturer`
- `semester`
- `credit_points`
- `course_description`

## AI Course Assistant

The backend uses the repository's shared Ollama service and the `qwen2.5:0.5b` model. For a selected course, the assistant generates a short course summary and three practical study recommendations.

## Docker and ports

All three Student 1 microservices are Dockerised.

| Service | Host port |
|---|---:|
| Course frontend | 8081 |
| Course backend/API | 8001 |
| Course database | 5001 |
| Shared Ollama | 11434 |
| Shared SmartCampus homepage | 8888 |

## Start with Docker Compose

From the repository root, build and start the required services:

```bash
docker compose up -d --build shared-frontend student1-frontend student1-backend student1-database ollama
```

Download the shared AI model the first time the application is started:

```bash
docker compose exec ollama ollama pull qwen2.5:0.5b
```

Open the shared SmartCampus homepage at:

```text
http://localhost:8888
```

Select **Course Management**, or open it directly at:

```text
http://localhost:8081
```

## Automated tests

Student 1 has pytest coverage for database health, seeded data, course CRUD, backend health, and backend request validation.

Install the test dependencies and run the tests from the repository root:

```bash
student-1/.venv/bin/pip install -r student-1/tests/requirements.txt
student-1/.venv/bin/python -m pytest student-1/tests -v
```

## Continuous integration

The Student 1 GitHub Actions workflow is located at:

```text
.github/workflows/student1-course-management-ci.yml
```

It checks Python dependencies and syntax, checks frontend JavaScript syntax, runs the pytest suite, and builds the three Student 1 Docker images without starting Ollama.
