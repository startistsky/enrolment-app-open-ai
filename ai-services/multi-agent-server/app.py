
import os
from pathlib import Path

from flask import Flask, jsonify, request

from coordinator import Coordinator, DECISIONS

def create_app(history_path=None, audit_path=None):
    app = Flask(__name__)

    base = Path(__file__).parent

    coordinator = Coordinator(
        history_path or os.getenv(
            "WORKFLOW_HISTORY_PATH",
            base / "workflow_history.jsonl"
        ),
        audit_path or os.getenv(
            "COORDINATION_AUDIT_PATH",
            base / "coordination_audit.jsonl"
        ),
    )

    app.extensions["coordinator"] = coordinator

    # ============================================================
    # HEALTH CHECK
    # ============================================================

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            service="multi-agent-server"
        )

    # ============================================================
    # COURSE MANAGEMENT WORKFLOW - STUDENT 1
    # ============================================================

    @app.post("/workflow/course")
    def course_workflow():
        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify(
                error="Request body must be a JSON object"
            ), 400

        user_request = body.get("user_request")

        if not isinstance(user_request, str) or not user_request.strip():
            return jsonify(
                error="user_request is required"
            ), 400

        if body.get("feature") != "course_management":
            return jsonify(
                error="feature must be course_management"
            ), 400

        evidence = body.get("evidence")

        if not isinstance(evidence, list) or any(
            not isinstance(row, dict) for row in evidence
        ):
            return jsonify(
                error="evidence must be a list of course objects"
            ), 400

        result, status = coordinator.run(
            user_request.strip(),
            evidence,
            feature="course_management"
        )

        return jsonify(result), status

    # ============================================================
    # ASSIGNMENT MANAGEMENT WORKFLOW - STUDENT 2
    # ============================================================

    @app.post("/workflow/assignment")
    def assignment_workflow():
        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify(
                error="Request body must be a JSON object"
            ), 400

        user_request = body.get("user_request")

        if not isinstance(user_request, str) or not user_request.strip():
            return jsonify(
                error="user_request is required"
            ), 400

        if body.get("feature") != "assignment_management":
            return jsonify(
                error="feature must be assignment_management"
            ), 400

        evidence = body.get("evidence")

        if not isinstance(evidence, list) or any(
            not isinstance(row, dict) for row in evidence
        ):
            return jsonify(
                error="evidence must be a list of assignment objects"
            ), 400

        result, status = coordinator.run(
            user_request.strip(),
            evidence,
            feature="assignment_management"
        )

        return jsonify(result), status

    # ============================================================
    # EVENT MANAGEMENT WORKFLOW - STUDENT 4 (RELEASE 2)
    # ============================================================

    @app.post("/workflow/resource")
    def resource_workflow():
        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify(error="JSON object required"), 400

        user_request = body.get("user_request")
        evidence = body.get("evidence")
        feature = body.get("feature")

        if feature != "resource_management":
            return jsonify(error="feature must be resource_management"), 400

        if not isinstance(user_request, str) or not user_request.strip():
            return jsonify(error="user_request is required"), 400

        if not isinstance(evidence, list) or not all(
            isinstance(item, dict) for item in evidence
        ):
            return jsonify(error="evidence must be a list of objects"), 400

        result, status = coordinator.run(
            user_request.strip(),
            evidence,
            feature="resource_management",
        )
        return jsonify(result), status

    # career workflow
    @app.post("/workflow/career") 
    def careerworkflow(): 
        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify(error="Request body must be a JSON object"), 400

        user_request = body.get("user_request") 
        if not isinstance(user_request, str) or not user_request.strip(): 
            return jsonify(error="user_request is required"), 400

        if body.get("feature") != "career_management": 
            return jsonify(error="feature must be career_management"), 400

        selected_job = body.get("selected_job") 
        if not isinstance(selected_job, dict): 
            return jsonify(error="selected_job must be a job object"), 400

        job_id = selected_job.get("id") 
        if ( not isinstance(job_id, int) or isinstance(job_id, bool) or job_id <= 0 ): 
            return jsonify(error="selectedjob.id must be a positive integer"), 400

        for field in ("title", "company"): 
            value = selected_job.get(field) 
            if not isinstance(value, str) or not value.strip(): 
                return jsonify( error=f"selectedjob.{field} is required" ), 400

        career_details = body.get("careerdetails", {}) 
        if not isinstance(career_details, dict): 
            return jsonify(error="career_details must be a JSON object"), 400

        result, status = coordinator.run_career( user_request.strip(), selected_job, career_details, )

        return jsonify(result), status

    # human decision
    
    @app.post("/workflow/event")
    def event_workflow():
        """
        Run the Event Management Multi-Agent workflow:

        Planner -> Worker -> Reviewer -> Human Review
        """

        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            return jsonify(
                error="Request body must be a JSON object"
            ), 400

        user_request = body.get("user_request")

        if not isinstance(user_request, str) or not user_request.strip():
            return jsonify(
                error="user_request is required"
            ), 400

        if body.get("feature") != "event_management":
            return jsonify(
                error="feature must be event_management"
            ), 400

        evidence = body.get("evidence")

        if not isinstance(evidence, list) or any(
            not isinstance(row, dict) for row in evidence
        ):
            return jsonify(
                error="evidence must be a list of event objects"
            ), 400

        result, status = coordinator.run(
            user_request.strip(),
            evidence,
            feature="event_management"
        )

        return jsonify(result), status

    # ============================================================
    # HUMAN REVIEW - SHARED ACROSS ALL FEATURES
    # ============================================================

    @app.post("/workflow/<workflow_id>/decision")
    def decision(workflow_id):
        """
        Human reviewer can:

        Accept
        Partially Accept
        Reject
        """

        body = request.get_json(silent=True)

        if (
            not isinstance(body, dict)
            or body.get("decision") not in DECISIONS
        ):
            return jsonify(
                error="Invalid human decision"
            ), 400

        reason = body.get("reason", "")

        if not isinstance(reason, str):
            return jsonify(
                error="reason must be a string"
            ), 400

        result, status = coordinator.decide(
            workflow_id,
            body["decision"],
            reason.strip()
        )

        return jsonify(result), status

    # ============================================================
    # WORKFLOW STATUS
    # ============================================================

    @app.get("/workflow/status")
    def status():
        return jsonify(
            workflows=coordinator.status()
        )

    # ============================================================
    # ERROR HANDLING
    # ============================================================

    @app.errorhandler(OSError)
    def persistence_error(error):
        return jsonify(
            error="Workflow evidence could not be persisted"
        ), 503

    # IMPORTANT:
    # Return the Flask application AFTER registering all routes.
    return app


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

app = create_app()



if __name__ == "__main__":
    app.run(
        host="0.0.0.0",  # noqa: S104 -- intentional local development service binding
        port=9201
    )
