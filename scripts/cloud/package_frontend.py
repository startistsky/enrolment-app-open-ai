"""Package committed Student 3 frontend files for Azure deployment."""

import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import os
import shutil
import tempfile
OUTPUT = Path(
    os.environ["FRONTEND_PACKAGE_OUTPUT"]
    if "FRONTEND_PACKAGE_OUTPUT" in os.environ
    else Path(tempfile.mkdtemp(prefix="student3-frontend-")) / "release.tar.gz"
)

GIT = shutil.which("git")
if GIT is None:
    raise SystemExit("Git executable not found")

status = subprocess.check_output(  # noqa: S603 - fixed Git arguments, no shell
    [GIT, "status", "--porcelain"],
    cwd=ROOT,
    text=True,
)

if status.strip():
    raise SystemExit("Working tree must be clean before packaging")

commit = subprocess.check_output(  # noqa: S603 - fixed Git arguments, no shell
    [GIT, "rev-parse", "HEAD"],
    cwd=ROOT,
    text=True,
).strip()

files = subprocess.check_output(  # noqa: S603 - fixed Git arguments, no shell
    [GIT, "ls-files", "student-3/frontend"],
    cwd=ROOT,
    text=True,
).splitlines()

with tarfile.open(OUTPUT, "w:gz") as archive:
    for name in files:
        path = ROOT / name
        if (
            not name.startswith("student-3/frontend/")
            or ".." in Path(name).parts
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(ROOT)
        ):
            raise SystemExit(f"Unsafe file: {name}")
        archive.add(path, arcname=name, recursive=False)

    manifest = json.dumps({
        "commit": commit,
        "deployment": "student3-frontend",
    }).encode()

    info = tarfile.TarInfo("deployment-source.json")
    info.size = len(manifest)
    archive.addfile(info, io.BytesIO(manifest))

print(f"FRONTEND_PACKAGE_PASSED: {len(files)} files")
