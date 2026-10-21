#!/usr/bin/env bash
# Runs on the VM via sudo over verified SSH during an explicit deployment.
set -Eeuo pipefail
trap 'echo "VM configuration failed at line $LINENO" >&2' ERR
: "${1:?Application archive path is required}"
: "${2:?Expected archive SHA256 is required}"
: "${3:?Release identifier is required}"
archive=$1
expected_sha=$2
release_id=$3
[[ "$expected_sha" =~ ^[a-f0-9]{64}$ && "$release_id" =~ ^[a-zA-Z0-9-]+$ ]] || { echo 'Invalid release metadata' >&2; exit 1; }
actual_sha=$(sha256sum "$archive" | cut -d ' ' -f 1)
[[ "$actual_sha" == "$expected_sha" ]] || { echo 'Application archive checksum mismatch' >&2; exit 1; }
DEPLOY_DIR=${DEPLOY_DIR:-/opt/asd-group5}
release_dir="$DEPLOY_DIR/releases/$release_id"
[[ ! -e "$release_dir" ]] || { echo 'Release directory already exists' >&2; exit 1; }
install -d -m 700 "$release_dir"
# Reject traversal, symlinks and special files before extracting private source.
python3 - "$archive" "$release_dir" <<'PY'
from pathlib import Path
import sys
import tarfile
with tarfile.open(sys.argv[1]) as archive:
    for member in archive.getmembers():
        path = Path(member.name)
        if path.is_absolute() or '..' in path.parts or not member.isfile():
            raise ValueError('Unsafe application archive member')
    archive.extractall(sys.argv[2], filter='data')
PY
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 curl
systemctl enable --now docker
cd "$release_dir"
cat deployment-source.json
echo
# Stable project name preserves the five database volumes across release directories.
compose_files=(-f docker-compose.cloud.yml)
if [[ -f docker-compose.bonus.yml ]]; then
  compose_files+=(-f docker-compose.bonus.yml)
fi
docker compose -p asd-group5-cloud "${compose_files[@]}" config -q
docker compose -p asd-group5-cloud "${compose_files[@]}" up -d --build --wait --wait-timeout 300
docker compose -p asd-group5-cloud "${compose_files[@]}" ps -a
bash scripts/cloud/health-check.sh
# Switch the operator's current-release link only after successful checks.
ln -s "$release_dir" "$DEPLOY_DIR/current-$release_id"
mv -Tf "$DEPLOY_DIR/current-$release_id" "$DEPLOY_DIR/current"
echo GROUP5_DEPLOYMENT_HEALTH_PASSED
