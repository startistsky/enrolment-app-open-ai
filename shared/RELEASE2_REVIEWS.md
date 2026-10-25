# Shared local Release 2 evidence reviews

The CLI remains a local tool. Release 1 `mcp`, `rag` and `all` retain their
original live validation purpose; `all` does not invoke Release 2 reviews.

Run from the repository root. Release 2 evidence reviews use the standard
library and shared review module; the Release 1 MCP and RAG modes additionally
require their service-client dependencies.

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

Multi-Agent Review supports the implemented feature identifiers
`course_management`, `assignment_management`, `resource_management`,
`event_management` and `career_management`. It correlates full snapshots and
audit events by workflow ID, checks matching feature identifiers, ordered
timestamped stages and a final human decision (including Reject), and requires
evidence attribution when `evidence_count` is positive. Earlier failed, pending
and legacy metadata-only attempts do not invalidate a later successful complete
record. Attribution presence can be checked, but grounding cannot be
reconstructed without the original supplied evidence, which the logs omit.
The tool never supplies a human decision.

Testing and Cloud reviews accept a JSON object or a Markdown report containing
one fenced `json` block with a `review_evidence` object. This explicit structured
summary avoids interpreting unrelated occurrences of words such as PASS in prose.
Missing/unstructured/malformed reports fail. Extra fields are ignored; required
fields must have the specified values. Reviews validate documented reports, not
independent cloud reachability or GitHub authenticity.

Testing summary fields: security `ruff`, `sensitive_data_scan`,
`pip_audit_raw`, and `pip_audit_gate` with PASS/FAIL values. If both scan-status
fields are present, they must agree. `unresolved_findings` is a required array, empty when the raw
audit passes and containing every finding when it fails. Each finding requires
`advisory_id`, `accepted`, `resolved`, `rationale`, and `mitigation`. Raw PASS
with listed findings and raw FAIL with no listed findings fail validation.
Accepted findings must remain `resolved: false`; a PASS raw audit cannot be
paired with unresolved findings. CI fields include `commit`, `run_url`,
`workflow_result: "succeeded"`, `endpoint_tests` mapping the selected feature's
actual backend routes to PASS, and `steps` mapping the corresponding CI step
names to `succeeded`. Set CI `feature` to one of the five identifiers above.
Reports without `feature` retain the legacy Student 1-compatible endpoint and
step profile. Missing required controls, endpoint evidence or test steps fails;
documented failures fail. The review does not independently verify run URLs or
test results. The CLI `--feature` option selects the same profile and rejects a
conflicting `feature` value in the supplied CI report.

Cloud reports select `deployment_profile` as `baseline` or `bonus`; omission
retains the baseline profile. Both profiles require platform, frontend, backend
API, database connectivity and successful deployment run evidence.

The baseline profile additionally requires `crud_validation`,
`persistence_configuration`, `persistence_validation` (all PASS),
`.github/workflows/cloud-deployment.yml`, all four
`disabled_by_default` controls (`ai_mode`, `mcp`, `rag`, `multi_agent`) set to
true, and an accepted human release approval with a valid ISO-8601 timestamp
including a timezone. Missing approval remains a validation failure. This
release approval is separate from a Multi-Agent workflow's Human Review.
Enabled baseline AI services fail validation.

The Azure BONUS profile instead requires
`.github/workflows/azure-bonus-deployment.yml`, PASS evidence for `ollama`,
`mcp`, `rag` and `multi_agent`, and `bonus_configuration` that explicitly
enables `ai_services_enabled`, identifies `qwen2.5:0.5b`, and supplies
credential-free service URLs matching the Student 3 BONUS Compose integration:
`http://ollama:11434/api/generate`, `http://mcp-server:9001/mcp`,
`http://rag-server:9101` and `http://multi-agent-server:9201`. BONUS evidence
does not claim CRUD, persistence or final human release approval: if these items
are absent, the review reports warnings and returns PASS_WITH_WARNINGS when all
required BONUS evidence is otherwise valid. An accepted release decision with
an invalid timestamp fails validation; missing approval remains a warning.
This approval is separate from a Multi-Agent workflow's Human Review. A documented failure in those
controls or a non-Accept human decision fails the review. Enabled BONUS services
are not rejected by the baseline disabled-by-default rule.
The CLI `--deployment-profile bonus` option selects this profile and rejects a
conflicting profile declared in the report.

Populate every field only from actual test, deployment and approval evidence.
The review validates supplied reports but does not query GitHub or Azure and
cannot turn historical prose into verified results.

Verification:

```sh
python -m pytest shared/tests ai-services/multi-agent-server/tests student-1/tests rag-server/tests/test_student1_semantic.py -q
python -m compileall -q shared ai-services/multi-agent-server student-1/backend
pre-commit run --all-files
```

Testing reports may use the earlier underscore-form status field or the
canonical `sensitive_data_scan` field. If both are present, their values must
agree. The canonical field avoids secret-keyword scanning ambiguity while
preserving support for existing reports.

## Azure assessment preparation

The selected cloud platform is Microsoft Azure. See [Azure deployment](../docs/AZURE_DEPLOYMENT.md)
for the manual VM baseline workflow and required real deployment evidence.
Repository preparation is not deployment evidence. Do not run Cloud Deployment
Review as a release approval until the selected profile's required deployment,
functional and approval evidence has been supplied. No cloud report is
generated by the preparation scripts.
