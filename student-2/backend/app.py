import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from rag_client import retrieve_assignment_context


DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://localhost:5002",
).rstrip("/")

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b",
)

REQUEST_TIMEOUT = int(
    os.getenv("REQUEST_TIMEOUT", "30")
)


app = Flask(__name__)
CORS(app)


def database_request(method, path, **kwargs):
    """Forward a request to the Student 2 database service."""

    try:
        response = requests.request(
            method,
            f"{DATABASE_SERVICE_URL}{path}",
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )

    except requests.RequestException as exc:
        return jsonify({
            "error": "Database service is unavailable",
            "details": str(exc),
        }), 503

    if response.status_code == 204:
        return "", 204

    try:
        response_data = response.json()

    except ValueError:
        return jsonify({
            "error": "Invalid response from database service",
            "status_code": response.status_code,
        }), 502

    return jsonify(response_data), response.status_code


def priority_rank(priority):
    """Convert an assignment priority into a sortable number."""

    ranks = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    return ranks.get(
        str(priority).strip().lower(),
        3,
    )


def progress_value(progress):
    """Convert progress into a safe integer value."""

    try:
        return int(progress)

    except (TypeError, ValueError):
        return 0


def assignment_sort_key(assignment):
    """
    Sort active assignments by:

    1. Priority.
    2. Earliest due date.
    3. Lowest progress.
    """

    return (
        priority_rank(
            assignment.get("priority")
        ),
        str(
            assignment.get(
                "due_date",
                "9999-12-31",
            )
        ),
        progress_value(
            assignment.get("progress")
        ),
    )


@app.get("/health")
def health():
    """Return the health status of the Student 2 backend."""

    return jsonify({
        "status": "healthy",
        "service": "student-2-backend",
    })


@app.get("/api/assignments")
def list_assignments():
    """Return assignments using the supplied filters."""

    return database_request(
        "GET",
        "/assignments",
        params=request.args,
    )


@app.get("/api/assignments/<int:assignment_id>")
def get_assignment(assignment_id):
    """Return one assignment by ID."""

    return database_request(
        "GET",
        f"/assignments/{assignment_id}",
    )


@app.post("/api/assignments")
def create_assignment():
    """Create a new assignment."""

    return database_request(
        "POST",
        "/assignments",
        json=request.get_json(silent=True) or {},
    )


@app.put("/api/assignments/<int:assignment_id>")
def update_assignment(assignment_id):
    """Update an existing assignment."""

    return database_request(
        "PUT",
        f"/assignments/{assignment_id}",
        json=request.get_json(silent=True) or {},
    )


@app.delete("/api/assignments/<int:assignment_id>")
def delete_assignment(assignment_id):
    """Delete an assignment."""

    return database_request(
        "DELETE",
        f"/assignments/{assignment_id}",
    )


@app.post("/api/ai/recommendations")
def recommend_priorities():
    """
    Generate a grounded assignment plan using:

    1. Current assignment records.
    2. Evidence from the shared RAG server.
    3. The configured Ollama language model.
    """

    payload = request.get_json(silent=True) or {}

    student_id = str(
        payload.get("student_id", "")
    ).strip()

    if not student_id:
        return jsonify({
            "error": "student_id is required",
        }), 400

    # Load the student's assignments.
    try:
        assignments_response = requests.get(
            f"{DATABASE_SERVICE_URL}/assignments",
            params={
                "student_id": student_id,
                "sort": "priority",
            },
            timeout=REQUEST_TIMEOUT,
        )

        assignments_response.raise_for_status()
        assignments = assignments_response.json()

    except requests.RequestException as exc:
        return jsonify({
            "error": "Could not load assignments",
            "details": str(exc),
        }), 503

    except ValueError as exc:
        return jsonify({
            "error": "Invalid assignment database response",
            "details": str(exc),
        }), 502

    if not isinstance(assignments, list):
        return jsonify({
            "error": "Invalid assignment database response",
            "details": "Expected a list of assignments",
        }), 502

    # Exclude completed assignments.
    active = [
        item
        for item in assignments
        if isinstance(item, dict)
        and item.get("status") != "Completed"
    ]

    if not active:
        return jsonify({
            "recommendation": (
                "All assignments are complete. Review upcoming "
                "subjects and prepare the next study block."
            ),
            "model": OLLAMA_MODEL,
            "assignment_count": 0,
            "rag": {
                "used": False,
                "query": "",
                "match_count": 0,
                "citations": [],
            },
            "workflow": {
                "plan": "Review the current workload",
                "act": "No urgent assignment action is required",
                "observe": "All assignments are completed",
                "adapt": "Prepare for future assignments",
            },
        })

    # Sort the workload using deterministic backend logic.
    active = sorted(
        active,
        key=assignment_sort_key,
    )

    top_assignment = active[0]

    top_assignment_line = (
        f"{top_assignment.get('assignment_title', 'Untitled')} | "
        f"{top_assignment.get('subject_name', 'Unknown subject')} | "
        f"due {top_assignment.get('due_date', 'Unknown')} | "
        f"{top_assignment.get('priority', 'Unknown')} priority | "
        f"{top_assignment.get('progress', 0)}% complete | "
        f"{top_assignment.get('status', 'Unknown status')}"
    )

    # Obtain the RAG query supplied by the frontend.
    rag_query = str(
        payload.get(
            "query",
            "What high priority assignments should I work on first?",
        )
    ).strip()

    if not rag_query:
        rag_query = (
            "What high priority assignments "
            "should I work on first?"
        )

    rag_result = retrieve_assignment_context(
        rag_query,
        top_k=min(
            max(len(active), 3),
            10,
        ),
    )

    rag_matches = []

    if (
        isinstance(rag_result, dict)
        and not rag_result.get(
            "insufficient_context",
            True,
        )
    ):
        rag_matches = [
            match
            for match in rag_result.get(
                "matches",
                [],
            )
            if isinstance(match, dict)
        ]

    # Remove duplicate RAG matches.
    unique_matches = []
    seen_source_ids = set()

    for match in rag_matches:
        source_id = str(
            match.get("source_id", "")
        ).strip()

        if not source_id:
            context = match.get(
                "context",
                {},
            )

            if isinstance(context, dict):
                source_id = str(
                    context.get(
                        "assignment_id",
                        "",
                    )
                ).strip()

        if not source_id:
            continue

        if source_id in seen_source_ids:
            continue

        seen_source_ids.add(source_id)
        unique_matches.append(match)

    # Limit evidence supplied to the small local model.
    unique_matches = unique_matches[:5]

    rag_context_lines = []
    rag_citations = []

    for match in unique_matches:
        context = match.get(
            "context",
            {},
        )

        if not isinstance(context, dict):
            continue

        context_student_id = str(
            context.get("student_id", "")
        ).strip()

        # Do not include evidence belonging to another student.
        if context_student_id != student_id:
            continue

        citation = str(
            match.get(
                "citation",
                "Assignment record",
            )
        ).strip()

        assignment_title = context.get(
            "assignment_title",
            "Untitled",
        )

        subject_name = context.get(
            "subject_name",
            "Unknown subject",
        )

        due_date = context.get(
            "due_date",
            "Unknown",
        )

        priority = context.get(
            "priority",
            "Unknown",
        )

        progress = context.get(
            "progress",
            0,
        )

        status = context.get(
            "status",
            "Unknown status",
        )

        evidence_line = (
            f"- [{citation}] "
            f"{assignment_title} | "
            f"{subject_name} | "
            f"due {due_date} | "
            f"{priority} priority | "
            f"{progress}% complete | "
            f"{status}"
        )

        rag_context_lines.append(
            evidence_line
        )

        rag_citations.append(
            citation
        )

    if rag_context_lines:
        retrieved_context = "\n".join(
            rag_context_lines
        )

    else:
        retrieved_context = (
            "No additional RAG matches were available."
        )

    # Format the complete active workload.
    assignment_lines = []

    for item in active:
        assignment_lines.append(
            f"- Assignment ID "
            f"{item.get('assignment_id', 'Unknown')} | "
            f"{item.get('assignment_title', 'Untitled')} | "
            f"{item.get('subject_name', 'Unknown subject')} | "
            f"due {item.get('due_date', 'Unknown')} | "
            f"{item.get('priority', 'Unknown')} priority | "
            f"{item.get('progress', 0)}% complete | "
            f"{item.get('status', 'Unknown status')}"
        )

    prompt = """You are a university assignment planning assistant.
Use the Plan -> Act -> Observe -> Adapt loop.

Use only facts contained in the supplied assignment data and retrieved RAG evidence.
Never invent assignments, deadlines, priorities, subjects, progress, status,
users, teams, dependencies, or technical capabilities.

Copy every assignment fact exactly as supplied.
A High-priority assignment must never be described as Low or Medium priority.
A Medium-priority assignment must never be described as High or Low priority.
A Low-priority assignment must never be described as High or Medium priority.

Do not claim that an assignment is unassigned to a user or team.
Do not discuss information that is absent from the supplied data.
Do not add an introduction or concluding paragraph.
Do not create a Supporting Assignment Citations section.
Verified citations will be added by the backend.

The backend has already calculated the required top-priority assignment.
You must use this exact assignment as the Top Priority:

""" + top_assignment_line + """

Follow this exact output structure:

1. Top Priority
Repeat the required top-priority assignment exactly and provide one short
explanation based only on its priority, due date, progress, and status.

2. Suggested Next Three Actions
Provide exactly three numbered actions.
Do not provide more or fewer than three actions.

3. Time-management Advice
Provide exactly three concise bullet points.
Do not provide more or fewer than three bullet points.

4. What to Observe and How to Adapt
Provide exactly three concise bullet points.
Do not provide more or fewer than three bullet points.

Retrieved RAG evidence:
""" + retrieved_context + """

Complete active assignment data:
""" + "\n".join(assignment_lines)

    # Send the grounded prompt to Ollama.
    try:
        ai_response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=REQUEST_TIMEOUT,
        )

        ai_response.raise_for_status()
        ai_data = ai_response.json()

        recommendation = str(
            ai_data.get("response", "")
        ).strip()

    except requests.RequestException as exc:
        return jsonify({
            "error": "Local AI service is unavailable",
            "details": str(exc),
            "hint": (
                f"Start Ollama and install "
                f"{OLLAMA_MODEL}."
            ),
        }), 503

    except ValueError as exc:
        return jsonify({
            "error": "Invalid response from local AI service",
            "details": str(exc),
        }), 502

    if not recommendation:
        return jsonify({
            "error": (
                "The local AI service returned "
                "an empty response"
            ),
        }), 502

    # Add citations deterministically after generation.
    if rag_context_lines:
        recommendation += (
            "\n\nSupporting Assignment Citations:\n"
            + "\n".join(rag_context_lines)
        )

    return jsonify({
        "recommendation": recommendation,
        "model": OLLAMA_MODEL,
        "assignment_count": len(active),
        "top_assignment": {
            "assignment_id": top_assignment.get(
                "assignment_id"
            ),
            "assignment_title": top_assignment.get(
                "assignment_title"
            ),
            "subject_name": top_assignment.get(
                "subject_name"
            ),
            "due_date": top_assignment.get(
                "due_date"
            ),
            "priority": top_assignment.get(
                "priority"
            ),
            "progress": top_assignment.get(
                "progress"
            ),
            "status": top_assignment.get(
                "status"
            ),
        },
        "rag": {
            "used": bool(
                rag_context_lines
            ),
            "query": rag_query,
            "match_count": len(
                rag_context_lines
            ),
            "citations": rag_citations,
        },
        "workflow": {
            "plan": (
                "Retrieve grounded assignment context "
                "and rank the active workload"
            ),
            "act": (
                "Generate a structured study plan "
                "with the local LLM"
            ),
            "observe": (
                f"Reviewed {len(active)} active assignments "
                f"and {len(rag_context_lines)} RAG matches"
            ),
            "adapt": (
                "Update the plan when assignment progress, "
                "priority, or deadlines change"
            ),
        },
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8002,
    )