# Student 3 — Release 2 Evidence Report

## 1. Feature Overview

Student 3 is responsible for Campus Resource Management in the Student Enrolment Application.

Release 2 extends the existing resource management functionality with an independent multi-agent workflow, integrating resource evidence, AI-assisted recommendations, human review, automated testing and CI validation.

The workflow is exposed through `/workflow/resource` in the shared Multi-Agent Server and is integrated with the Student 3 backend through `/api/multi-agent/resource`.

## 2. Multi-Agent Architecture

The Resource Management workflow follows:

**Planner → Worker → Reviewer → Human Decision**

- **Planner Agent:** Analyses the user's resource request and prepares a plan.
- **Worker Agent:** Identifies matching resources using database evidence and provides grounded recommendations.
- **Reviewer Agent:** Reviews the Worker's output for unsupported claims, incorrect resource IDs and other risks.
- **Human Reviewer:** Makes the final Accept, Partially Accept or Reject decision.

The system does not automatically approve the AI recommendation. Human review is required before the workflow is marked completed.

## 3. Live Multi-Agent Workflow Evidence

Two Resource Management workflows were completed with recorded human decisions.

| Workflow ID | Status | Human Decision |
|---|---|---|
| bcfd1fc0-c3a3-4775-8740-ee6fc875a5f4 | Completed | Partially Accept |
| a8415e45-6b67-4f35-ae6f-bc858950785d | Completed | Accept |

### Workflow 1 — Partially Accept

The Worker produced resource recommendations grounded in database evidence. However, the Planner included irrelevant resources, and the Reviewer incorrectly reported that resource IDs were missing.

The human reviewer selected **Partially Accept** because the recommendations were useful but the agent outputs contained issues requiring correction.

### Workflow 2 — Accept

The resource recommendations were checked against database evidence, including resource IDs, capacity and availability.

The human reviewer selected **Accept** after verifying the relevant resource information.

These two decisions demonstrate human oversight rather than automatic acceptance of AI-generated recommendations.

## 4. Persistent JSONL Evidence

The Multi-Agent Server records workflow information in:

- `ai-services/multi-agent-server/workflow_history.jsonl`
- `ai-services/multi-agent-server/coordination_audit.jsonl`

The local evidence inspection identified:

| Evidence | Count |
|---|---:|
| Resource workflow history records | 8 |
| Resource coordination audit events | 36 |
| Completed resource workflows with human decisions | 2 |

Both completed workflows contain the following ordered audit events:

1. `started`
2. `planner_completed`
3. `worker_completed`
4. `reviewer_completed`
5. `human_review_pending`
6. `human_decision`

The history includes pending and completed snapshots, while the audit trail records the coordination events and human decisions.

Earlier pending workflows and a model error were also retained as part of the development and testing history.

## 5. Automated Testing

Student 3 maintains two Resource Multi-Agent test files:

| Test File | Tests | Result |
|---|---:|---|
| `test_resource_agents.py` | 8 | PASS |
| `test_student3_resource_workflow.py` | 9 | PASS |
| **Total** | **17** | **PASS** |

The Agent Regression Tests cover resource classification, availability and capacity matching, evidence grounding, invalid resource IDs and Reviewer validation.

The Workflow API Tests cover agent execution order, pending human review, all three human decisions, invalid requests, invalid decisions, duplicate decision prevention and JSONL persistence.

The Workflow API Tests use mocked agents to validate orchestration without depending on a live Ollama model.

## 6. GitHub Actions CI Evidence

The Student 3 CI workflow is configured in:

`.github/workflows/student-3.yml`

The GitHub Actions run completed successfully on 17 October 2026.

**CI Result: SUCCESS**

- 8 Resource Agent Regression Tests passed.
- 9 Resource Workflow API Tests passed.
- The Student 3 CI job completed successfully.

GitHub Actions Evidence:

https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39006775584

The CI workflow also includes MCP/RAG automated tests, dependency checks, Docker Compose validation and Student 3 Docker image builds.

## 7. Security and Quality Gates

Before committing the Resource Workflow tests and CI configuration, the following checks passed:

- Ruff code quality checks
- Ruff security checks
- Detect Secrets
- Dependency Audit
- Git diff validation

The Resource Workflow tests were committed in `f3ecbd0`.

The CI configuration was updated in `d950da0`.

## 8. Limitations and Improvements

During live testing, the Planner sometimes included irrelevant resources, and the Reviewer incorrectly reported missing resource IDs.

These issues demonstrated the importance of grounding agent responses in database evidence and retaining human approval authority.

Additional regression tests were developed to verify resource matching, invalid IDs and Reviewer false-positive handling.

The automated tests confirm the expected workflow behaviour under controlled conditions. They do not independently establish the reliability of every live model response.

Cloud deployment validation and final presentation evidence should be documented separately after testing the deployed Student 3 application.

## 9. Summary

Student 3 Release 2 delivers an independent Resource Management Multi-Agent workflow with evidence-grounded recommendations, Reviewer validation, mandatory human approval and persistent JSONL audit records.

Two live workflows were completed with recorded human decisions, and 17 Multi-Agent automated tests passed in GitHub Actions.

Together, these results provide evidence of workflow orchestration, human oversight, testing and CI integration.

## 10. Release 2 Additional Validation — 17 October 2026

Additional live integration testing and debugging were performed on the Student 3 Resource Management application.

### RAG Recommendation Accuracy

A live RAG request was tested using:

`Find an available study room for 6 students`

The initial response included incorrect availability claims and confused room capacity with the number of available rooms.

The Student 3 backend was improved to validate availability and capacity against live database records before returning recommendations for availability-specific requests.

The final verified response was:

> Building 11 Study Room 1 is currently available and can accommodate 6 students. Location: Building 11, Level 4.

The response included the citation:

`campus_resources.txt#Building-11-Study-Room-1`

The availability-specific response uses verified database values rather than allowing the LLM to generate unsupported capacity or availability claims.

**Result: PASS**

## 11. Resource Type Detection Bug Fix

During live AI Recommendation testing, the request:

`Find an available study room for 6 students`

incorrectly detected both `Computer Lab` and `Study Room`.

### Root Cause

The keyword `lab` was matched as a substring of `available`, causing a false-positive Computer Lab classification.

### Correction

The backend resource type detection logic was updated so the standalone keyword `lab` requires an exact word match.

### Regression Testing

| Test Scenario | Expected Result | Status |
|---|---|---|
| Available study room | Study Room | PASS |
| Computer lab | Computer Lab | PASS |
| Study room or computer lab | Both types | PASS |
| Available computer lab | Computer Lab | PASS |

Four automated regression cases were added in:

`student-3/tests/test_resource_type_detection.py`

**Result: 4/4 PASS**

## 12. Updated Automated Testing and Code Quality

The complete Student 3 test suite was executed locally after the changes.

Command:

`python -m pytest student-3/tests/ -v`

**Result: 35 passed in 26.23 seconds**

The RAG integration suite included 11 passing tests, including a new regression test verifying that Busy resources are excluded from availability-specific recommendations and that capacity is described correctly.

Code quality command:

`ruff check student-3/backend/app.py student-3/tests/`

**Result: All checks passed!**

These results are local validation evidence. The earlier GitHub Actions CI result remains separately documented in Section 6.

## 13. Additional Live Multi-Agent and Human Review Evidence

A new Resource Management workflow was executed on 17 October 2026.

**Workflow ID:** `9789c1ed-9f2d-4d4d-aaa9-d1a7e482af37`

**User Request:** Find an available study room for 6 students.

**Database Evidence:** 10 campus resources.

### Agent Execution

| Component | Evidence | Result |
|---|---|---|
| Planner | Identified resource IDs 2 and 8 | Completed |
| Worker | Recommended available resources with verified capacities | Completed |
| Reviewer | Reviewed evidence and returned correction guidance | Completed |
| Human Review | Partially Accept | Completed |
| Overall Workflow | Final status completed | PASS |

The Worker recommended:

- Building 11 Study Room 1: ID 2, capacity 6, Available.
- Building 1 Quiet Study Area: ID 8, capacity 20, Available.

The human reviewer selected **Partially Accept** because the dedicated Study Room should be prioritised over the open study area.

### Persistent Workflow History

Two snapshots were verified in:

`ai-services/multi-agent-server/workflow_history.jsonl`

| Snapshot | Workflow Status | Human Review |
|---|---|---|
| Before decision | pending_human_review | pending |
| After decision | completed | Partially Accept |

### Coordination Audit Trail

Six ordered events were verified in:

`ai-services/multi-agent-server/coordination_audit.jsonl`

1. `started`
2. `planner_completed`
3. `worker_completed`
4. `reviewer_completed`
5. `human_review_pending`
6. `human_decision`

The audit record confirmed:

- `feature`: resource_management
- `evidence_count`: 10
- `planner_completion_source`: model
- `worker_completion_source`: model
- `human_review_status`: completed
- `human_decision`: Partially Accept
- `status`: completed

The Workflow Status API independently confirmed that the workflow was completed.

An earlier failed workflow also remained visible in the status history and was not counted as a successful workflow.

**Result: PASS — Live Multi-Agent Execution, Human Review and Persistent Audit Evidence verified.**

## 14. Updated Validation Summary

| Validation Area | Result |
|---|---|
| Resource CRUD and Database | Previously validated |
| MCP Integration | PASS |
| RAG Recommendation | PASS |
| RAG Regression Tests | 11/11 PASS |
| Resource Type Regression Tests | 4/4 PASS |
| Full Student 3 Automated Test Suite | 35/35 PASS |
| Ruff Code Quality | PASS |
| Multi-Agent Workflow | PASS |
| Human-in-the-Loop Review | PASS |
| Workflow History and Audit Persistence | PASS |
| Existing GitHub Actions CI | SUCCESS — previously recorded |

The additional testing demonstrates iterative debugging, evidence-grounded recommendations, regression testing, mandatory human oversight and auditable workflow execution.

The latest local changes still require Git review and a new CI run after they are committed and pushed.
