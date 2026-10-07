# Student 1 Pre-Commit Security Testing Report

Run date: 7 October 2026 (Australia/Sydney). Branch: `feature/student-1-release-2`.
No commit or push was performed.

## Scope and tools

Ruff scans Python in `student-1/`, `multi-agent-server/`, `mcp-server/`,
`rag-server/`, `shared/` and `scripts/`, selecting the full stable S rule family.
Secret detection covers repository source (including untracked files in the manual
run). Virtual environments, caches, Chroma persistence, generated data and runtime
JSONL files are excluded. No application service or Docker architecture was added.

Tools are pinned separately in `requirements-security.txt`: pre-commit 4.6.2,
Ruff 0.16.10, detect-secrets 1.5.0 and pip-audit 2.10.1. Local pre-commit hooks use
isolated Python environments with matching pinned tools.

Dependency audit resolves the combined graph from all six required files:
Student 1 backend, database and tests; Multi-Agent, MCP and RAG requirements.
Transitive dependencies are included. Network access to package indexes/advisory
services is required. Resolution/network errors and vulnerabilities fail the hook.
The raw audit has no ignores. The commit gate applies only the four exact
documented GHSA acceptances below, only to ChromaDB 1.5.9 with no fix version.
All other findings and execution errors fail; there is no package-wide ignore.

## Trigger and reproduction

Install a persistent local tooling environment from the repository root:

```sh
python -m venv .venv-security
source .venv-security/bin/activate
python -m pip install -r requirements-security.txt
pre-commit install
python scripts/run_security_scans.py
pre-commit run --all-files
```

The manual command prints Ruff Security, Detect Secrets and Dependency Audit,
runs Ruff, secret detection and both dependency audit modes. Raw findings remain
visible; the overall exit status follows the gated result, while raw execution
errors also fail independently. Run `python scripts/security_pip_audit.py` alone
for raw evidence (exit 1 with findings), or add `--gate` for the commit policy. Ruff and pip-audit run on every
commit, even for changes outside Python files; detect-secrets checks staged files.
The manual secret scan also checks untracked, non-ignored source. Pre-commit
`--all-files` uses tracked files; it does not stage new files.

For a visible first Release 2 commit demonstration, review/stage the intended
Release 2 changes (including the new security files), then run:

```sh
git commit -m "feat: add Release 2 multi-agent workflow and local security checks"
```

The gate permits only the documented temporary no-fix acceptances. This is
conditional risk acceptance, not resolution; never bypass unaccepted findings. This task installed `.git/hooks/pre-commit` using an isolated
`/tmp/enrolment-security-venv` environment; repeat the persistent install above
before relying on the hook after temporary-directory cleanup.

Maintain reviewed baseline entries using the standard workflow:

```sh
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
```

Review new results before accepting a baseline; never baseline real credentials.

## Actual results

| Check | Current result |
| --- | --- |
| Ruff S-family scan | PASS: `All checks passed!` |
| detect-secrets | PASS: no new potential secrets beyond two reviewed placeholders |
| pip-audit, combined graph | FAIL: five advisory entries for ChromaDB 1.5.9; four distinct advisory IDs |
| Manual security command | PASS, exit 0; raw findings printed and temporarily accepted by gate |
| `pre-commit run --all-files` | PASS: Ruff, Detect Secrets and gated Dependency Audit |
| Application tests, existing environment | 155 passed |
| Application tests, isolated environment with patched pins | 155 passed |
| Python compilation / `git diff --check` | PASS |

Executed test command in both environments:

```sh
python -m pytest multi-agent-server/tests student-1/tests rag-server/tests/test_student1_semantic.py -q
```

The isolated compatibility environment installed the updated backend, database
and test requirements. It did not install/run live Ollama or the full embedding
stack; the application tests mock external calls as designed. Dependency audit
resolved the full RAG graph independently. Docker builds were not performed.

Historical unfiltered-gate output before temporary acceptance (preserved evidence):

```text
Ruff Security............................................................Passed
Detect Secrets...........................................................Passed
Dependency Audit.........................................................Failed
Found 5 known vulnerabilities in 1 package
chromadb 1.5.9 PYSEC-2026-311
chromadb 1.5.9 PYSEC-2026-311
chromadb 1.5.9 PYSEC-2026-3814
chromadb 1.5.9 PYSEC-2026-3815
chromadb 1.5.9 PYSEC-2026-3813
```

## Findings and handling

The initial audit reported 21 entries across five packages. Updated vulnerable
pins in the six scoped requirements files:

| Package | Previous | Updated | Initial advisory IDs |
| --- | --- | --- | --- |
| Flask | 3.0.3 | 3.1.3 | PYSEC-2026-2151 |
| Flask-Cors | 4.0.1 | 6.0.0 | PYSEC-2024-71, PYSEC-2026-1383/1384/1385 |
| requests | 2.32.3 | 2.33.0 | PYSEC-2026-1872/2275 |
| pytest | 8.3.5 | 9.0.3 | PYSEC-2026-1845 |

The rerun reports none of these package findings. Compatibility tests passed.
Flask debug mode was disabled in Student 1's legacy app, backend and database
entry points to fix genuine S201 findings (interactive debugger exposure).

Narrow documented exceptions:

- S101 is exempted only in the three scoped pytest test directories: assertions
  are test expectations, not production authorization/input checks. Other S rules
  still apply to tests.
- Five exact `0.0.0.0` binding lines use explained S104 suppressions: Docker
  services require container ingress and local MCP/RAG/Multi-Agent services must
  remain reachable from the Docker backend. These are intentional local-development
  bindings, not evidence that exposure is safe; host/network restrictions remain
  necessary. No global S104 ignore exists.
- Fixed subprocess argument arrays in security scripts have line-local S603/S607
  explanations. They use no shell or interpolated user commands.
- Two baseline entries are reviewed false positives: the literal dummy value `ollama` in the OpenAI client constructor
  in `student-1/app.py` and `student-1/agentic_loop.py` is a local Ollama OpenAI-client
  placeholder, not an issued credential. Both have `is_secret: false`; source was
  preserved. No real credentials were found by this scan. This is a detector result,
  not proof that every possible secret is absent.

## Temporary acceptance of remaining dependency findings

Reviewed 7 October 2026. Audited/current pinned ChromaDB version: **1.5.9**.
ChromaDB is not installed in the current agent Python environment; the full
requirements audit resolves 1.5.9. The user's running embedded RAG environment
was not modified or independently inspected for its installed package version.
For a live environment, verify with `python -m pip show chromadb` there.

| Explicit gate ID | pip-audit ID | CVE | Severity | Audited version | Fix version |
| --- | --- | --- | --- | --- | --- |
| [GHSA-f4j7-r4q5-qw2c](https://github.com/advisories/GHSA-f4j7-r4q5-qw2c) | PYSEC-2026-311 | CVE-2026-45829 | Critical, 9.3 | 1.5.9 | None |
| [GHSA-36p7-vc44-83pf](https://github.com/advisories/GHSA-36p7-vc44-83pf) | PYSEC-2026-3814 | CVE-2026-45833 | Critical, 9.4 | 1.5.9 | None |
| [GHSA-xph7-9rjv-w5fr](https://github.com/advisories/GHSA-xph7-9rjv-w5fr) | PYSEC-2026-3815 | CVE-2026-45831 | High, 8.8 | 1.5.9 | None |
| [GHSA-2wm9-hf6c-p5cr](https://github.com/advisories/GHSA-2wm9-hf6c-p5cr) | PYSEC-2026-3813 | CVE-2026-45830 | High, 8.8 | 1.5.9 | None |

Severity is from the linked published advisories, not pip-audit's JSON output.
For **each** listed advisory, the current pip-audit output has an empty
`fix_versions` list, and its published advisory lists no patched version. No
known upgrade target resolves it at this review date; inventing a version or
replacing the working RAG architecture is not a remediation. This justifies only
a temporary local-development acceptance with the exposure reductions below.

Per-advisory risk assessment and repository mitigation:

- **GHSA-f4j7-r4q5-qw2c:** pre-authentication arbitrary code execution via Chroma's
  HTTP collection creation/model-repository configuration with
  `trust_remote_code=true`. Student 1 uses `chromadb.PersistentClient` in
  `rag-server/retrievers/student1_course_retriever.py`, a fixed local collection
  and cosine HNSW configuration. It does not expose Chroma's HTTP server API or
  forward user-supplied model-repository/remote-code configuration. This reduces
  exposure to the published exploit path; **the package vulnerability remains**.
- **GHSA-36p7-vc44-83pf:** authenticated arbitrary code execution via Chroma's
  HTTP collection update/model-repository configuration with UPDATE_COLLECTION
  permission. The repository's Student 1 flow has no exposed Chroma update API
  and accepts course queries rather than model repository configuration. Accept
  temporarily because no fix exists and the documented server path is absent;
  code execution would remain severe if that configuration surface were exposed.
- **GHSA-xph7-9rjv-w5fr:** RBAC permissions do not enforce tenant/database/collection
  resource scope. Student 1's embedded local collection does not rely on Chroma's
  HTTP SimpleRBACAuthorizationProvider as a multi-tenant isolation boundary.
  Accept temporarily without claiming effective package RBAC; no patched upgrade
  exists and no Chroma tenant permission service is exposed by this flow.
- **GHSA-2wm9-hf6c-p5cr:** authenticated cross-tenant collection read/write/delete.
  The Student 1 course path uses a fixed embedded collection, not an exposed
  multi-tenant Chroma collection HTTP API. Accept temporarily because no patched
  upgrade exists and the described cross-tenant API boundary is absent. This is
  exposure reduction, not a claim that vulnerable authorization is repaired.

These mitigations describe the inspected Student 1 path, not a security guarantee
for every optional shared RAG feature or a future deployment. Local filesystem
access, malicious configuration and future Chroma HTTP exposure remain risks.
Review/remove acceptance before exposing Chroma's HTTP server, adding remote model
configuration, changing dependency version, or relying on tenant isolation.
Review the allowlist at each release/dependency update. If pip-audit publishes a
fix version for an accepted advisory, the gate automatically fails that finding.

## Gate implementation and current evidence

`scripts/security_pip_audit.py` runs pip-audit without `--ignore-vuln` in both modes
and prints **every** finding with its aliases and fix versions. Raw mode returns
non-zero for all findings. Gate mode applies `TEMPORARY_UNPATCHED_IGNORES` to exact
GHSA IDs (matched against primary IDs or advisory aliases), only on package
`chromadb`, version `1.5.9`, and `fix_versions == []`. Each accepted finding is
printed as **TEMPORARILY ACCEPTED (not resolved)** with its rationale. No wildcard,
all-Chroma ignore or global pip-audit disable exists. Unknown findings, different
versions/packages, available fixes, skipped dependencies and malformed/execution
failures still fail the gate.

The raw output contains five entries for four distinct IDs (PYSEC-2026-311 occurs
twice); neither mode deletes the duplicate from displayed evidence. The manual
script prints both raw and gated sections and returns the gate status only when
the raw scan completed normally. A raw execution error cannot be accepted.

Current actual verification (7 October 2026):

| Check | Result |
| --- | --- |
| Ruff / Detect Secrets | PASS / PASS |
| Unfiltered dependency audit | FAIL: five entries, four unique IDs, no fixes listed |
| Gated dependency audit | PASS: only the documented no-fix findings accepted |
| Manual script | PASS, exit 0; both audit results visibly printed |
| `pre-commit run --all-files` | PASS, exit 0: all three hooks passed |
| Requested application tests | 155 passed |
| Gate-policy regression tests (`python -m pytest scripts/tests -q`) | 6 passed |

Actual final output:

```text
Unfiltered dependency audit: FAIL (5 entries)
Pre-commit gated dependency audit: PASS; 0 unaccepted findings
Security gate (raw findings remain unresolved): PASS
Ruff Security............................................................Passed
Detect Secrets...........................................................Passed
Dependency Audit.........................................................Passed
```

Regression tests cover all four accepted IDs, raw failure versus gated acceptance,
new advisory blocking, wrong package/version, a newly available fix, incomplete
responses and clean-audit success. The additional tests use no live network.

**Final gate status: PASS with explicit temporary acceptance. Raw vulnerability
status: FAIL; four distinct ChromaDB advisories remain unresolved.**

**Findings remain visible and unresolved. Temporary gate acceptance is not a clean
vulnerability scan or remediation.**

Tool references: [Ruff security rules](https://docs.astral.sh/ruff/rules/),
[detect-secrets baseline workflow](https://github.com/Yelp/detect-secrets),
[pip-audit requirements and pre-commit usage](https://github.com/pypa/pip-audit).
