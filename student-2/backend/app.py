import os

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5002")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

app = Flask(__name__)
CORS(app)


def database_request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            f"{DATABASE_SERVICE_URL}{path}",
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        return jsonify({"error": "Database service is unavailable", "details": str(exc)}), 503

    if response.status_code == 204:
        return "", 204
    return jsonify(response.json()), response.status_code


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "service": "student-2-backend"})


@app.get("/api/assignments")
def list_assignments():
    return database_request("GET", "/assignments", params=request.args)


@app.get("/api/assignments/<int:assignment_id>")
def get_assignment(assignment_id):
    return database_request("GET", f"/assignments/{assignment_id}")


@app.post("/api/assignments")
def create_assignment():
    return database_request("POST", "/assignments", json=request.get_json(silent=True) or {})


@app.put("/api/assignments/<int:assignment_id>")
def update_assignment(assignment_id):
    return database_request(
        "PUT", f"/assignments/{assignment_id}", json=request.get_json(silent=True) or {}
    )


@app.delete("/api/assignments/<int:assignment_id>")
def delete_assignment(assignment_id):
    return database_request("DELETE", f"/assignments/{assignment_id}")


@app.post("/api/ai/recommendations")
def recommend_priorities():
    payload = request.get_json(silent=True) or {}
    student_id = str(payload.get("student_id", "")).strip()
    if not student_id:
        return jsonify({"error": "student_id is required"}), 400

    try:
        assignments_response = requests.get(
            f"{DATABASE_SERVICE_URL}/assignments",
            params={"student_id": student_id, "sort": "priority"},
            timeout=REQUEST_TIMEOUT,
        )
        assignments_response.raise_for_status()
        assignments = assignments_response.json()
    except requests.RequestException as exc:
        return jsonify({"error": "Could not load assignments", "details": str(exc)}), 503

    active = [item for item in assignments if item["status"] != "Completed"]
    if not active:
        return jsonify({"recommendation": "All assignments are complete. Review upcoming subjects and plan your next study block.", "workflow": {"plan": "Review workload", "act": "No urgent action", "observe": "All work completed", "adapt": "Prepare for future tasks"}})

    lines = [
        f"- {item['assignment_title']} | {item['subject_name']} | due {item['due_date']} | {item['priority']} priority | {item['progress']}% complete"
        for item in active
    ]
    prompt = """You are a university assignment planning assistant. Use the Plan -> Act -> Observe -> Adapt loop.
Prioritise the student's assignments using due dates, stated priority, progress, and workload.
Return a concise plan with: 1) Top priority, 2) Suggested next three actions, 3) Time-management advice, 4) What to observe and how to adapt.
Do not invent assignment facts. Assignment data:\n""" + "\n".join(lines)

    try:
        ai_response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT,
        )
        ai_response.raise_for_status()
        recommendation = ai_response.json().get("response", "").strip()
    except requests.RequestException as exc:
        return jsonify({
            "error": "Local AI service is unavailable",
            "details": str(exc),
            "hint": f"Start Ollama and install {OLLAMA_MODEL}.",
        }), 503

    return jsonify({
        "recommendation": recommendation,
        "model": OLLAMA_MODEL,
        "assignment_count": len(active),
        "workflow": {
            "plan": "Analyse deadlines, priorities, progress, and workload",
            "act": "Generate an ordered study plan with the local LLM",
            "observe": f"Reviewed {len(active)} active assignments",
            "adapt": "Update priorities when progress or deadlines change",
        },
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
