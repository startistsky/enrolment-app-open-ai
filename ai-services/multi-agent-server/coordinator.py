import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4


from agents import planner_agent, worker_agent, reviewer_agent
from llm_client import ModelError

DECISIONS = ["Accept", "Partially Accept", "Reject"]

class Coordinator:
    """Sequential execution with workflow snapshots and concise audit evidence.

    Reviewable workflows stay in memory; after restart clients must run again.
    This local foundation runs in one process, with serialized log/decision writes.
    """
    def __init__(self, history_path, audit_path):
        self.history_path = Path(history_path)
        self.audit_path = Path(audit_path)
        self.workflows = {}
        self.user_requests = {}
        self.worker_completion_sources = {}
        self.planner_completion_sources = {}
        self.lock = RLock()

    def record(self, workflow, event):
        row = {
            "workflow_id": workflow["workflow_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feature": workflow["feature"], "event": event,
            "participating_agents": ["planner", "worker", "reviewer"],
            "status": workflow["status"],
            "evidence_count": workflow["evidence_count"],
            **{f"{role}_status": workflow[f"{role}_status"] for role in ("planner", "worker", "reviewer")},
            "human_review_status": workflow["human_review"]["status"],
            "human_decision": workflow["human_review"].get("decision"),
        }
        source = self.worker_completion_sources.get(workflow["workflow_id"])
        if source:
            row["worker_completion_source"] = source
        planner_source = self.planner_completion_sources.get(workflow["workflow_id"])
        if planner_source:
            row["planner_completion_source"] = planner_source
        # Audit excludes application content; history captures completed review states.
        # Do not persist raw evidence, service configuration or credentials.
        with self.lock:
            with self.audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row) + "\n")
            if event in ("human_review_pending", "human_decision"):
                snapshot = {
                    "workflow_id": workflow["workflow_id"],
                    "timestamp": row["timestamp"], "feature": workflow["feature"],
                    "status": workflow["status"],
                    "user_request": self.user_requests[workflow["workflow_id"]],
                    "evidence_count": workflow["evidence_count"],
                    **{f"{role}_result": workflow[f"{role}_result"]
                       for role in ("planner", "worker", "reviewer")},
                    "human_review": workflow["human_review"],
                }
                if planner_source:
                    snapshot["planner_completion_source"] = planner_source
                if source:
                    snapshot["worker_completion_source"] = source
                with self.history_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(snapshot) + "\n")

    def run(self, user_request, evidence):
        workflow = {
            "workflow_id": str(uuid4()), "feature": "course_management",
            "status": "running", "evidence_count": len(evidence),
            "human_review": {"required": True, "status": "pending",
                             "allowed_decisions": DECISIONS.copy()},
            **{f"{role}_status": "pending" for role in ("planner", "worker", "reviewer")},
        }
        with self.lock:
            self.workflows[workflow["workflow_id"]] = workflow
            self.user_requests[workflow["workflow_id"]] = user_request
        self.record(workflow, "started")
        for role, agent in (("planner", planner_agent), ("worker", worker_agent), ("reviewer", reviewer_agent)):
            args = [user_request, evidence]
            if role != "planner":
                args.append(workflow["planner_result"])
            if role == "reviewer":
                args.append(workflow["worker_result"])
            try:
                result = agent.run(*args)
            except ModelError as exc:
                with self.lock:
                    workflow[f"{role}_status"] = "failed"
                    workflow["status"] = "failed"
                    workflow["human_review"]["status"] = "unavailable"
                    workflow["error"] = str(exc)
                    workflow["failed_agent"] = role
                    self.record(workflow, "model_error")
                    return copy.deepcopy(workflow), exc.status
            with self.lock:
                if role == "planner":
                    self.planner_completion_sources[workflow["workflow_id"]] = getattr(result, "completion_source", "model")
                if role == "worker":
                    self.worker_completion_sources[workflow["workflow_id"]] = getattr(result, "completion_source", "model")
                workflow[f"{role}_result"] = dict(result)
                workflow[f"{role}_status"] = "completed"
                self.record(workflow, f"{role}_completed")
        with self.lock:
            workflow["status"] = "pending_human_review"
            self.record(workflow, "human_review_pending")
            return copy.deepcopy(workflow), 200

    def decide(self, workflow_id, decision, reason):
        with self.lock:
            workflow = self.workflows.get(workflow_id)
            if workflow is None:
                return {"error": "Workflow not found; run again if the server restarted"}, 404
            if workflow["status"] != "pending_human_review" or workflow["reviewer_status"] != "completed":
                return {"error": "Workflow is not awaiting human review"}, 409
            updated = copy.deepcopy(workflow)
            updated["status"] = "completed"
            updated["human_review"].update(status="completed", decision=decision, reason=reason)
            self.record(updated, "human_decision")
            self.workflows[workflow_id] = updated
            return copy.deepcopy(updated), 200

    def status(self):
        with self.lock:
            return [{"workflow_id": w["workflow_id"], "status": w["status"],
                     "human_review_status": w["human_review"]["status"]}
                    for w in self.workflows.values()]

    def run_career(self, user_request, selected_job, career_details=None):
        """Run the career planner, worker, and reviewer sequentially."""

        career_details = career_details or {}

        workflow = {
            "workflow_id": str(uuid4()),
            "feature": "careermanagement",
            "status": "running",
            "evidence_count": 1 + int(bool(career_details)),
            "human_review": {
                "required": True,
                "status": "pending",
                "allowed_decisions": DECISIONS.copy(),
            },
            **{f"{role}_status": "pending" for role in ("planner", "worker", "reviewer")},
        }

        workflow_id = workflow["workflow_id"]

        with self.lock:
            self.workflows[workflow_id] = workflow
            self.user_requests[workflow_id] = user_request

        self.record(workflow, "started")

        agents = (
            ("planner", planner_agent),
            ("worker", worker_agent),
            ("reviewer", reviewer_agent),
        )

        for role, agent in agents:
            try:
                if role == "planner":
                    result = agent.run_career(user_request, selected_job, career_details)
                elif role == "worker":
                    result = agent.run_career(
                        user_request,
                        selected_job,
                        career_details,
                        planner_result=workflow["planner_result"],
                    )
                else:
                    result = agent.run_career(
                        user_request,
                        selected_job,
                        career_details,
                        planner_result=workflow["planner_result"],
                        worker_result=workflow["worker_result"],
                    )
            except (ModelError, ValueError) as exc:
                with self.lock:
                    workflow[f"{role}_status"] = "failed"
                    workflow["status"] = "failed"
                    workflow["human_review"]["status"] = "unavailable"
                    workflow["error"] = str(exc)
                    workflow["failed_agent"] = role
                    self.record(workflow, "model_error")
                status = exc.status if isinstance(exc, ModelError) else 400
                return copy.deepcopy(workflow), status

            with self.lock:
                if role == "planner":
                    self.planner_completion_sources[workflow_id] = getattr(result, "completion_source", "model")
                elif role == "worker":
                    self.worker_completion_sources[workflow_id] = getattr(result, "completion_source", "model")

                workflow[f"{role}_result"] = dict(result)
                workflow[f"{role}_status"] = "completed"
                self.record(workflow, f"{role}_completed")

        with self.lock:
            workflow["status"] = "pending_human_review"
            self.record(workflow, "human_review_pending")

        return copy.deepcopy(workflow), 200
