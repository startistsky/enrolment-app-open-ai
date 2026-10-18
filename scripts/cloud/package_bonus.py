"""Package the Azure Bonus release without local credentials or runtime data."""

import argparse
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from package_source import eligible as baseline_eligible

BONUS_ROOTS = (
    "mcp-server/",
    "rag-server/",
    "ai-services/multi-agent-server/",
)

BONUS_FILES = {
    "docker-compose.bonus.yml",
}

SKIP_PARTS = {
    ".git", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", "chroma", "chroma-data",
    "docker-data", "ollama-data", ".venv", ".env",
}

SKIP_SUFFIXES = (
    ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3",
    ".jsonl", ".pyc", ".pem", ".key", ".p12", ".pfx",
)


def eligible(name):
    path = Path(name)

    if baseline_eligible(name):
        return True

    if path.is_absolute() or ".." in path.parts:
        return False

    if name not in BONUS_FILES and not name.startswith(BONUS_ROOTS):
        return False

    if any(
        part in SKIP_PARTS or part.startswith((".venv", ".env"))
        for part in path.parts
    ):
        return False

    if name.endswith(SKIP_SUFFIXES):
        return False

    if path.name in {"id_rsa", "id_ed25519", "credentials", "config.json"}:
        return False

    return True


def package(source, output):
    source = source.resolve()

    result = subprocess.run(  # noqa: S603 -- fixed Git command, no shell.
        [shutil.which("git"), "ls-files", "--cached", "-z"],
        cwd=source,
        check=True,
        capture_output=True,
    )

    status = subprocess.check_output(  # noqa: S603 -- fixed Git status command.
        [shutil.which("git"), "status", "--porcelain"],
        cwd=source,
        text=True,
    )

    if status.strip():
        raise ValueError(
            "Refusing to package a dirty Git working tree. "
            "Commit and review changes before deployment."
        )

    names = sorted({
        name
        for name in result.stdout.decode().split("\0")
        if name and eligible(name)
    })

    required = {"docker-compose.cloud.yml", "docker-compose.bonus.yml"}

    if not required.issubset(names):
        raise ValueError("Required cloud Compose files are missing")

    commit = subprocess.check_output(  # noqa: S603 -- fixed Git revision command.
        [shutil.which("git"), "rev-parse", "HEAD"],
        cwd=source,
        text=True,
    ).strip()

    with tarfile.open(output, "w:gz") as archive:
        for name in names:
            path = source / name

            if (
                path.is_symlink()
                or not path.is_file()
                or not path.resolve().is_relative_to(source)
            ):
                raise ValueError(f"Unsafe file: {name}")

            archive.add(path, arcname=name, recursive=False)

        manifest = json.dumps({
            "commit": commit,
            "deployment": "azure-bonus",
        }).encode()

        entry = tarfile.TarInfo("deployment-source.json")
        entry.size = len(manifest)
        entry.mode = 0o600
        archive.addfile(entry, io.BytesIO(manifest))

    print(f"Packaged {len(names)} Bonus release files")
    print(f"Source commit: {commit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package(args.source_dir, args.output)
