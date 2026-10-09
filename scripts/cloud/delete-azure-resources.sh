#!/usr/bin/env bash
set -Eeuo pipefail
RESOURCE_GROUP=${RESOURCE_GROUP:-asd-group5-rg}
VM_NAME=${VM_NAME:-asd-group5-vm}
[[ "$VM_NAME" =~ ^[a-zA-Z0-9-]+$ ]] || { echo 'Invalid VM name' >&2; exit 1; }
echo "Will permanently delete $VM_NAME, its OS disk, NIC, public IP, NSG and VNet in $RESOURCE_GROUP."
echo 'Named Docker volumes on the OS disk will be lost. The resource group will remain.'
read -r -p "Type DELETE $RESOURCE_GROUP/$VM_NAME to confirm: " confirmation
[[ "$confirmation" == "DELETE $RESOURCE_GROUP/$VM_NAME" ]] || { echo 'Deletion cancelled'; exit 1; }
# Only delete the explicitly named assessment deployment; never delete the shared resource group.
az vm delete -g "$RESOURCE_GROUP" -n "$VM_NAME" --yes
# NIC and OS disk use Delete lifecycle options; these commands remove residual network resources.
az network public-ip delete -g "$RESOURCE_GROUP" -n "$VM_NAME-ip"
az network nsg delete -g "$RESOURCE_GROUP" -n "$VM_NAME-nsg"
az network vnet delete -g "$RESOURCE_GROUP" -n "$VM_NAME-vnet"
echo 'Inspect the resource group for leftovers before ending the assessment.'
