#!/usr/bin/env bash
# Never sourced or executed by local validation. Execution creates billable resources.
set -Eeuo pipefail
trap 'echo "Azure deployment failed at line $LINENO" >&2' ERR
RESOURCE_GROUP=${RESOURCE_GROUP:-asd-group5-rg}
LOCATION=${LOCATION:-australiaeast}
VM_NAME=${VM_NAME:-asd-group5-vm}
VM_SIZE=${VM_SIZE:-Standard_B2s}
ADMIN_USERNAME=${ADMIN_USERNAME:-azureuser}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR=${SOURCE_DIR:-$(cd "$script_dir/../.." && pwd)}
: "${SSH_PRIVATE_KEY_PATH:?Set the path to your deployment SSH private key}"
: "${SSH_PUBLIC_KEY:?Set an SSH public key; never a private key}"
: "${HTTP_SOURCE_CIDR:?Set the assessor/team public IP CIDR allowed to access the demo}"
[[ "$VM_NAME" =~ ^[a-zA-Z0-9-]+$ ]] || { echo 'Invalid VM name' >&2; exit 1; }
[[ "$SSH_PUBLIC_KEY" == ssh-* ]] || { echo 'Expected an OpenSSH public key' >&2; exit 1; }
[[ "$ADMIN_USERNAME" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'Invalid admin username' >&2; exit 1; }
[[ -f "$SSH_PRIVATE_KEY_PATH" ]] || { echo 'SSH private-key file not found' >&2; exit 1; }
# SSH refuses permissive key files; also fail clearly before provisioning anything.
python3 - "$SSH_PRIVATE_KEY_PATH" <<'PYCODE'
import os, stat, sys
if stat.S_IMODE(os.stat(sys.argv[1]).st_mode) & 0o077:
    raise SystemExit('SSH private key must have chmod 600 or stricter permissions')
PYCODE
ssh_public_from_private=$(ssh-keygen -y -P '' -f "$SSH_PRIVATE_KEY_PATH")
[[ $(awk '{print $1 " " $2}' <<< "$SSH_PUBLIC_KEY") == $(awk '{print $1 " " $2}' <<< "$ssh_public_from_private") ]] || { echo 'SSH public/private keys do not match' >&2; exit 1; }
SSH_SOURCE_CIDR=${SSH_SOURCE_CIDR:-$(curl --fail --silent --show-error --retry 3 https://api.ipify.org)/32}
python3 - "$SSH_SOURCE_CIDR" <<'PYCODE'
import ipaddress, sys
network = ipaddress.ip_network(sys.argv[1], strict=True)
if network.version != 4 or network.prefixlen != 32 or not network.network_address.is_global:
    raise SystemExit('SSH_SOURCE_CIDR must identify one public IPv4 address (/32)')
PYCODE
umask 077
work_dir=$(mktemp -d)
ssh_rule_created=false
remote_dir=''
cleanup() {
  result=$?
  trap - EXIT
  if [[ -n "$remote_dir" ]]; then
    ssh "${ssh_options[@]}" "$ADMIN_USERNAME@$ip" "rm -rf -- '$remote_dir'" >/dev/null 2>&1 || echo 'Remote upload cleanup failed; remove the private staging directory manually.' >&2
  fi
  if [[ "$ssh_rule_created" == true ]]; then
    az network nsg rule delete -g "$RESOURCE_GROUP" --nsg-name "$VM_NAME-nsg" -n CloudDeploymentSSH -o none || { echo 'SSH rule cleanup failed; delete CloudDeploymentSSH manually.' >&2; result=1; }
  fi
  rm -rf -- "$work_dir"
  exit "$result"
}
trap cleanup EXIT
# Package first; includes checked-out changes, excludes credentials/Git metadata/runtime data.
python3 "$script_dir/package_source.py" --source-dir "$SOURCE_DIR" --output "$work_dir/source.tar.gz"
checksum=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$work_dir/source.tar.gz")
command -v az >/dev/null
az account show --query '{subscription:name,state:state}' -o table
az group show --name "$RESOURCE_GROUP" --query name -o tsv >/dev/null
# Discover existing resources without treating authentication/network errors as absence.
exists=$(az vm list -g "$RESOURCE_GROUP" --query "[?name=='$VM_NAME'].name" -o tsv)
if [[ -z "$exists" ]]; then
  az network nsg create -g "$RESOURCE_GROUP" -n "$VM_NAME-nsg" -l "$LOCATION" -o none
  az network vnet create -g "$RESOURCE_GROUP" -n "$VM_NAME-vnet" -l "$LOCATION" \
    --address-prefixes 10.55.0.0/16 --subnet-name cloud-baseline --subnet-prefixes 10.55.1.0/24 -o none
  az network public-ip create -g "$RESOURCE_GROUP" -n "$VM_NAME-ip" -l "$LOCATION" \
    --sku Standard --allocation-method Static -o none
  az network nic create -g "$RESOURCE_GROUP" -n "$VM_NAME-nic" -l "$LOCATION" \
    --vnet-name "$VM_NAME-vnet" --subnet cloud-baseline --network-security-group "$VM_NAME-nsg" \
    --public-ip-address "$VM_NAME-ip" -o none
  az vm create -g "$RESOURCE_GROUP" -n "$VM_NAME" -l "$LOCATION" \
    --image Ubuntu2404 --size "$VM_SIZE" --admin-username "$ADMIN_USERNAME" \
    --authentication-type ssh --ssh-key-values "$SSH_PUBLIC_KEY" \
    --nics "$VM_NAME-nic" --nic-delete-option Delete --storage-sku Standard_LRS \
    --os-disk-size-gb 32 \
    --os-disk-name "$VM_NAME-osdisk" --os-disk-delete-option Delete -o none
else
  az vm start -g "$RESOURCE_GROUP" -n "$VM_NAME" -o none
fi
# Only frontend ports are permanently allowed; deployment SSH is temporary.
az network nsg rule create -g "$RESOURCE_GROUP" --nsg-name "$VM_NAME-nsg" \
  -n CloudFrontend --priority 200 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes "$HTTP_SOURCE_CIDR" --destination-port-ranges 8080 8081 8082 8083 8085 8888 -o none
ip=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query publicIps -o tsv)
python3 - "$ip" <<'PYCODE'
import ipaddress, sys
ipaddress.IPv4Address(sys.argv[1])
PYCODE
# Read the SSH host key through Azure's authenticated control plane, not ssh-keyscan.
host_result=$(az vm run-command invoke -g "$RESOURCE_GROUP" -n "$VM_NAME" \
  --command-id RunShellScript --scripts "printf 'GROUP5_SSH_HOST_KEY '; cat /etc/ssh/ssh_host_ed25519_key.pub" -o json)
python3 -c 'import json,sys; result=json.load(sys.stdin); entries=result.get("value",[]); lines=[line for entry in entries for line in entry.get("message", "").splitlines() if line.startswith("GROUP5_SSH_HOST_KEY ssh-ed25519 ")]; assert len(lines)==1 and all(e.get("code", "").endswith("/succeeded") for e in entries), "Could not authenticate VM host key"; print(sys.argv[1], " ".join(lines[0].split()[1:3]))' "$ip" <<< "$host_result" > "$work_dir/known_hosts"
# Open SSH to this runner/developer's single IPv4 address only, then close it on exit.
ssh_rule_created=true
az network nsg rule create -g "$RESOURCE_GROUP" --nsg-name "$VM_NAME-nsg" \
  -n CloudDeploymentSSH --priority 210 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes "$SSH_SOURCE_CIDR" --destination-port-ranges 22 -o none
ssh_options=(-i "$SSH_PRIVATE_KEY_PATH" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$work_dir/known_hosts" \
  -o HostKeyAlgorithms=ssh-ed25519 -o ConnectTimeout=15 -o LogLevel=ERROR)
# Wait for sshd without ever bypassing host-key verification.
ready=false
for attempt in {1..20}; do
  if ssh "${ssh_options[@]}" "$ADMIN_USERNAME@$ip" true; then ready=true; break; fi
  sleep 3
done
[[ "$ready" == true ]] || { echo 'Verified SSH connection did not become ready' >&2; exit 1; }
release_id="$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$work_dir" | tr -cd 'a-zA-Z0-9')"
remote_dir="/tmp/group5-$release_id"
ssh "${ssh_options[@]}" "$ADMIN_USERNAME@$ip" "umask 077; mkdir -- '$remote_dir'"
scp "${ssh_options[@]}" "$work_dir/source.tar.gz" "$script_dir/configure-vm.sh" "$ADMIN_USERNAME@$ip:$remote_dir/"
ssh "${ssh_options[@]}" "$ADMIN_USERNAME@$ip" \
  "sudo -- bash '$remote_dir/configure-vm.sh' '$remote_dir/source.tar.gz' '$checksum' '$release_id'"
for port in 8888 8081 8082 8083 8080 8085; do
  printf 'Frontend URL: http://%s:%s\n' "$ip" "$port"
done
