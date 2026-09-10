import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent


def _resolve_repository_path(path):
    """Resolve a path relative to this module and keep it inside the repository."""
    try:
        resolved_path = (BASE_DIR / Path(path)).resolve()
    except (OSError, TypeError, ValueError) as exc:
        return None, {
            "error": "Invalid path",
            "path": str(path),
            "detail": str(exc),
        }

    if resolved_path != REPO_ROOT and REPO_ROOT not in resolved_path.parents:
        return None, {
            "error": "Access outside repository is not allowed",
            "path": str(resolved_path),
        }

    return resolved_path, None


def list_project_files(directory_path=".."):
    """List the direct children of a repository directory in sorted order."""
    resolved_path, error = _resolve_repository_path(directory_path)
    if error:
        return error

    if not resolved_path.is_dir():
        return {
            "error": "Directory not found",
            "path": str(resolved_path),
        }

    try:
        return sorted(child.name for child in resolved_path.iterdir())
    except OSError as exc:
        return {
            "error": "Unable to list directory",
            "path": str(resolved_path),
            "detail": str(exc),
        }


def read_ci_report(report_path="../reports/report.json"):
    """Read and return a JSON CI evidence report stored in the repository."""
    resolved_path, error = _resolve_repository_path(report_path)
    if error:
        return error

    if not resolved_path.is_file():
        return {
            "error": "Report not found",
            "path": str(resolved_path),
            "hint": "CI evidence report is not available",
        }

    try:
        with resolved_path.open("r", encoding="utf-8") as report_file:
            return json.load(report_file)
    except json.JSONDecodeError as exc:
        return {
            "error": "Invalid JSON report",
            "path": str(resolved_path),
            "detail": str(exc),
        }
    except OSError as exc:
        return {
            "error": "Unable to read report",
            "path": str(resolved_path),
            "detail": str(exc),
        }
