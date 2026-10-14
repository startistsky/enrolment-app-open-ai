#!/usr/bin/env bash
set -Eeuo pipefail
RESOURCE_GROUP=${RESOURCE_GROUP:-asd-group5-rg}
VM_NAME=${VM_NAME:-asd-group5-vm}
az vm deallocate -g "$RESOURCE_GROUP" -n "$VM_NAME"
az vm get-instance-view -g "$RESOURCE_GROUP" -n "$VM_NAME" --query instanceView.statuses -o table
 echo 'VM deallocated. Disk and public-IP charges may remain.'
