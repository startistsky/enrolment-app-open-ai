import os
from pathlib import Path

from flask import Flask, jsonify, request

from coordinator import Coordinator, DECISIONS


def create_app(history_path=None, audit_path=None):
    app = Flask(__name__)
    base = Path(__file__).parent
    coordinator = Coordinator(
        history_path or os.getenv("WORKFLOW_HISTORY_PATH", base / "workflow_history.jsonl"),
        audit_path or os.getenv("COORDINATION_AUDIT_PATH", base / "coordination_audit.jsonl"),
    )
    app.extensions["coordinator"] = coordinator

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="multi-agent-server")

    @app.post("/workflow/course")
    def course_workflow():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Request body must be a JSON object"), 400
        user_request = body.get("user_request")
        if not isinstance(user_request, str) or not user_request.strip():
            return jsonify(error="user_request is required"), 400
        if body.get("feature") != "course_management":
            return jsonify(error="feature must be course_management"), 400
        evidence = body.get("evidence")
        if not isinstance(evidence, list) or any(not isinstance(row, dict) for row in evidence):
            return jsonify(error="evidence must be a list of course objects"), 400
        result, status = coordinator.run(user_request.strip(), evidence)
        return jsonify(result), status

    @app.post("/workflow/<workflow_id>/decision")
    def decision(workflow_id):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get("decision") not in DECISIONS:
            return jsonify(error="Invalid human decision"), 400
        reason = body.get("reason", "")
        if not isinstance(reason, str):
            return jsonify(error="reason must be a string"), 400
        result, status = coordinator.decide(workflow_id, body["decision"], reason.strip())
        return jsonify(result), status

    @app.get("/workflow/status")
    def status():
        return jsonify(workflows=coordinator.status())

    @app.errorhandler(OSError)
    def persistence_error(error):
        return jsonify(error="Workflow evidence could not be persisted"), 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9201)  # noqa: S104 -- intentional local Docker/host service ingress; not a public deployment.
