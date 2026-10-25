"""Run repository security checks and save a Markdown report."""
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "agentic-review-logs" / "pre-commit-security-report.md"
EXCLUDED = re.compile(
    r"(^|/)(\.venv[^/]*|venv|env|__pycache__|chroma[^/]*|docker-data|ollama-data)/"
    r"|\.jsonl$|^reports/student-5-pre-commit-security-report\.md$"
    r"|^reports/testing-review-(security|ci)-report\.json$"
    r"|^reports/student-[1-5]-post-commit-ci-report\.md$"
)


def run(command):
    # Commands are fixed argument arrays; filenames are separate arguments, no shell.
    result = subprocess.run(  # noqa: S603 -- fixed tool invocations, no shell or user input.
        command, cwd=ROOT, check=False, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    if output:
        print(output, end="" if output.endswith("\n") else "\n", flush=True)
    return result.returncode, output


def render_report(results, generated_at):
    lines = [
        "# Pre-commit Security Scan Report",
        "",
        f"Generated: {generated_at}",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for name, (status, _) in results.items():
        lines.append(f"| {name} | {status} |")
    overall = "PASS" if all(
        results[name][0] == "PASS"
        for name in ("Ruff Security", "Detect Secrets", "Dependency Audit Gate")
    ) and results["Raw Dependency Audit"][0] != "ERROR" else "FAIL"
    lines.extend(["", f"Overall security gate: **{overall}**"])
    for name, (_, output) in results.items():
        lines.extend(["", f"<details><summary>{name} output</summary>", ""])
        lines.extend(["```text", output.rstrip().replace("```", "'''") or "(no output)", "```", "</details>"])
    return "\n".join(lines) + "\n", overall


def main():
    print("\nRuff Security", flush=True)
    ruff_status, ruff_output = run([
        sys.executable, "-m", "ruff", "check", "--config", "ruff.toml",
        "student-1", "student-2", "student-3", "student-4", "student-5",
        "ai-services/multi-agent-server", "mcp-server", "rag-server", "shared", "scripts",
    ])
    results = {"Ruff Security": ("PASS" if ruff_status == 0 else "FAIL", ruff_output)}
    print("\nDetect Secrets", flush=True)
    # Include new, untracked source so the manual report covers Release 2 before staging.
    files = subprocess.check_output(  # noqa: S603,S607 -- fixed Git command, no shell/input.
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT  # noqa: S607 -- fixed Git executable from developer PATH.
    ).decode().split("\0")
    files = sorted({name for name in files if name and name != ".secrets.baseline"
                    and not EXCLUDED.search(name) and (ROOT / name).is_file()})
    hook = Path(sys.executable).parent / "detect-secrets-hook"
    secret_status, secret_output = run([str(hook), "--baseline", ".secrets.baseline", "--", *files])
    results["Detect Secrets"] = ("PASS" if secret_status == 0 else "FAIL", secret_output)
    print("\nUnfiltered dependency audit findings", flush=True)
    raw_status, raw_output = run([sys.executable, str(ROOT / "scripts/security_pip_audit.py")])
    # Raw findings (exit 1) remain visible; errors (exit 2+) fail independently.
    raw_result = "PASS" if raw_status == 0 else "FINDINGS" if raw_status == 1 else "ERROR"
    results["Raw Dependency Audit"] = (raw_result, raw_output)
    print("\nPre-commit gated dependency audit result", flush=True)
    gate_status, gate_output = run([
        sys.executable, str(ROOT / "scripts/security_pip_audit.py"), "--gate",
    ])
    results["Dependency Audit Gate"] = ("PASS" if gate_status == 0 else "FAIL", gate_output)
    report, overall = render_report(results, datetime.now(timezone.utc).isoformat())
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nSecurity report written to {REPORT_PATH.relative_to(ROOT)}", flush=True)
    print("\nSecurity gate (raw findings remain unresolved): " + overall, flush=True)
    return int(overall == "FAIL")


if __name__ == "__main__":
    sys.exit(main())
