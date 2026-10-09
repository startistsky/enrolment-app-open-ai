# Group 5 Cloud Deployment Evidence Report

**Overall status: PENDING — this report does not establish final release approval or Cloud Deployment Review PASS.**

Evidence source: verified deployment and test results supplied by the user.
This report records that evidence without independently re-running deployment,
CRUD operations, persistence tests or the agentic Cloud Deployment Review.
Deployment/test timestamps, screenshots and raw logs were not supplied; none
are invented here.

## 1. Verified group infrastructure evidence

| Item | Verified value |
| --- | --- |
| Platform | Microsoft Azure |
| Resource group | `asd-group5-rg` |
| Deployment region | `eastasia` |
| VM | `asd-group5-vm` |
| VM size | `Standard_B2s_v2` |
| VM capacity | 2 vCPUs, 8 GiB RAM |
| Deployment branch/ref | `feature/student-1-release-2` |
| Deployed commit | `6c56b673e7d8ec07c6085c22a26570b313cbaceb` |
| Workflow | Azure Cloud Baseline Deployment |
| Workflow file | `.github/workflows/cloud-deployment.yml` |
| Deployment run | [GitHub Actions run 37945957570](https://github.com/startistsky/enrolment-app-open-ai/actions/runs/37945957570) |
| Workflow result | Success |

Verified workflow evidence:

- Azure OIDC authentication succeeded.
- Cloud configuration validation succeeded.
- VM deployment and configuration succeeded.
- Docker Compose deployment succeeded.
- Health checks passed.
- `GROUP5_DEPLOYMENT_HEALTH_PASSED` was recorded.
- All deployed frontend/backend/database containers were reported healthy.

These results establish group infrastructure deployment and health evidence.
They do not establish full Group 5 CRUD or persistence completion.

Public frontend URLs supplied with the deployment evidence:

| Frontend | URL |
| --- | --- |
| Shared home | [Shared home](http://20.205.47.155:8888) |
| Student 1 Courses | [Courses](http://20.205.47.155:8081) |
| Student 2 Assignments | [Assignments](http://20.205.47.155:8082) |
| Student 3 Resources | [Resources](http://20.205.47.155:8083) |
| Student 4 Events | [Events](http://20.205.47.155:8080) |
| Student 5 Career | [Career](http://20.205.47.155:8085) |

Listing these URLs does not claim Student 2–5 functional testing is complete.

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

## 3. Pending Student 2–5 CRUD/persistence evidence

No verified CRUD or persistence results were supplied for Student 2, Student 3,
Student 4 or Student 5. Each module still needs create/read/update/delete evidence
and a persistence check across container recreation, using temporary test records.
Container health and deployment success do not substitute for those checks.

## 4. Pending group human release review

The group human release review is PENDING. No final Accept, Partially Accept or
Reject decision, completed review timestamp or release approval was supplied.
This report does not infer approval from workflow success or Student 1 test results.

## 5. Pending final Cloud Deployment Review

The final Group 5 Cloud Deployment Review is PENDING. The agentic cloud review
has not been run as part of preparing this report and must not be represented as PASS.
Full Group 5 CRUD/persistence evidence and the group human release review remain
outstanding. The supplied disabled-response evidence covers the three Student 1
endpoints above; further AI Mode/group-wide endpoint evidence is not supplied.

## Evidence Status

PASS means the specific evidence was verified and supplied. PENDING means the
required evidence or review has not yet been supplied or completed.

| Evidence item | Status | Basis / remaining work |
| --- | --- | --- |
| GitHub Actions deployment run | PASS | Run 37945957570: Success; deployed commit recorded above |
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
| Student 2 CRUD | PENDING | No verified results supplied |
| Student 2 persistence | PENDING | No verified results supplied |
| Student 3 CRUD | PENDING | No verified results supplied |
| Student 3 persistence | PENDING | No verified results supplied |
| Student 4 CRUD | PENDING | No verified results supplied |
| Student 4 persistence | PENDING | No verified results supplied |
| Student 5 CRUD | PENDING | No verified results supplied |
| Student 5 persistence | PENDING | No verified results supplied |
| Further AI Mode / group-wide disabled endpoint evidence | PENDING | Not established by the three supplied Student 1 endpoint tests |
| Full Group 5 CRUD/persistence completion | PENDING | Student 2–5 evidence outstanding |
| Group human release review and final approval | PENDING | No final decision or completed review supplied |
| Final Group 5 Cloud Deployment Review | PENDING | Await complete evidence and review; not run for this report |
