"""Unfiltered evidence audit, or a narrowly scoped temporary pre-commit gate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = (
    "student-1/requirements.txt",
    "student-1/backend/requirements.txt",
    "student-1/database/requirements.txt",
    "student-1/tests/requirements.txt",
    "student-2/backend/requirements.txt",
    "student-2/database/requirements.txt",
    "student-2/tests/requirements.txt",
    "student-3/backend/requirements.txt",
    "student-3/database/requirements.txt",
    "student-3/tests/requirements.txt",
    "student-4/backend/requirements.txt",
    "student-4/database/requirements.txt",
    "student-5/backend/requirements.txt",
    "student-5/database/requirements.txt",
    "student-5/tests/requirements.txt",
    "ai-services/multi-agent-server/requirements.txt",
    "mcp-server/requirements.txt",
    "rag-server/requirements.txt",
)
# Acceptance applies ONLY to chromadb 1.5.9 and only while fix_versions is empty.
# Review on every dependency/exposure change; details are in the security report.
TEMPORARY_UNPATCHED_IGNORES = {
    "GHSA-f4j7-r4q5-qw2c": "No listed patch; embedded PersistentClient, no Chroma HTTP/model-repository configuration API.",
    "GHSA-36p7-vc44-83pf": "No listed patch; no exposed Chroma UPDATE_COLLECTION/model-repository API.",
    "GHSA-xph7-9rjv-w5fr": "No listed patch; embedded local collection, no Chroma HTTP RBAC service or tenant permission boundary.",
    "GHSA-2wm9-hf6c-p5cr": "No listed patch; no exposed Chroma multi-tenant collection HTTP API.",
}


def temporary_acceptance(dependency, vulnerability):
    if dependency["name"] != "chromadb" or dependency["version"] != "1.5.9":
        return None
    if vulnerability.get("fix_versions") != []:
        return None
    identifiers = {vulnerability["id"], *vulnerability.get("aliases", [])}
    return next((key for key in TEMPORARY_UNPATCHED_IGNORES if key in identifiers), None)


def audit_result(report, returncode, gate):
    """Print every finding, then separately apply the documented acceptance policy."""
    dependencies = report.get("dependencies") if isinstance(report, dict) else None
    if returncode not in (0, 1) or not isinstance(dependencies, list):
        print("Audit execution/protocol error: FAIL", flush=True)
        return 2
    findings = []
    try:
        for dependency in dependencies:
            if dependency.get("skip_reason") or not isinstance(dependency.get("vulns"), list):
                raise ValueError("Incomplete dependency audit")
            for vulnerability in dependency["vulns"]:
                # Validate fields before acceptance; incomplete results fail closed.
                if not isinstance(vulnerability["id"], str) or not isinstance(vulnerability["fix_versions"], list):
                    raise ValueError("Invalid vulnerability result")
                findings.append((dependency, vulnerability))
                identifiers = ", ".join([vulnerability["id"], *vulnerability.get("aliases", [])])
                print(f'{dependency["name"]} {dependency["version"]}: {identifiers}; '
                      f'fix versions: {vulnerability["fix_versions"] or "none"}', flush=True)
        if (returncode == 1) != bool(findings):
            raise ValueError("Audit exit status contradicts findings")
        print(f"Unfiltered dependency audit: {'FAIL' if findings else 'PASS'} ({len(findings)} entries)", flush=True)
        if not gate:
            return int(bool(findings))
        rejected = []
        for dependency, vulnerability in findings:
            accepted = temporary_acceptance(dependency, vulnerability)
            if accepted:
                print(f"TEMPORARILY ACCEPTED (not resolved): {accepted}: "
                      f"{TEMPORARY_UNPATCHED_IGNORES[accepted]}", flush=True)
            else:
                rejected.append(vulnerability["id"])
        print(f"Pre-commit gated dependency audit: {'FAIL' if rejected else 'PASS'}; "
              f"{len(rejected)} unaccepted findings", flush=True)
        return int(bool(rejected))
    except (KeyError, TypeError, ValueError):
        print("Incomplete or invalid audit response: FAIL", flush=True)
        return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true",
                        help="Apply documented temporary no-fix acceptances")
    args = parser.parse_args()

    overall_status = 0

    for requirement in REQUIREMENTS:
        print(f"\\n===== Auditing {requirement} =====", flush=True)

        command = [
            sys.executable, "-m", "pip_audit",
            "--progress-spinner", "off",
            "--format", "json",
            "-r", requirement,
        ]

        # Fixed pip-audit command; requirements paths come from a trusted constant.
        result = subprocess.run(  # noqa: S603
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        if result.stderr:
            print(result.stderr, file=sys.stderr, end="", flush=True)

        try:
            report = json.loads(result.stdout)
        except ValueError:
            print(f"Audit returned no valid JSON for {requirement}: FAIL",
                  flush=True)
            overall_status = 2
            continue

        status = audit_result(report, result.returncode, args.gate)
        overall_status = max(overall_status, status)

    print(
        f"\\nOverall dependency audit: "
        f"{'PASS' if overall_status == 0 else 'FAIL'}",
        flush=True,
    )
    return overall_status


if __name__ == "__main__":
    sys.exit(main())
