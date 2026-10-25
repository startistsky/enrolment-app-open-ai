# Shared local Release 2 evidence reviews

The CLI remains a local tool. Release 1 `mcp`, `rag` and `all` retain their
original live validation purpose; `all` does not invoke Release 2 reviews.

Run from the repository root using the existing backend/MCP Python dependencies:

```sh
python shared/agentic_loop.py --mode testing-review --student 1 \
  --output agentic-review-logs/student-1-testing-review-summary.json
python shared/agentic_loop.py --mode testing-review --student 2 \
  --output agentic-review-logs/student-2-testing-review-summary.json
python shared/agentic_loop.py --mode testing-review --student 3 \
  --output agentic-review-logs/student-3-testing-review-summary.json
python shared/agentic_loop.py --mode testing-review --student 4 \
  --output agentic-review-logs/student-4-testing-review-summary.json
python shared/agentic_loop.py --mode testing-review --student 5 \
  --output agentic-review-logs/student-5-testing-review-summary.json
python shared/agentic_loop.py --mode testing-review --student all \
  --security-report reports/testing-review-security-report.json \
  --ci-report reports/testing-review-ci-report.json
python shared/agentic_loop.py --mode multi-agent-review \
  --workflow-history ai-services/multi-agent-server/workflow_history.jsonl \
  --coordination-audit ai-services/multi-agent-server/coordination_audit.jsonl \
  --student all
python shared/agentic_loop.py --mode cloud-review \
  --student all --cloud-report reports/cloud-deployment-report.md
```

Each Release 2 execution uses PLAN → ACT → OBSERVE → REVIEW → ADAPT and appends
a JSON record to `agentic-review-logs/<mode>.jsonl`. `--log-dir` changes that
location; `--output` optionally writes a formatted JSON summary. PASS and
PASS_WITH_WARNINGS exit 0; FAIL exits 1. Generated logs contain checks and source
paths, not raw report text, course evidence, model output or credentials. Keep
source paths free of credentials. The default runtime directory is ignored by Git.

The pre-commit security hook also writes its Markdown results to
`agentic-review-logs/pre-commit-security-report.md`, including raw scanner output
and the separate dependency gate result. This local report is regenerated on each
run and is intentionally ignored by Git.
The structured Testing Review evidence JSON files are excluded from Detect
Secrets input: their public commit hashes and security-status field names trigger
scanner false positives, and these files contain review evidence rather than
credentials. The per-student post-commit CI Markdown reports are excluded for
the same reason: their public commit hashes are test-run identifiers, not
secrets. These reports are still validated by the deterministic review tool.

Multi-Agent Review correlates full snapshots and audit events by workflow ID,
checks ordered timestamped stages and a final human decision (including Reject),
and checks evidence attribution for course, assignment, resource, event and
career workflows (Students 1-5). `--student 1` through `--student 5` scopes the
review to one student; the default `--student all` passes only when each
student has at least one complete workflow. Earlier failed, pending and legacy
metadata-only attempts do not invalidate a later successful complete record.
Attribution presence can be checked, but grounding cannot be reconstructed
without the original supplied evidence, which the logs omit. Run each real
student workflow, inspect its three agent results and submit the actual human
decision through the frontend before expecting an all-students PASS; the tool
never supplies human decisions.

Testing and Cloud reviews accept a JSON object or a Markdown report containing
one fenced `json` block with a `review_evidence` object. Missing, unstructured,
or malformed reports fail. Reviews validate documented evidence, not independent
cloud reachability or GitHub authenticity.

For `testing-review`, `--student 1` through `--student 5` selects a student's
security and CI evidence. The default remains Student 1 for compatibility.
`--student all` requires both reports to contain a `students` object keyed by
the CI report; security can instead be one report explicitly scoped with
`"scope": "all students"` (or `"all"` / `"repository"`). Each student must have
passing security controls, a successful CI run, both of that student's exact
Multi-Agent POST endpoints, and the workflow's test step. Single-student reports
must identify their student (`"student": "N"`); legacy flat Student 1 reports
without that field remain accepted. Each CI object uses `commit`, `run_url`,
`workflow_result: "succeeded"`, `endpoint_tests` with both endpoint values set
to `"PASS"`, and `steps` with that student's required step set to `"succeeded"`.
Required controls and endpoint/test-step evidence fail closed; missing optional
image-build details warn, and documented failures fail. For single-student
review, the CLI uses the combined all-student JSON files when both are present;
otherwise, its default report paths are
`reports/student-N-pre-commit-security-report.md` and
`reports/student-N-post-commit-ci-report.md`. For all students, provide the
combined JSON report files explicitly. For example:

The commands above use the combined JSON evidence files when available. They
contain the successful workflow records and local endpoint test results
collected for this checkout. The per-student Markdown files are fallback inputs;
a successful GitHub workflow alone does not create those local reports.

```json
{
  "students": {
    "1": {
      "commit": "actual-commit",
      "run_url": "actual-CI-run-URL",
      "workflow_result": "succeeded",
      "endpoint_tests": {
        "POST /api/multi-agent/course-workflow": "PASS",
        "POST /api/multi-agent/course-workflow/<workflow_id>/decision": "PASS"
      },
      "steps": {"Post-commit endpoint tests": "succeeded"}
    }
  }
}
```

Use the exact endpoint pair and required test-step name in
`shared/release2_reviews.py` for each student; do not copy Student 1's keys for
other students. Security objects additionally require `ruff`, `detect_secrets`,
`pip_audit_gate`, and `pip_audit_raw` statuses plus `unresolved_findings`.

For `cloud-review`, `--student 1` through `--student 5` checks the selected
student's `frontend_access`, `backend_api_access`, `database_connectivity`,
`crud_validation`, and `persistence_validation` fields. `--student all`
requires those fields under a
`students` object for every student. Deployment workflow, platform, disabled
service configuration, and human release approval remain group-wide fields.
The default remains Student 1 for compatibility.

An all-student cloud report keeps group-wide fields at the top level and nests
the five per-student validation fields:

```json
{
  "platform": "Azure",
  "deployment_workflow_result": "succeeded",
  "deployment_run_url": "actual-deployment-run-URL",
  "workflow_file": ".github/workflows/cloud-deployment.yml",
  "disabled_by_default": {"ai_mode": true, "mcp": true, "rag": true, "multi_agent": true},
  "human_release_decision": "Accept",
  "human_review_completed_at": "actual-review-timestamp",
  "students": {
    "1": {
      "frontend_access": "PASS",
      "backend_api_access": "PASS",
      "database_connectivity": "PASS",
      "crud_validation": "PASS",
      "persistence_validation": "PASS"
    }
  }
}
```

The example shows the required shape only: a real `--student all` report must
include entries for Students 1–5, populated from actual validation evidence.

No real cloud report is created by this task. A future report must document:
`platform` (AWS/Azure); `frontend_access`, `backend_api_access`,
`database_connectivity`, `crud_validation` (PASS); `deployment_workflow_result`
(succeeded), `deployment_run_url`; `workflow_file`
(`.github/workflows/cloud-deployment.yml`); `disabled_by_default` with `ai_mode`,
`mcp`, `rag`, `multi_agent` all true; `human_release_decision` (Accept), and
`human_review_completed_at`. Populate those fields only after real deployment
and human approval. Enabled baseline AI services fail validation.

Verification:

```sh
python -m pytest shared/tests ai-services/multi-agent-server/tests student-1/tests rag-server/tests/test_student1_semantic.py -q
python -m compileall -q shared ai-services/multi-agent-server student-1/backend
pre-commit run --all-files
```

The secret baseline includes a reviewed report-only false positive for the
`detect_secrets` PASS status field. It is scanner outcome metadata, not a credential.

## Azure assessment preparation

The selected cloud platform is Microsoft Azure. See [Azure deployment](../docs/AZURE_DEPLOYMENT.md)
for the manual VM baseline workflow and required real deployment evidence.
Repository preparation is not deployment evidence. Do not run Cloud Deployment
Review as a release approval until the Azure deployment, CRUD checks, disabled
AI controls and human review have been evidenced. No cloud report is generated
by the preparation scripts.
