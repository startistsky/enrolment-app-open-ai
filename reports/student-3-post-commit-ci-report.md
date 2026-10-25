# Student 3 Post-Commit CI Testing Report

## Verified GitHub Actions run

GitHub Actions reported the following Student 3 Campus Resource CI run as
successful:

| Item | Verified value |
|---|---|
| Workflow | Student 3 Campus Resource CI |
| Run | #94 |
| Event / branch | Pull request / `fix/student3-multi-agent-json` |
| Tested commit | `5651dc70fbea` (abbreviated) |
| Run URL | https://github.com/startistsky/enrolment-app-open-ai/actions/runs/40096233219 |
| Job result | Success |
| Run date | 24 October 2026 |

The run passed **40 automated tests**: 4 backend CI tests, 15 MCP/RAG tests,
8 Resource Agent tests and 13 Resource Workflow tests. Dependency and syntax
checks, Compose validation, and all three Student 3 image builds also passed.
This was a pull-request run, not a post-merge run. It tested the identified
historical commit only and does **not** validate the current uncommitted shared
review changes.

Earlier Release 2 Resource Management Run #64 remains available as historical
evidence:
https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39031065295
It passed its then-configured CI steps on commit `a5087adbc36b` (abbreviated)
on 17 October 2026. Run #94 supersedes it for recency and test coverage.

## Separately recorded local checks (not GitHub Actions evidence)

The following checks were recorded locally and are not post-commit CI evidence:

- Student 3 backend CI tests plus the Resource workflow API tests: **17 passed**.
- Resource Agent regression tests: **8 passed**.
- Configured Ruff checks for Student 3, Resource agents, coordinator and the
  shared review files: **passed**.

The dependency scan found four distinct unresolved ChromaDB advisories. Their
raw and gated statuses and temporary acceptance rationale are documented in
[`student-3-pre-commit-security-report.md`](./student-3-pre-commit-security-report.md).

## Endpoint evidence and scope

Run #94's backend CI tests exercise the Student 3 backend CI test module. Its
Multi-Agent workflow tests exercise the shared Resource workflow and human
decision routes; they do not directly establish that both Student 3 backend
proxy routes were exercised. Separate functional evidence is:

- `POST /api/multi-agent/resource`: the Azure BONUS deployment run below
  exercised this backend route and recorded `PASS: B4 Multi-Agent Human Review`.
  The health check verifies the response reaches `pending_human_review`; it does
  not by itself verify a completed human decision.
- `POST /api/multi-agent/<workflow_id>/decision`: the previously supplied
  completed Azure workflow record `c39713bc-d471-41ba-9a59-dbca4b3d341e`
  reported a completed human decision. Its Azure history/audit export is not
  present in this workspace; the workflow identifier and result are retained
  here as user-supplied evidence, not as a CI test log.

The locally available JSONL history contains a separate completed Resource
workflow (`9789c1ed-9f2d-4d4d-aaa9-d1a7e482af37`) with a `Partially Accept`
decision. It is local workflow evidence and is not labelled as Azure evidence.

```json
{
  "review_evidence": {
    "feature": "resource_management",
    "branch": "fix/student3-multi-agent-json",
    "commit": "5651dc70fbea (abbreviated)",
    "workflow": "Student 3 Campus Resource CI",
    "run_number": 94,
    "run_date": "2026-10-24",
    "run_url": "https://github.com/startistsky/enrolment-app-open-ai/actions/runs/40096233219",
    "workflow_result": "succeeded",
    "trigger_event": "pull_request",
    "automated_test_count": 40,
    "automated_test_breakdown": {
      "student3_backend_ci": 4,
      "mcp_rag": 15,
      "resource_agent": 8,
      "resource_workflow": 13
    },
    "endpoint_tests": {
      "POST /api/multi-agent/resource": "PASS",
      "POST /api/multi-agent/<workflow_id>/decision": "PASS"
    },
    "endpoint_test_sources": {
      "POST /api/multi-agent/resource": {
        "kind": "Azure BONUS functional health check",
        "run_url": "https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39369577924",
        "result": "Started a Resource workflow and verified pending_human_review"
      },
      "POST /api/multi-agent/<workflow_id>/decision": {
        "kind": "Previously supplied completed Azure workflow record",
        "workflow_id": "c39713bc-d471-41ba-9a59-dbca4b3d341e",
        "limitation": "No associated Azure history/audit export is present in this workspace"
      }
    },
    "steps": {
      "Check Python dependencies": "succeeded",
      "Check Python syntax": "succeeded",
      "Run automated tests": "succeeded",
      "Run Student 3 R2 Multi-Agent tests": "succeeded",
      "Run Student 3 Resource Workflow tests": "succeeded",
      "Validate Docker Compose": "succeeded",
      "Build Student 3 database": "succeeded",
      "Build Student 3 backend": "succeeded",
      "Build Student 3 frontend": "succeeded"
    },
    "historical_run_64": {
      "run_url": "https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39031065295",
      "commit": "a5087adbc36b (abbreviated)",
      "run_date": "2026-10-17"
    },
    "local_test_results": {
      "student3_backend_and_resource_workflow_tests": "17 passed",
      "resource_agent_regression_tests": "8 passed",
      "configured_ruff": "PASS"
    },
    "security_report": "reports/student-3-pre-commit-security-report.md",
    "ci_evidence_limitation": "Run 94 is a historical pull-request run for commit 5651dc70fbea; it does not include the current uncommitted shared review changes and is not post-merge CI evidence"
  }
}
```
