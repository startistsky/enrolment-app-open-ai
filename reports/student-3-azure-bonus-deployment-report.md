# Student 3 Azure BONUS Deployment Evidence

**Profile:** Azure BONUS B1–B4. This report distinguishes verified deployment
and functional evidence from configuration-only items and missing assessment
evidence. It does not claim complete Student 3 CRUD, persistence verification,
or group human release approval.

## Confirmed Azure deployments

### Student 3 BONUS B1–B4 run

The successful second attempt of Azure BONUS run #1 deployed commit
`f75e64ac987d` (abbreviated) on 20 October 2026:

https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39369577924

The successful job logs contain these checks:

- Backend health passed.
- B2 MCP passed.
- B1 Ollama recommendation passed and checked the configured model.
- B3 RAG grounded retrieval passed.
- B4 Multi-Agent passed its pending-human-review response check.
- The B1–B4 health-check marker and Student 3 deployment success marker were
  recorded.
- A Student 3 `/resources` read was checked after the B1–B4 health check.

The B4 deployment check starts a workflow and verifies that human review is
required and pending. It does not perform the human decision.

### Baseline frontend/backend/database checks

The successful Azure Cloud Baseline run #4 on 19 October 2026 checked the
Student 3 frontend, backend, database-backed resource read, and deployment
health:

https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39263904008

The Action log reports `Frontend 8083: reachable`, a healthy Student 3 backend
and database, and `Database-backed read 8083/resources: reachable`. The same
log explicitly says these health/read checks do **not** prove full CRUD writes
or human release approval.

### Later run not used as BONUS functional proof

Azure BONUS run #3 completed successfully on 21 October 2026 at commit
`5200a242ecb8f341f27ea89d364940b19b8f9fb6`:

https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39578906701

Its available log includes the baseline `GROUP5_DEPLOYMENT_HEALTH_PASSED`
marker, but not the B1–B4 functional markers. This report therefore does not
use that run as evidence that B1–B4 were reverified.

## Configuration versus runtime evidence

The successful Student 3 BONUS run checked out commit
`f75e64ac987d` (abbreviated). The Compose files at that exact
commit configure Student 3 with AI services enabled, Ollama `qwen2.5:0.5b`, and
MCP, RAG, and Multi-Agent service URLs. The BONUS Compose file also defines
persistent named volumes for Ollama, Chroma/RAG, and Multi-Agent data; the cloud
Compose file defines `student3-resource-data`.

Those volumes are **configuration evidence only**. No Student 3 persistence
test across container recreation is established here. The deployment logs
contain a read check, not full create/read/update/delete evidence. The group's
final human release approval is not documented in the available reports.

The local workflow JSONL files contain completed Resource workflow
`9789c1ed-9f2d-4d4d-aaa9-d1a7e482af37` with a `Partially Accept` decision and
ordered audit events. Those records are local and are not represented as Azure
workflow history. A previously supplied Azure workflow identifier
`c39713bc-d471-41ba-9a59-dbca4b3d341e` was described as completed with Human
Review, but its Azure history/audit export is not present in this workspace.
Application workflow Human Review is not the same as group release approval.

```json
{
  "review_evidence": {
    "deployment_profile": "bonus",
    "platform": "Azure",
    "frontend_access": "PASS",
    "backend_api_access": "PASS",
    "database_connectivity": "PASS",
    "deployment_workflow_result": "succeeded",
    "deployment_run_url": "https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39369577924",
    "workflow_file": ".github/workflows/azure-bonus-deployment.yml",
    "deployment_commit": "f75e64ac987d (abbreviated)",
    "bonus_services": {
      "ollama": "PASS",
      "mcp": "PASS",
      "rag": "PASS",
      "multi_agent": "PASS"
    },
    "bonus_configuration": {
      "ai_services_enabled": true,
      "ollama_model": "qwen2.5:0.5b",
      "service_urls": {
        "ollama": "http://ollama:11434/api/generate",
        "mcp": "http://mcp-server:9001/mcp",
        "rag": "http://rag-server:9101",
        "multi_agent": "http://multi-agent-server:9201"
      },
      "source": "docker-compose.cloud.yml and docker-compose.bonus.yml at deployment commit f75e64ac987d (abbreviated)"
    },
    "crud_validation": "MISSING",
    "persistence_configuration": "PASS",
    "persistence_validation": "MISSING",
    "evidence_notes": {
      "crud": "Deployment performed a Student 3 /resources read only; no create, update, or delete validation is established.",
      "persistence": "Named volumes are configured; persistence across recreation was not tested in the supplied evidence.",
      "human_release_approval": "MISSING; no final group release decision or completion timestamp was supplied.",
      "bonus_health_check": "B4 check verified pending_human_review, not a completed human decision.",
      "later_run": "Run 39578906701 succeeded but its available logs did not contain B1-B4 functional markers."
    }
  }
}
```
