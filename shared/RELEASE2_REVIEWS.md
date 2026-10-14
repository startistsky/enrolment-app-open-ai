# Shared local Release 2 evidence reviews

The CLI remains a local tool. Release 1 `mcp`, `rag` and `all` retain their
original live validation purpose; `all` does not invoke Release 2 reviews.

Run from the repository root using the existing backend/MCP Python dependencies:

```sh
python shared/agentic_loop.py --mode testing-review \
  --security-report reports/student-1-pre-commit-security-report.md \
  --ci-report reports/student-1-post-commit-ci-report.md \
  --output agentic-review-logs/testing-review-summary.json
python shared/agentic_loop.py --mode multi-agent-review \
  --workflow-history ai-services/multi-agent-server/workflow_history.jsonl \
  --coordination-audit ai-services/multi-agent-server/coordination_audit.jsonl
python shared/agentic_loop.py --mode cloud-review \
  --cloud-report reports/cloud-deployment-report.md
```

Each Release 2 execution uses PLAN → ACT → OBSERVE → REVIEW → ADAPT and appends
a JSON record to `agentic-review-logs/<mode>.jsonl`. `--log-dir` changes that
location; `--output` optionally writes a formatted JSON summary. PASS and
PASS_WITH_WARNINGS exit 0; FAIL exits 1. Generated logs contain checks and source
paths, not raw report text, course evidence, model output or credentials. Keep
source paths free of credentials. The default runtime directory is ignored by Git.

Multi-Agent Review correlates full snapshots and audit events by workflow ID,
checks ordered timestamped stages and a final human decision (including Reject),
and requires evidence attribution when evidence_count is positive. Earlier failed,
pending and legacy metadata-only attempts do not invalidate a later successful
complete record. Attribution presence can be checked, but grounding cannot be
reconstructed without the original supplied evidence, which the logs omit.
To complete current evidence, run a live course workflow, inspect its three
agent results and submit your actual human decision through the frontend. Then
rerun the review; the tool never supplies a human decision.

Testing and Cloud reviews accept a JSON object or a Markdown report containing
one fenced `json` block with a `review_evidence` object. This explicit structured
summary avoids interpreting unrelated occurrences of words such as PASS in prose.
Missing/unstructured/malformed reports fail. The supplied testing reports include
such summaries based on their documented evidence. Extra fields are ignored;
required fields must have the specified values. Reviews validate documented
reports, not independent cloud reachability or GitHub authenticity.

Testing summary fields: security `ruff`, `detect_secrets`, `pip_audit_raw`,
`pip_audit_gate` with PASS/FAIL values; `unresolved_findings` is an array with
`advisory_id`, `accepted`, `resolved`, `rationale`, `mitigation`. Accepted findings
must remain `resolved: false`. CI fields include `commit`, `run_url`,
`workflow_result: "succeeded"`, `endpoint_tests` mapping the two exact POST routes
to PASS, and `steps` mapping the CI step names to `succeeded`. Missing required
controls or endpoint evidence fails; missing optional build/full-suite details
warns, while documented failures fail.

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
