#!/usr/bin/env bash
set -Eeuo pipefail

ARCHIVE="${1:?Missing frontend archive}"
EXPECTED_SHA="${2:?Missing SHA256}"
RELEASE_ID="${3:?Missing release ID}"

PROJECT="asd-group5-cloud"
ROOT="/opt/asd-group5"
BASELINE="$ROOT/current"
DEPLOY_DIR="$ROOT/frontend-releases/$RELEASE_ID"
SERVICE="student3-frontend"

log() {
  printf '[FRONTEND] %s\n' "$*"
}

fail() {
  printf '[FRONTEND ERROR] %s\n' "$*" >&2
  exit 1
}

[[ "$(id -u)" == "0" ]] || fail "Run with sudo"
[[ "$RELEASE_ID" =~ ^[a-zA-Z0-9._-]+$ ]] || fail "Invalid release ID"
[[ "$EXPECTED_SHA" =~ ^[a-fA-F0-9]{64}$ ]] || fail "Invalid SHA256"
[[ -f "$ARCHIVE" ]] || fail "Archive missing"
[[ -L "$BASELINE" ]] || fail "Baseline pointer must be a symlink"
[[ ! -e "$DEPLOY_DIR" ]] || fail "Release ID already exists"

BASELINE_REAL="$(readlink -f "$BASELINE")"
[[ -f "$BASELINE_REAL/docker-compose.cloud.yml" ]] ||
  fail "Baseline Compose configuration missing"

ACTUAL_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || fail "SHA256 mismatch"

log "Validating frontend archive"

python3 - "$ARCHIVE" <<'PY'
import sys
import tarfile
from pathlib import PurePosixPath

archive_path = sys.argv[1]
required = {
    "student-3/frontend/Dockerfile",
    "student-3/frontend/index.html",
    "student-3/frontend/nginx.conf",
}
found = set()

with tarfile.open(archive_path, "r:gz") as archive:
    for member in archive.getmembers():
        path = PurePosixPath(member.name)

        if (
            path.is_absolute()
            or ".." in path.parts
            or not member.isfile()
            or (
                not member.name.startswith("student-3/frontend/")
                and member.name != "deployment-source.json"
            )
            or member.name in found
        ):
            raise SystemExit(f"Unsafe archive entry: {member.name}")

        found.add(member.name)

if not required.issubset(found):
    raise SystemExit("Required frontend files missing")

print("FRONTEND_ARCHIVE_VALIDATION_PASSED")
PY

mkdir -p "$DEPLOY_DIR"
tar -xzf "$ARCHIVE" -C "$DEPLOY_DIR"

grep -q 'data-ai-mode="multi-agent"' \
  "$DEPLOY_DIR/student-3/frontend/index.html" ||
  fail "Multi-Agent button missing"

IMAGE="asd-student3-frontend:$RELEASE_ID"

log "Building frontend image"

docker build \
  -f "$DEPLOY_DIR/student-3/frontend/Dockerfile" \
  -t "$IMAGE" \
  "$DEPLOY_DIR"

cd "$BASELINE_REAL"

BASE_COMPOSE=(
  docker compose
  -p "$PROJECT"
  -f docker-compose.cloud.yml
)

CONTAINER_ID="$("${BASE_COMPOSE[@]}" ps -q "$SERVICE")"
[[ -n "$CONTAINER_ID" ]] || fail "Existing frontend container missing"

OLD_IMAGE="$(docker inspect --format '{{.Image}}' "$CONTAINER_ID")"
[[ -n "$OLD_IMAGE" ]] || fail "Existing frontend image missing"

docker image inspect "$OLD_IMAGE" >/dev/null ||
  fail "Existing frontend image unavailable"

log "Original frontend image: $OLD_IMAGE"

write_override() {
  local image="$1"
  printf 'services:\n  student3-frontend:\n    image: "%s"\n    build: !reset null\n' \
    "$image" > "$DEPLOY_DIR/frontend-override.yml"
}

write_override "$IMAGE"

COMPOSE=(
  docker compose
  -p "$PROJECT"
  -f docker-compose.cloud.yml
  -f "$DEPLOY_DIR/frontend-override.yml"
)

"${COMPOSE[@]}" config --quiet

SWITCHED=0
SUCCESS=0

rollback() {
  log "Restoring previous frontend image"

  write_override "$OLD_IMAGE"

  "${COMPOSE[@]}" up -d \
    --no-deps \
    --force-recreate \
    --no-build \
    "$SERVICE" || return 1

  for attempt in {1..20}; do
    local restored_id
    restored_id="$("${COMPOSE[@]}" ps -q "$SERVICE")"

    if [[ -n "$restored_id" ]] &&
       [[ "$(docker inspect --format '{{.Image}}' "$restored_id")" == "$OLD_IMAGE" ]] &&
       curl -fsS --max-time 5 \
         http://127.0.0.1:8083/index.html >/dev/null 2>&1; then
      log "Previous frontend restored"
      return 0
    fi

    sleep 3
  done

  return 1
}

on_exit() {
  local result=$?
  trap - EXIT

  if [[ "$SUCCESS" == "1" ]]; then
    exit 0
  fi

  if [[ "$SWITCHED" == "1" ]]; then
    rollback || log "CRITICAL: Manual frontend recovery required"
  fi

  exit "$result"
}

trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

log "Updating Student 3 frontend only"

SWITCHED=1

"${COMPOSE[@]}" up -d \
  --no-deps \
  --force-recreate \
  --no-build \
  "$SERVICE"

log "Verifying frontend and backend"

PASSED=0

for attempt in {1..20}; do
  if curl -fsS --max-time 5 \
    http://127.0.0.1:8083/index.html |
    grep -q 'data-ai-mode="multi-agent"'; then
    PASSED=1
    break
  fi
  sleep 3
done

[[ "$PASSED" == "1" ]] || fail "Multi-Agent frontend verification failed"

curl -fsS --max-time 10 \
  http://127.0.0.1:8003/health >/dev/null ||
  fail "Backend health check failed"

SUCCESS=1
log "GROUP5_STUDENT3_FRONTEND_DEPLOYMENT_PASSED"
