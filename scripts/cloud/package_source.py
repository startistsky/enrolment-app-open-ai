"""Package checked-out application source without Git metadata or local runtime data."""
import argparse
import io
import json
import shutil
from pathlib import Path
import subprocess
import tarfile

SOURCE_ROOTS = tuple(f'student-{number}/' for number in range(1, 6)) + ('shared/frontend/',)
EXACT_FILES = {'docker-compose.cloud.yml', 'scripts/cloud/health-check.sh'}
SKIP_PARTS = {'.git', '.aws', '.codex', '.agents', '__pycache__', '.pytest_cache', '.ruff_cache',
              'node_modules', 'chroma', 'docker-data', 'ollama-data'}
SKIP_SUFFIXES = ('.db', '.db-wal', '.db-shm', '.sqlite', '.sqlite3', '.jsonl', '.pyc', '.pem', '.key', '.p12', '.pfx')


def eligible(name):
    path = Path(name)
    return (
        not path.is_absolute() and '..' not in path.parts
        and (name in EXACT_FILES or name.startswith(SOURCE_ROOTS))
        and not any(part in SKIP_PARTS or part.startswith(('.venv', '.env')) and part != '.env.example'
                    for part in path.parts)
        and not name.endswith(SKIP_SUFFIXES)
        and path.name not in ('id_rsa', 'id_ed25519', 'credentials', 'config.json')
    )


def package(source, output):
    source = source.resolve()
    result = subprocess.run(  # noqa: S603,S607 -- fixed Git command, no shell or credentials.
        [shutil.which('git'), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=source, check=True, capture_output=True,
    )
    names = sorted({name for name in result.stdout.decode().split('\0') if name and eligible(name)})
    for required in EXACT_FILES:
        if required not in names:
            raise ValueError(f'Required application file is absent or gitignored: {required}')
    commit = subprocess.check_output(  # noqa: S603,S607 -- fixed read-only Git command.
        [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=source, text=True,
    ).strip()
    dirty = bool(subprocess.check_output(  # noqa: S603,S607 -- fixed read-only Git command.
        [shutil.which('git'), 'status', '--porcelain'], cwd=source,
    ))
    with tarfile.open(output, 'w:gz') as archive:
        for name in names:
            path = source / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(source):
                raise ValueError(f'Refusing non-regular application file: {name}')
            archive.add(path, arcname=name, recursive=False)
        manifest = json.dumps({'commit': commit, 'working_tree_modified': dirty}).encode()
        entry = tarfile.TarInfo('deployment-source.json')
        entry.size = len(manifest)
        entry.mode = 0o600
        archive.addfile(entry, io.BytesIO(manifest))
    print(f'Packaged {len(names)} application files; commit {commit}; working tree modified: {dirty}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package(args.source_dir, args.output)
