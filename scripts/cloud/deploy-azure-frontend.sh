#!/usr/bin/env bash
set -Eeuo pipefail

# Azure Student 3 frontend-only deployment transport.
# Existing VM only. No infrastructure provisioning.

RESOURCE_GROUP="${RESOURCE_GROUP:-asd-group5-rg}"
VM_NAME="${VM_NAME:-asd-group5-vm}"
ADMIN_USERNAME="${ADMIN_USERNAME:-azureuser}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="${SOURCE_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

: "${SSH_PRIVATE_KEY_PATH:?SSH_PRIVATE_KEY_PATH is required}"
: "${SSH_PUBLIC_KEY:?SSH_PUBLIC_KEY is required}"

[[ "$VM_NAME" =~ ^[a-zA-Z0-9-]+$ ]] ||
  { echo "Invalid VM name" >&2; exit 1; }

[[ "$ADMIN_USERNAME" =~ ^[a-z_][a-z0-9_-]*$ ]] ||
  { echo "Invalid SSH username" >&2; exit 1; }

[[ -f "$SSH_PRIVATE_KEY_PATH" ]] ||
  { echo "SSH private key not found" >&2; exit 1; }

[[ "$SSH_PUBLIC_KEY" == ssh-* ]] ||
  { echo "Invalid SSH public key" >&2; exit 1; }

for command_name in az ssh scp ssh-keygen python3 curl; do
  command -v "$command_name" >/dev/null ||
    { echo "Missing command: $command_name" >&2; exit 1; }
done

python3 - "$SSH_PRIVATE_KEY_PATH" <<'PY'
import os
import stat
import sys

mode = stat.S_IMODE(os.stat(sys.argv[1]).st_mode)
if mode & 0o077:
    raise SystemExit("SSH private key permissions must be 600 or stricter")
PY

ACTUAL_PUBLIC_KEY="$(
  ssh-keygen -y -P '' -f "$SSH_PRIVATE_KEY_PATH"
)"

[[ "$(awk '{print $1 " " $2}' <<< "$SSH_PUBLIC_KEY")" == \
   "$(awk '{print $1 " " $2}' <<< "$ACTUAL_PUBLIC_KEY")" ]] ||
  { echo "SSH key pair mismatch" >&2; exit 1; }

SSH_SOURCE_CIDR="${SSH_SOURCE_CIDR:-$(curl -fsS --retry 3 https://api.ipify.org)/32}"

python3 - "$SSH_SOURCE_CIDR" <<'PY'
import ipaddress
import sys

network = ipaddress.ip_network(sys.argv[1], strict=True)

if (
    network.version != 4
    or network.prefixlen != 32
    or not network.network_address.is_global
):
    raise SystemExit("SSH source must be one public IPv4 /32")
PY

umask 077

WORK_DIR="$(mktemp -d)"
SSH_RULE_CREATED=0
REMOTE_DIR=""
VM_IP=""
SSH_OPTIONS=()

cleanup() {
  local result=$?
  trap - EXIT

  if [[ -n "$REMOTE_DIR" && -n "$VM_IP" ]]; then
    ssh "${SSH_OPTIONS[@]}" \
      "$ADMIN_USERNAME@$VM_IP" \
      "rm -rf -- '$REMOTE_DIR'" \
      >/dev/null 2>&1 ||
      echo "WARNING: Remote staging cleanup failed" >&2
  fi

  if [[ "$SSH_RULE_CREATED" == "1" ]]; then
    if ! az network nsg rule delete \
      --resource-group "$RESOURCE_GROUP" \
      --nsg-name "$VM_NAME-nsg" \
      --name CloudStudent3FrontendSSH \
      --output none; then

      echo "CRITICAL: Remove CloudStudent3FrontendSSH manually" >&2
      result=1
    fi
  fi

  rm -rf -- "$WORK_DIR"
  exit "$result"
}

trap cleanup EXIT

echo "===== Package committed Student 3 frontend ====="

FRONTEND_PACKAGE_OUTPUT="$WORK_DIR/student3-frontend.tar.gz" \
  python3 "$SCRIPT_DIR/package_frontend.py"


SHA256="$(
  python3 - "$WORK_DIR/student3-frontend.tar.gz" <<'PY'
import hashlib
import sys

digest = hashlib.sha256()

with open(sys.argv[1], "rb") as source:
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)

print(digest.hexdigest())
PY
)"

echo "===== Verify existing Azure VM ====="

az account show --query "{name:name,state:state}" --output table

az group show \
  --name "$RESOURCE_GROUP" \
  --query name \
  --output tsv >/dev/null

VM_ID="$(
  az vm show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query id \
    --output tsv
)"

[[ -n "$VM_ID" ]] ||
  { echo "Existing Azure VM not found" >&2; exit 1; }

VM_STATE="$(
  az vm get-instance-view \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query "instanceView.statuses[?starts_with(code, 'PowerState/')].code | [0]" \
    --output tsv
)"

[[ "$VM_STATE" == "PowerState/running" ]] ||
  { echo "VM must already be running: $VM_STATE" >&2; exit 1; }

VM_IP="$(
  az vm show -d \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query publicIps \
    --output tsv
)"

python3 - "$VM_IP" <<'PY'
import ipaddress
import sys

ipaddress.IPv4Address(sys.argv[1])
PY

echo "===== Authenticate VM SSH host key ====="

HOST_RESULT="$(
  az vm run-command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --command-id RunShellScript \
    --scripts \
      "printf 'GROUP5_SSH_HOST_KEY '; cat /etc/ssh/ssh_host_ed25519_key.pub" \
    --output json
)"

python3 - "$VM_IP" "$WORK_DIR/known_hosts" "$HOST_RESULT" <<'PY'
import json
import sys

ip = sys.argv[1]
output = sys.argv[2]
result = json.loads(sys.argv[3])

entries = result.get("value", [])

if not entries or not all(
    item.get("code", "").endswith("/succeeded")
    for item in entries
):
    raise SystemExit("Azure host-key retrieval failed")

lines = [
    line
    for entry in entries
    for line in entry.get("message", "").splitlines()
    if line.startswith("GROUP5_SSH_HOST_KEY ssh-ed25519 ")
]

if len(lines) != 1:
    raise SystemExit("Expected exactly one authenticated SSH host key")

parts = lines[0].split()

if len(parts) < 3:
    raise SystemExit("Malformed SSH host key")

with open(output, "w", encoding="utf-8") as handle:
    handle.write(f"{ip} {parts[1]} {parts[2]}\n")
PY

SSH_OPTIONS=(
  -i "$SSH_PRIVATE_KEY_PATH"
  -o IdentitiesOnly=yes
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$WORK_DIR/known_hosts"
  -o HostKeyAlgorithms=ssh-ed25519
  -o ConnectTimeout=15
  -o LogLevel=ERROR
)

echo "===== Check temporary SSH rule ====="

EXISTING_RULE="$(
  az network nsg rule list \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "$VM_NAME-nsg" \
    --query "[?name=='CloudStudent3FrontendSSH'].name | [0]" \
    --output tsv
)"

[[ -z "$EXISTING_RULE" ]] ||
  { echo "Temporary frontend SSH rule already exists; refusing to overwrite" >&2; exit 1; }

PRIORITY_CONFLICT="$(
  az network nsg rule list \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "$VM_NAME-nsg" \
    --query "[?priority==\`212\` && direction=='Inbound'].name | [0]" \
    --output tsv
)"

[[ -z "$PRIORITY_CONFLICT" ]] || {
  echo "NSG inbound priority 212 is already used: $PRIORITY_CONFLICT" >&2
  exit 1
}

echo "===== Open temporary SSH access ====="

# Set cleanup flag before creation to cover partial CLI failures.
SSH_RULE_CREATED=1

az network nsg rule create \
  --resource-group "$RESOURCE_GROUP" \
  --nsg-name "$VM_NAME-nsg" \
  --name CloudStudent3FrontendSSH \
  --priority 212 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes "$SSH_SOURCE_CIDR" \
  --destination-port-ranges 22 \
  --output none

echo "===== Verify SSH connection ====="

READY=0

for attempt in {1..20}; do
  if ssh "${SSH_OPTIONS[@]}" "$ADMIN_USERNAME@$VM_IP" true; then
    READY=1
    break
  fi
  sleep 3
done

[[ "$READY" == "1" ]] ||
  { echo "Verified SSH connection unavailable" >&2; exit 1; }

RELEASE_ID="$(
  date -u +%Y%m%dT%H%M%SZ
)-${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"

[[ "$RELEASE_ID" =~ ^[a-zA-Z0-9._-]+$ ]] ||
  { echo "Invalid release ID" >&2; exit 1; }

REMOTE_DIR="/tmp/group5-frontend-$RELEASE_ID"

echo "===== Upload Student 3 frontend release ====="

ssh "${SSH_OPTIONS[@]}" \
  "$ADMIN_USERNAME@$VM_IP" \
  "umask 077; mkdir -- '$REMOTE_DIR'"

scp "${SSH_OPTIONS[@]}" \
  "$WORK_DIR/student3-frontend.tar.gz" \
  "$SCRIPT_DIR/configure-frontend-vm.sh" \
  "$ADMIN_USERNAME@$VM_IP:$REMOTE_DIR/"

echo "===== Deploy and verify Student 3 frontend ====="

ssh "${SSH_OPTIONS[@]}" \
  "$ADMIN_USERNAME@$VM_IP" \
  "sudo -- bash '$REMOTE_DIR/configure-frontend-vm.sh' \
  '$REMOTE_DIR/student3-frontend.tar.gz' '$SHA256' '$RELEASE_ID'"

echo "GROUP5_STUDENT3_FRONTEND_UPLOAD_AND_DEPLOY_PASSED"
