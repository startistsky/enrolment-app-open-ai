# Group 5 Cloud Deployment Evidence Report

**Overall status: INCOMPLETE — all-student Cloud Review currently FAILS; this report does not establish final release approval.**

Evidence sources: verified Azure workflow runs and live HTTP checks performed
on 25 October 2026. Live checks covered frontend access, backend health,
temporary CRUD records, and safe AI/MCP/RAG/Multi-Agent probes for Students
1–5. All temporary CRUD records were deleted. No service-recreation
persistence check, Azure redeployment or human release decision was performed
in this validation pass.

## 1. Verified group infrastructure evidence

| Item | Verified value |
| --- | --- |
| Platform | Microsoft Azure |
| Resource group | `asd-group5-rg` |
| Deployment region | `eastasia` |
| VM | `asd-group5-vm` |
| VM size | `Standard_B2s_v2` |
| VM capacity | 2 vCPUs, 8 GiB RAM |
| Baseline deployment branch/ref | `main` |
| Baseline deployed commit | `25a902c2243f46437cfd59556f2ab57631c603b6` |
| Baseline workflow | Azure Cloud Baseline Deployment |
| Baseline workflow file | `.github/workflows/cloud-deployment.yml` |
| Baseline deployment run | [GitHub Actions run 39263904008](https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39263904008) |
| Baseline workflow result | Success |
| Latest BONUS workflow | Azure Students 3 and 5 Bonus Deployment |
| BONUS branch/ref and commit | `main`, `5200a242ecb8f341f27ea89d364940b19b8f9fb6` |
| BONUS run/result | [GitHub Actions run 39578906701](https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39578906701), Success |
| VM start run | [GitHub Actions run 40171824203](https://github.com/startistsky/enrolment-app-open-ai/actions/runs/40171824203) |

Verified workflow evidence:

- Azure OIDC authentication succeeded.
- Cloud configuration validation succeeded.
- VM deployment and configuration succeeded.
- Docker Compose deployment succeeded.
- Health checks passed.
- `GROUP5_DEPLOYMENT_HEALTH_PASSED` was recorded.
- All deployed frontend/backend/database containers were reported healthy.

The latest successful deployment workflow is the BONUS deployment, not the
baseline workflow. The structured Cloud Review evidence below still references
the baseline run, so it must not be interpreted as proof that the current live
runtime has baseline-only controls.

Public frontend URLs supplied with the deployment evidence:

| Frontend | URL |
| --- | --- |
| Shared home | [Shared home](http://20.205.47.155:8888) |
| Student 1 Courses | [Courses](http://20.205.47.155:8081) |
| Student 2 Assignments | [Assignments](http://20.205.47.155:8082) |
| Student 3 Resources | [Resources](http://20.205.47.155:8083) |
| Student 4 Events | [Events](http://20.205.47.155:8080) |
| Student 5 Career | [Career](http://20.205.47.155:8085) |

All five frontend roots and backend `/health` endpoints returned HTTP 200 during
the live validation. The CRUD results below independently verify the API-to-
database path for each student.

## 2. Verified Student 1 cloud evidence

### CRUD through the deployed Courses frontend

Create, read/list, update and delete operations were each verified through the
[deployed Student 1 Courses frontend](http://20.205.47.155:8081).
Each operation passed. This conclusion applies to Student 1 only.

### Persistence across container recreation

A temporary course with code `PERSIST101` and name `Persistence Test` was created.
The Student 1 database, backend and frontend containers were force-recreated.
The course remained present after recreation, establishing persistence PASS for
Student 1. The temporary course was subsequently removable.

No specific commands, record IDs or timestamps are asserted because those details
were not supplied.

### Verified AI-disabled endpoint responses

| Service control | Method | Deployed endpoint | Verified result |
| --- | --- | --- | --- |
| MCP | GET | `http://20.205.47.155:8081/api/mcp/course-count` | HTTP 503 |
| RAG | POST | `http://20.205.47.155:8081/api/rag/course` | HTTP 503 |
| Multi-Agent | POST | `http://20.205.47.155:8081/api/multi-agent/course-workflow` | HTTP 503 |

All three requests returned the same verified JSON response:

```json
{"error":"AI, MCP, RAG and Multi-Agent services are disabled in this deployment"}
```

This is verified disabled-response evidence for those three Student 1 endpoints.
It does not assert separate AI Mode endpoint testing or equivalent endpoint tests
for Student 2–5.

## 3. Live Student 1–5 CRUD evidence

At `2026-10-25T07:13:46Z` the final student check completed. For each student, a
uniquely named temporary record was created, read, updated and deleted through
the deployed API. Every temporary record was removed. The actual HTTP results
were:

| Student | Frontend root | Backend `/health` | Create | Read | Update | Delete | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 200 | 200 | 201 | 200 | 200 | 200 | PASS |
| 2 | 200 | 200 | 201 | 200 | 200 | 204 | PASS |
| 3 | 200 | 200 | 201 | 200 | 200 | 200 | PASS |
| 4 | 200 | 200 | 201 | 200 (collection) | 200 | 200 | PASS |
| 5 | 200 | 200 | 201 | 200 | 200 | 200 | PASS |

Student 4 exposes collection-read rather than item-read; the created event was
confirmed in the collection both before and after update. Database connectivity
is established by successful persisted create/read/update/delete operations, not
by the health response alone.

Persistence across service/container recreation remains independently verified
only for Student 1 by the earlier `PERSIST101` test. Students 2–5 are still
PENDING for persistence; volume declarations in Compose are configuration
evidence, not a substitute for observing data after recreation. The user
declined the requested group restart because it would interrupt all five sites,
so no recreation was attempted and no live data was changed beyond the
temporary CRUD records, which were deleted.

## 4. Cloud-control remediation and deployment status

The latest BONUS run completed successfully on `main` and overlays AI
integrations. Safe live probes show the current runtime is mixed rather than
uniformly baseline-disabled: Student 1 AI/MCP/RAG, Student 2 AI/Multi-Agent,
Student 4 AI/MCP/RAG, and Student 5 AI returned HTTP 503; Student 3 MCP
returned HTTP 200, while its AI, RAG and Multi-Agent empty-payload probes
returned HTTP 400 validation responses. Student 4 and Student 5 Multi-Agent
empty-payload probes also returned HTTP 400. These requests did not start valid
workflows or modify data. The Student 3 MCP result confirms at least one
integration is active in the current runtime.

For the **baseline** profile, source changes now set Student 4's
`MULTI_AGENT_ENABLED=false`, apply Student 5's disabled-service guard to both
blueprints, and add regression coverage for all discovered AI/Multi-Agent
routes. The focused cloud/student tests pass (19 passed), and rendered baseline
Compose configuration validates. Those source changes have **not** been
deployed to Azure.

Cloud Review currently has baseline-only assumptions: `cloud-deployment.yml`
must be the reviewed workflow and AI/MCP/RAG/Multi-Agent must all be disabled.
The most recent successful Azure run is the BONUS workflow, which has different
service expectations. The current live environment must not be declared a
baseline pass, nor should a baseline redeployment overwrite the BONUS setup
without a chosen target profile and a data-preservation plan.

## 5. Pending group human release review

The group human release review is PENDING. No final Accept, Partially Accept or
Reject decision, completed review timestamp or release approval was supplied.
This report does not infer approval from workflow success or Student 1 test results.

## 6. All-student Cloud Deployment Review result

The all-student Cloud Deployment Review ran against baseline-shaped evidence
and returned FAIL. CRUD and service access now pass for all five students, but
persistence for Students 2–5, a consistent deployment profile, and final human
release approval remain outstanding. The checker must not be represented as
PASS until the profile is resolved and all required evidence is verified.

The review was run at `2026-10-25T07:20:23Z` using
`python shared/agentic_loop.py --mode cloud-review --student all`. It recognized
the frontend, backend, database and CRUD evidence for every student, and
returned **FAIL** for these exact remaining gaps:

- Persistence has not been verified after service/container recreation for
  Students 2–5.
- The latest BONUS runtime is not uniformly disabled: Student 3's MCP probe
  returned HTTP 200. The local baseline fixes are not deployed, and Cloud
  Review's baseline-only workflow requirement does not match the latest BONUS
  deployment.
- Final human release approval is still pending.

The machine-readable result is [cloud-review-all-result.json](./cloud-review-all-result.json);
the appended run is recorded in `agentic-review-logs/cloud-review.jsonl`.

## Evidence Status

PASS means the specific evidence was verified and supplied. PENDING means the
required evidence or review has not yet been supplied or completed.

| Evidence item | Status | Basis / remaining work |
| --- | --- | --- |
| GitHub Actions baseline deployment run | PASS | Run 39263904008 on `main`: Success; baseline commit recorded above |
| Latest BONUS deployment run | PASS | Run 39578906701 on `main`: Success; this is the latest deployment workflow |
| Azure OIDC authentication | PASS | Verified workflow evidence |
| Cloud configuration validation | PASS | Verified workflow evidence |
| VM deployment and configuration | PASS | Verified workflow evidence |
| Docker Compose deployment | PASS | Verified workflow evidence |
| Deployment health checks | PASS | Verified workflow evidence |
| Deployment success marker | PASS | `GROUP5_DEPLOYMENT_HEALTH_PASSED` recorded |
| Deployed container health | PASS | Frontend/backend/database containers reported healthy |
| Student 1 create | PASS | Performed through deployed Courses frontend |
| Student 1 read/list | PASS | Performed through deployed Courses frontend |
| Student 1 update | PASS | Performed through deployed Courses frontend |
| Student 1 delete | PASS | Performed through deployed Courses frontend |
| Student 1 persistence | PASS | `PERSIST101` remained after force-recreating its three containers |
| Student 1 temporary persistence course removability | PASS | Temporary course was subsequently removable |
| Student 1 MCP disabled response | PASS | Verified GET returned HTTP 503 and disabled JSON |
| Student 1 RAG disabled response | PASS | Verified POST returned HTTP 503 and disabled JSON |
| Student 1 Multi-Agent disabled response | PASS | Verified POST returned HTTP 503 and disabled JSON |
| Student 2 CRUD | PASS | Temporary assignment create/read/update/delete verified; record removed |
| Student 2 persistence | PENDING | No verified results supplied |
| Student 3 CRUD | PASS | Temporary resource create/read/update/delete verified; record removed |
| Student 3 persistence | PENDING | No verified results supplied |
| Student 4 CRUD | PASS | Temporary event create/collection-read/update/delete verified; record removed |
| Student 4 persistence | PENDING | No verified results supplied |
| Student 5 CRUD | PASS | Temporary job create/read/update/delete verified; record removed |
| Student 5 persistence | PENDING | No verified results supplied |
| Student 1–5 frontend/API/database access | PASS | Root and health returned HTTP 200; CRUD passed for each student |
| Baseline disabled-service runtime evidence | PENDING | Latest BONUS deployment differs; live Student 3 MCP returned HTTP 200 |
| Full Group 5 CRUD/persistence completion | PENDING | Student 2–5 persistence evidence outstanding |
| Group human release review and final approval | PENDING | No final decision or completed review supplied |
| Final Group 5 Cloud Deployment Review | FAIL | All-student check ran at 2026-10-25T07:20:23Z; see exact outstanding evidence above |

## Structured Cloud Review Evidence

This block records baseline-review statuses. `PENDING` means evidence is not
established; it must not be treated as a pass. Live reachability and CRUD
statuses reflect the 25 October 2026 validation. Persistence for Students 2–5,
a consistent deployment profile, and human approval remain pending.

## Current Validation Attempt

On 25 October 2026, live frontend, health and CRUD probes succeeded for all five
students; each temporary record was deleted. AI/MCP/RAG/Multi-Agent probes
showed mixed behavior documented above. No container recreation, redeployment
or final human decision was performed.

```json
{
  "review_evidence": {
    "platform": "Azure",
    "deployment_workflow_result": "succeeded",
    "deployment_run_url": "https://github.com/startistsky/enrolment-app-open-ai/actions/runs/39263904008",
    "workflow_file": ".github/workflows/cloud-deployment.yml",
    "disabled_by_default": {
      "ai_mode": "PENDING",
      "mcp": "PENDING",
      "rag": "PENDING",
      "multi_agent": "PENDING"
    },
    "human_release_decision": "PENDING",
    "students": {
      "1": {
        "frontend_access": "PASS",
        "backend_api_access": "PASS",
        "database_connectivity": "PASS",
        "crud_validation": "PASS",
        "persistence_validation": "PASS"
      },
      "2": {
        "frontend_access": "PASS",
        "backend_api_access": "PASS",
        "database_connectivity": "PASS",
        "crud_validation": "PASS",
        "persistence_validation": "PENDING"
      },
      "3": {
        "frontend_access": "PASS",
        "backend_api_access": "PASS",
        "database_connectivity": "PASS",
        "crud_validation": "PASS",
        "persistence_validation": "PENDING"
      },
      "4": {
        "frontend_access": "PASS",
        "backend_api_access": "PASS",
        "database_connectivity": "PASS",
        "crud_validation": "PASS",
        "persistence_validation": "PENDING"
      },
      "5": {
        "frontend_access": "PASS",
        "backend_api_access": "PASS",
        "database_connectivity": "PASS",
        "crud_validation": "PASS",
        "persistence_validation": "PENDING"
      }
    }
  }
}
```
