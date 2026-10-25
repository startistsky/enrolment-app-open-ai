# Student 3 Pre-Commit Security Scan

**Scope:** local, uncommitted workspace at HEAD
`350197ed9d6b` (abbreviated), 25 October 2026. The configured Ruff hook checked
the repository's Student 1–5 and shared/server source scopes. The configured
dependency acceptance gate checked its full requirements list. The raw
Student 3 audit evidence resolves `student-3/tests/requirements.txt`, which
includes the Student 3 backend requirements. The final Detect Secrets hook
checked all seven changed files, including the new untracked reports. These
are local checks, not results from the historical GitHub Actions run.

## Verified scan results

- Ruff with the repository `ruff.toml`: **PASS**.
- Detect Secrets against `.secrets.baseline` for all seven changed files:
  **PASS**. Public commit identifiers are abbreviated in the report evidence;
  no scanner exceptions or baseline changes were made.
- Raw Student 3 dependency audit: **FAIL**, with five audit entries for four
  distinct advisories affecting `chromadb 1.5.9`. One advisory appeared twice
  because the test requirements include the backend requirements.
- Existing repository dependency acceptance gate: **PASS**. All four unique
  findings match the existing temporary no-fix acceptance policy. They remain
  unresolved; this is not a clean raw audit.

Raw pip-audit JSON and stderr were saved outside the repository:

- `/tmp/student3-review-evidence/security/student3-pip-audit-raw.json`
- `/tmp/student3-review-evidence/security/student3-pip-audit-stderr.txt`

## Unresolved dependency findings

The current audit returned an empty `fix_versions` list for each advisory.
Acceptance below follows `scripts/security_pip_audit.py`; it does not mean the
vulnerabilities are resolved. The exposure notes are the repository's existing
temporary acceptance rationale for the embedded Chroma use.

| Advisory | pip-audit IDs | Occurrences | Status |
|---|---|---:|---|
| GHSA-f4j7-r4q5-qw2c | PYSEC-2026-311, CVE-2026-45829 | 2 | Accepted temporarily; unresolved; no fix listed |
| GHSA-36p7-vc44-83pf | PYSEC-2026-3814, CVE-2026-45833 | 1 | Accepted temporarily; unresolved; no fix listed |
| GHSA-xph7-9rjv-w5fr | PYSEC-2026-3815, CVE-2026-45831 | 1 | Accepted temporarily; unresolved; no fix listed |
| GHSA-2wm9-hf6c-p5cr | PYSEC-2026-3813, CVE-2026-45830 | 1 | Accepted temporarily; unresolved; no fix listed |

The Student 3 source uses embedded local Chroma persistence; this scan does not
verify a deployed Chroma version or prove that every exposure path is absent.
Reassess these acceptances when the dependency, configuration, or exposure
changes, and when a fixed release becomes available.

```json
{
  "review_evidence": {
    "ruff": "PASS",
    "sensitive_data_scan": "PASS",
    "pip_audit_raw": "FAIL",
    "pip_audit_gate": "PASS",
    "unresolved_findings": [
      {
        "advisory_id": "GHSA-f4j7-r4q5-qw2c",
        "accepted": true,
        "resolved": false,
        "rationale": "No patched version listed for audited chromadb 1.5.9",
        "mitigation": "No listed patch; embedded PersistentClient, no Chroma HTTP/model-repository configuration API.",
        "occurrences": 2,
        "pip_audit_ids": ["PYSEC-2026-311", "CVE-2026-45829"]
      },
      {
        "advisory_id": "GHSA-36p7-vc44-83pf",
        "accepted": true,
        "resolved": false,
        "rationale": "No patched version listed for audited chromadb 1.5.9",
        "mitigation": "No listed patch; no exposed Chroma UPDATE_COLLECTION/model-repository API.",
        "occurrences": 1,
        "pip_audit_ids": ["PYSEC-2026-3814", "CVE-2026-45833"]
      },
      {
        "advisory_id": "GHSA-xph7-9rjv-w5fr",
        "accepted": true,
        "resolved": false,
        "rationale": "No patched version listed for audited chromadb 1.5.9",
        "mitigation": "No listed patch; embedded local collection, no Chroma HTTP RBAC service or tenant permission boundary.",
        "occurrences": 1,
        "pip_audit_ids": ["PYSEC-2026-3815", "CVE-2026-45831"]
      },
      {
        "advisory_id": "GHSA-2wm9-hf6c-p5cr",
        "accepted": true,
        "resolved": false,
        "rationale": "No patched version listed for audited chromadb 1.5.9",
        "mitigation": "No listed patch; no exposed Chroma multi-tenant collection HTTP API.",
        "occurrences": 1,
        "pip_audit_ids": ["PYSEC-2026-3813", "CVE-2026-45830"]
      }
    ],
    "ruff_scan_scope": [
      "student-1",
      "student-2",
      "student-3",
      "ai-services/multi-agent-server",
      "mcp-server",
      "rag-server",
      "shared",
      "scripts"
    ],
    "sensitive_data_scan_scope": [
      "shared/RELEASE2_REVIEWS.md",
      "shared/agentic_loop.py",
      "shared/release2_reviews.py",
      "shared/tests/test_release2_reviews.py",
      "reports/student-3-azure-bonus-deployment-report.md",
      "reports/student-3-post-commit-ci-report.md",
      "reports/student-3-pre-commit-security-report.md"
    ],
    "audit_entry_count": 5,
    "distinct_advisory_count": 4,
    "working_tree_commit": "350197ed9d6b (abbreviated)"
  }
}
```
