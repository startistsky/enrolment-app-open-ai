#!/usr/bin/env bash
set -Eeuo pipefail

# Student 3 Azure Bonus B1-B4 deployment.
# This script runs ON the Azure VM, not on the Mac.
#
# Required:
#   sudo bash configure-bonus-vm.sh ARCHIVE SHA256 RELEASE_ID
#
# Safety:
# - Never delete Docker volumes.
# - Never run docker compose down.
# - Never modify other students' services.
# - Keep the existing baseline release pointer unchanged.

ARCHIVE="${1:?Missing release archive}"
EXPECTED_SHA="${2:?Missing SHA256}"
RELEASE_ID="${3:?Missing release ID}"

PROJECT="asd-group5-cloud"
ROOT="/opt/asd-group5"
BASELINE="$ROOT/current"
RELEASE="$ROOT/releases/$RELEASE_ID"

BONUS_SERVICES=(
  ollama
  mcp-server
  rag-init
  rag-server
  ollama-init
  multi-agent-server
)

BACKEND="student3-backend"
BACKEND_SWITCHED=0
DEPLOYMENT_SUCCESS=0
ORIGINAL_BACKEND_IMAGE=""
ORIGINAL_BACKEND_CONTAINER=""

log() {
  printf '[BONUS] %s\n' "$*"
}

fail() {
  printf '[BONUS ERROR] %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "Required file missing: $1"
}

wait_for_container() {
  local service="$1"
  local attempts="${2:-40}"
  local container_id
  local status

  container_id="$(
    docker compose \
      -p "$PROJECT" \
      -f docker-compose.cloud.yml \
      -f docker-compose.bonus.yml \
      ps -q "$service"
  )"

  [[ -n "$container_id" ]] ||
    fail "No container found for $service"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    status="$(
      docker inspect \
        --format '{{.State.Status}}' \
        "$container_id"
    )"

    if [[ "$status" == "running" ]]; then
      log "$service is running"
      return 0
    fi

    if [[ "$status" == "exited" ||
          "$status" == "dead" ]]; then
      fail "$service stopped unexpectedly"
    fi

    sleep 3
  done

  fail "$service did not start in time"
}

wait_for_job() {
  local service="$1"
  local attempts="${2:-120}"
  local container_id
  local status
  local exit_code

  container_id="$(
    docker compose \
      -p "$PROJECT" \
      -f docker-compose.cloud.yml \
      -f docker-compose.bonus.yml \
      ps -a -q "$service"
  )"

  [[ -n "$container_id" ]] ||
    fail "No container found for $service"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    status="$(
      docker inspect \
        --format '{{.State.Status}}' \
        "$container_id"
    )"

    if [[ "$status" == "exited" ]]; then
      exit_code="$(
        docker inspect \
          --format '{{.State.ExitCode}}' \
          "$container_id"
      )"

      [[ "$exit_code" == "0" ]] ||
        fail "$service exited with code $exit_code"

      log "$service completed successfully"
      return 0
    fi

    if [[ "$status" == "dead" ]]; then
      fail "$service container is dead"
    fi

    sleep 5
  done

  fail "$service initialization timed out"
}

rollback_backend() {
  log "Attempting Student 3 backend rollback"

  if [[ ! -d "$BASELINE" ]]; then
    log "Baseline directory unavailable"
    return 1
  fi

  (
    cd "$BASELINE"

    [[ -n "$ORIGINAL_BACKEND_IMAGE" ]] || return 1

    docker image inspect "$ORIGINAL_BACKEND_IMAGE" >/dev/null ||
      return 1

    # Pin rollback to the exact image running before deployment.
    local rollback_override
    rollback_override="$(mktemp "$BASELINE_REAL/rollback.XXXXXX.yml")"

    printf 'services:\n  student3-backend:\n    image: "%s"\n    build: !reset null\n' \
      "$ORIGINAL_BACKEND_IMAGE" > "$rollback_override"

    if docker compose \
      -p "$PROJECT" \
      -f docker-compose.cloud.yml \
      -f "$rollback_override" \
      up -d --no-deps --force-recreate --no-build "$BACKEND"; then
      rm -f -- "$rollback_override"
    else
      rm -f -- "$rollback_override"
      return 1
    fi
  ) || return 1

  log "Checking restored backend"

  for ((attempt = 1; attempt <= 30; attempt++)); do
    if curl \
      --fail \
      --silent \
      --show-error \
      --max-time 5 \
      http://127.0.0.1:8003/health \
      >/dev/null 2>&1; then

      log "Student 3 backend restored"
      return 0
    fi

    sleep 3
  done

  log "Rollback health check failed"
  return 1
}

on_exit() {
  local exit_code=$?

  trap - EXIT

  if [[ "$DEPLOYMENT_SUCCESS" == "1" ]]; then
    exit 0
  fi

  if [[ "$BACKEND_SWITCHED" == "1" ]]; then
    if rollback_backend; then
      log "Rollback completed"
    else
      log "WARNING: Manual backend recovery required"
    fi
  else
    log "Student 3 backend was not switched"
  fi

  exit "$exit_code"
}

trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

log "Validating environment"

[[ "$(id -u)" == "0" ]] ||
  fail "Run this script with sudo"

[[ "$RELEASE_ID" =~ ^[a-zA-Z0-9._-]+$ ]] ||
  fail "Invalid release ID"

[[ "$EXPECTED_SHA" =~ ^[a-fA-F0-9]{64}$ ]] ||
  fail "Invalid SHA256"

require_file "$ARCHIVE"

[[ -L "$BASELINE" ]] ||
  fail "Baseline current pointer must be a symlink"

BASELINE_REAL="$(readlink -f "$BASELINE")"

[[ -d "$BASELINE_REAL" ]] ||
  fail "Baseline release directory is unavailable"

require_file "$BASELINE_REAL/docker-compose.cloud.yml"

log "Baseline release: $BASELINE_REAL"

command -v docker >/dev/null ||
  fail "Docker is not installed"

command -v curl >/dev/null ||
  fail "curl is not installed"

command -v python3 >/dev/null ||
  fail "Python is not installed"

docker compose version >/dev/null ||
  fail "Docker Compose is unavailable"

log "Checking archive checksum"

ACTUAL_SHA="$(sha256sum "$ARCHIVE" | cut -d' ' -f1)"

[[ "${ACTUAL_SHA,,}" == "${EXPECTED_SHA,,}" ]] ||
  fail "Archive checksum mismatch"

log "Checking existing baseline"

cd "$BASELINE"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  config --quiet

BASELINE_BACKEND_ID="$(
  docker compose \
    -p "$PROJECT" \
    -f docker-compose.cloud.yml \
    ps -q "$BACKEND"
)"

[[ -n "$BASELINE_BACKEND_ID" ]] ||
  fail "Existing Student 3 backend not found"

BASELINE_STATUS="$(
  docker inspect \
    --format '{{.State.Status}}' \
    "$BASELINE_BACKEND_ID"
)"

[[ "$BASELINE_STATUS" == "running" ]] ||
  fail "Existing Student 3 backend is not running"

ORIGINAL_BACKEND_CONTAINER="$BASELINE_BACKEND_ID"

ORIGINAL_BACKEND_IMAGE="$(
  docker inspect     --format '{{.Image}}'     "$ORIGINAL_BACKEND_CONTAINER"
)"

[[ -n "$ORIGINAL_BACKEND_IMAGE" ]] ||
  fail "Unable to capture original backend image"

docker image inspect "$ORIGINAL_BACKEND_IMAGE" >/dev/null ||
  fail "Original backend image unavailable"

log "Original Student 3 backend image captured"

curl \
  --fail \
  --silent \
  --show-error \
  --max-time 10 \
  http://127.0.0.1:8003/health \
  >/dev/null ||
  fail "Existing Student 3 backend health failed"

log "Existing Student 3 backend healthy"

BASELINE_AI_SETTING="$(
  docker compose     -p "$PROJECT"     -f docker-compose.cloud.yml     config --format json |
  python3 -c '
import json
import sys

config = json.load(sys.stdin)
service = config["services"]["student3-backend"]
env = service.get("environment", {})
if isinstance(env, list):
    env = dict(item.split("=", 1) for item in env)
print(str(env.get("AI_SERVICES_ENABLED", "")).lower())
'
)"

[[ "$BASELINE_AI_SETTING" == "false" ]] ||
  fail "Baseline AI configuration is not disabled; refusing unsafe rollback"

log "Baseline rollback configuration verified"

[[ ! -e "$RELEASE" ]] ||
  fail "Release directory already exists"

mkdir -p "$ROOT/releases"
mkdir "$RELEASE"

log "Checking archive member paths"

python3 - "$ARCHIVE" "$RELEASE" <<'PY'
import pathlib
import sys
import tarfile

archive_path = sys.argv[1]
destination = pathlib.Path(sys.argv[2]).resolve()

with tarfile.open(archive_path, "r:gz") as archive:
    members = archive.getmembers()

    for member in members:
        path = pathlib.PurePosixPath(member.name)

        if (
            path.is_absolute()
            or ".." in path.parts
            or not member.isfile()
        ):
            raise SystemExit(
                f"Unsafe archive member: {member.name}"
            )

        target = destination.joinpath(*path.parts)

        if not target.resolve().is_relative_to(destination):
            raise SystemExit("Archive path escapes release directory")

    for member in members:
        target = destination.joinpath(
            *pathlib.PurePosixPath(member.name).parts
        )

        target.parent.mkdir(parents=True, exist_ok=True)

        source = archive.extractfile(member)

        if source is None:
            raise SystemExit("Archive member could not be read")

        with source, target.open("xb") as output:
            import shutil
            shutil.copyfileobj(source, output)
PY

cd "$RELEASE"

require_file docker-compose.cloud.yml
require_file docker-compose.bonus.yml
require_file scripts/cloud/bonus-health-check.sh

log "Validating combined Compose configuration"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  config --quiet

log "Building Bonus services"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  build \
  mcp-server \
  rag-init \
  rag-server \
  multi-agent-server

log "Starting Ollama"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  ollama

wait_for_container ollama

log "Starting MCP"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  mcp-server

wait_for_container mcp-server

log "Downloading Ollama model"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  ollama-init

wait_for_job ollama-init 180

log "Building RAG knowledge index"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  rag-init

wait_for_job rag-init 120

log "Starting RAG server"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  rag-server

wait_for_container rag-server

log "Starting Multi-Agent server"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  multi-agent-server

wait_for_container multi-agent-server

log "All Bonus dependencies started"

log "Switching Student 3 backend to Bonus configuration"

# Set before the command so a partial recreation triggers rollback.
BACKEND_SWITCHED=1

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  up -d \
  --no-deps \
  --force-recreate \
  "$BACKEND"

log "Waiting for Student 3 backend health"

BACKEND_HEALTHY=0

for ((attempt = 1; attempt <= 40; attempt++)); do
  if curl \
    --fail \
    --silent \
    --show-error \
    --max-time 5 \
    http://127.0.0.1:8003/health \
    >/dev/null 2>&1; then

    BACKEND_HEALTHY=1
    break
  fi

  sleep 3
done

[[ "$BACKEND_HEALTHY" == "1" ]] ||
  fail "Student 3 backend did not become healthy"

log "Running B1-B4 functional verification"

BASE_URL=http://127.0.0.1:8003 \
  bash scripts/cloud/bonus-health-check.sh

log "Checking Student 3 CRUD read"

curl \
  --fail \
  --silent \
  --show-error \
  --max-time 15 \
  http://127.0.0.1:8003/resources \
  >/dev/null

log "Checking service status"

docker compose \
  -p "$PROJECT" \
  -f docker-compose.cloud.yml \
  -f docker-compose.bonus.yml \
  ps \
  ollama \
  mcp-server \
  rag-server \
  multi-agent-server \
  student3-backend

DEPLOYMENT_SUCCESS=1

log "GROUP5_STUDENT3_AZURE_BONUS_DEPLOYMENT_PASSED"
