"""Show raw evidence and the separate commit gate; fail on unaccepted findings/errors."""
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = re.compile(r"(^|/)(\.venv[^/]*|venv|env|__pycache__|chroma[^/]*|docker-data|ollama-data)/|\.jsonl$")


def run(command):
    # Commands are fixed argument arrays; filenames are separate arguments, no shell.
    return subprocess.run(command, cwd=ROOT, check=False).returncode  # noqa: S603


def main():
    print("\nRuff Security", flush=True)
    results = [run([sys.executable, "-m", "ruff", "check", "--config", "ruff.toml",
                    "student-1", "multi-agent-server", "mcp-server", "rag-server", "shared", "scripts"])]
    print("\nDetect Secrets", flush=True)
    # Include new, untracked source so the manual report covers Release 2 before staging.
    files = subprocess.check_output(  # noqa: S603,S607 -- fixed Git command, no shell/input.
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT  # noqa: S607 -- fixed Git executable from developer PATH.
    ).decode().split("\0")
    files = sorted({name for name in files if name and name != ".secrets.baseline"
                    and not EXCLUDED.search(name) and (ROOT / name).is_file()})
    hook = Path(sys.executable).parent / "detect-secrets-hook"
    results.append(run([str(hook), "--baseline", ".secrets.baseline", "--", *files]))
    print("\nUnfiltered dependency audit findings", flush=True)
    raw_status = run([sys.executable, str(ROOT / "scripts/security_pip_audit.py")])
    # Raw findings (exit 1) remain visible; errors (exit 2+) fail independently.
    results.append(int(raw_status not in (0, 1)))
    print("\nPre-commit gated dependency audit result", flush=True)
    results.append(run([sys.executable, str(ROOT / "scripts/security_pip_audit.py"), "--gate"]))
    print("\nSecurity gate (raw findings remain unresolved): " + ("PASS" if not any(results) else "FAIL"), flush=True)
    return int(any(results))


if __name__ == "__main__":
    sys.exit(main())
