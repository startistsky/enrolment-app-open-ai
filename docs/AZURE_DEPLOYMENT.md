# Group 5 Azure deployment preparation

Status: repository prepared for validation. No Azure resources have been created
by this work, and no deployment or Cloud Deployment Review PASS is claimed.

## Architecture and subscription

GitHub Actions (manual dispatch, Azure OIDC) → Azure Linux VM (Ubuntu 24.04) →
Docker Compose frontend/backend/SQLite baseline. The existing resource group is
`asd-group5-rg`, region `australiaeast`, subscription context **Azure for Students**.
Confirm the selected subscription with `az account show` before executing scripts.
The scripts intentionally do not create or delete the shared resource group.

`docker-compose.cloud.yml` contains all five modules plus the shared frontend.
Student 1–4 use internal database APIs. Student 5 has a one-shot database seed
container and a backend that accesses the same named SQLite volume directly;
its database container is not an HTTP service. Five named volumes retain database
data across container recreation. They live on the VM OS disk, not external storage.

Frontend URLs use the VM hostname/IP and existing module ports:

| Module | Public port | Backend (VM loopback only) |
| --- | --- | --- |
| Shared home | 8888 | — |
| Courses | 8081 | 8001 |
| Assignments | 8082 | 8002 |
| Resources | 8083 | 8003 |
| Events | 8080 | 8000 |
| Career | 8085 | 8005 |

Nginx proxies browser API requests using Compose DNS names. Browser navigation
uses port metadata to build links on the current hostname and protocol. No database
ports are published. Loopback in health checks refers to the container/VM itself;
it is not a browser or container-to-container address. The cloud file contains no
`host.docker.internal` references. Unused legacy top-level Student Dockerfiles
are empty and are not selected by either Compose file.

## Local versus cloud and disabled AI

The local `docker-compose.yml` remains unchanged and retains Ollama and host
services. Local behavior defaults to AI enabled. Cloud sets
`AI_SERVICES_ENABLED=false` on every backend and clears all AI/MCP/RAG/Multi-Agent
URLs. Server request guards reject relevant routes with HTTP 503 before any model,
MCP, RAG, or Multi-Agent work. No Ollama, MCP, RAG or Multi-Agent container is
included. Existing UI controls may remain visible and report the disabled response.
Flask debug is disabled for cloud. This is an assessment baseline, not a production
TLS/authentication deployment.

## Audit and compatibility fixes

- Student 2 and 5 API clients used the browser's localhost: now use same-origin
  `/api`; Student 2 gained an nginx API proxy.
- Student 3 used a separate public backend port: now uses same-origin routes with
  an nginx proxy; the database receives `/data/campus_resources.db` on a named volume.
- Integrated navigation previously sent remote users to their own localhost:
  links now follow the current hostname while retaining local module ports.
- Student 5 ignored `DATABASE_PATH`: both seed and backend now respect the shared
  `/data/career.db` path, retaining the prior path when the variable is absent.
- Backends lacked a cloud disable guard: explicit cloud configuration now blocks
  all AI route families, including Student 1 Release 1 validation routes.
- Container health dependencies replace local Ollama startup dependencies.
- Student 4/5 Flask debug defaults are retained locally and explicitly disabled
  in cloud. Existing seed scripts keep existing data when populated.

## Prerequisites and deployment

The repository stays **private**. Deployment transfers the checked-out application
from GitHub Actions or a developer machine; the VM never clones/fetches from GitHub
and receives no repository token or Git metadata. The workflow's selected private
branch must contain these files when deployment is later dispatched. Local deployment
can use the current checkout, including eligible uncommitted/untracked source files.
This preparation does not commit, push, execute deployment scripts or create resources.
Confirm the `Standard_B2s` quota/availability in Australia East for Azure for Students.

Authenticate with Azure CLI and configure on a developer machine:

```sh
export RESOURCE_GROUP=asd-group5-rg
export LOCATION=australiaeast
export VM_NAME=asd-group5-vm
export SOURCE_DIR="$PWD"
export SSH_PUBLIC_KEY="$(cat ~/.ssh/id_ed25519.pub)"
export SSH_PRIVATE_KEY_PATH="$HOME/.ssh/id_ed25519"
chmod 600 "$SSH_PRIVATE_KEY_PATH"
export HTTP_SOURCE_CIDR=YOUR_PUBLIC_IP/32
# SSH_SOURCE_CIDR optionally overrides automatic public IPv4 discovery; must be /32.
# Executing the following creates billable resources; only execute at deployment time.
bash scripts/cloud/deploy-azure-vm.sh
```

Use a dedicated matching deployment key pair. Automated deployment requires an
unencrypted key (interactive passphrase prompts are disabled); protect the private
key in GitHub secrets or your local file permissions. Do not commit either deployment
key or place key files inside the application checkout. Local private keys remain at
the developer-supplied path; the script does not remove a developer's existing key.
GitHub writes its secret into a temporary file with mode 600 and deletes it on exit.
The private key is used only by the SSH/SCP deployment connection, never uploaded
to the VM, printed in logs or included in application packaging. The public key is
used for VM creation and must match the private key. Existing VMs must already
authorize that matching key and use the configured admin username.

The deployment script:

1. Packages application source from the checkout, before provisioning. The archive
   includes Student 1–5, shared frontend, cloud Compose and the health script.
   Git metadata, checkout credentials, `.env` files (except `.env.example`), local
   key files, database files, runtime JSONL, caches and virtual environments are
   excluded. Symlinks are rejected. Review source for embedded credentials before
   deployment; filename filtering cannot detect credentials embedded in source.
2. Creates or starts the configured VM in the existing resource group.
3. Obtains the VM's Ed25519 SSH **host public key** using authenticated Azure Run
   Command and writes a temporary `known_hosts` entry. SSH/SCP require strict
   host-key checking; they never trust an unauthenticated `ssh-keyscan` result.
4. Opens TCP 22 only from the current runner/developer public IPv4 `/32`, obtained
   via HTTPS from `api.ipify.org` (or supplied as `SSH_SOURCE_CIDR`). Transfer fails
   if the deployment connection uses a different NAT egress address.
5. Transfers the application archive and configuration script over SSH/SCP. Guest
   setup verifies the SHA256 and rejects unsafe archive entries, then extracts into
   a root-owned private `/opt/asd-group5/releases/<release-id>` directory. It installs
   Docker/Compose from Ubuntu packages, builds/starts the baseline and runs health
   checks. It switches `/opt/asd-group5/current` after successful validation.
6. Removes upload staging and the temporary SSH rule on exit; the runner removes
   its temporary key file. Database volumes retain the stable `asd-group5-cloud`
   Compose project name across releases. No `down -v` is run.

Azure Run Command only retrieves the public host key; it carries no GitHub or SSH
private credentials. See Microsoft's [Run Command documentation](https://learn.microsoft.com/en-us/cli/azure/vm/run-command).
Run Command and SSH deployment need appropriate resource-group permissions and VM
agent connectivity. Restrict who can dispatch this workflow and change its scripts.
No additional Azure storage account or source-download credential is required.

Successful releases are retained for diagnosis; manually remove unused release
folders after collecting evidence. A failed deployment can partially replace
containers even though the current link is unchanged: automatic rollback is not
implemented. Never run local and GitHub deployments concurrently against the same VM.
Normal error handling closes SSH; forced runner termination or Azure API failure
can leave `CloudDeploymentSSH` behind. Check/delete that rule after cancelled/failed
runs. Any leftover rule is still restricted to the single deployment IPv4 address.

Expected named resources created in the existing group:

- VM `asd-group5-vm`, Ubuntu 24.04, size `Standard_B2s`.
- Managed OS disk `asd-group5-vm-osdisk`, 32 GiB, Standard LRS.
- VNet `asd-group5-vm-vnet` and subnet `cloud-baseline`.
- NSG `asd-group5-vm-nsg`, rule `CloudFrontend` allowing TCP 8080, 8081, 8082, 8083, 8085
  and 8888 from `HTTP_SOURCE_CIDR`; `CloudDeploymentSSH` temporarily allows TCP 22
  from the deployment public IPv4 `/32`. Port 8084 is not opened.
- Standard static public IP `asd-group5-vm-ip`.
- NIC `asd-group5-vm-nic` attached to that VNet/NSG/public IP.

No AI infrastructure, managed database, new subscription, or resource group is created.
An existing VM must be the deployment created by this script with its named NSG;
this is not an arbitrary existing-VM migration tool.

## GitHub manual workflow

`.github/workflows/cloud-deployment.yml` has only `workflow_dispatch`.
Create an `azure-assessment` GitHub environment and configure its branch policy
and optional approval protection. Configure an Entra application/service principal
with an OIDC federated credential for
`repo:OWNER/REPOSITORY:environment:azure-assessment`; grant deployment permissions
scoped to `asd-group5-rg` (Contributor is sufficient; refine if required).
No client secret is required. See Microsoft's
[Azure GitHub OIDC instructions](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect).

Required repository/environment secrets:

| Secret | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | Entra application client ID |
| `AZURE_TENANT_ID` | Directory tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure for Students subscription ID |
| `AZURE_VM_SSH_PUBLIC_KEY` | Matching OpenSSH public key text |
| `AZURE_VM_SSH_PRIVATE_KEY` | Dedicated deployment private key, unencrypted |

Required repository/environment variable: `AZURE_HTTP_SOURCE_CIDR`, the source CIDR
allowed to browse the frontend. Use the assessor/team `/32` for a restricted demo;
`0.0.0.0/0` is supported when public HTTP assessment access is explicitly desired.
The HTTP rule never includes backend, database or AI ports. The six published
frontend ports are needed by the existing integrated module navigation; nginx reaches
backends internally. Backends bind only to VM loopback for on-VM health checks.
Database APIs have no host port mappings. TCP 22 is temporarily restricted to the
runner's detected IPv4 `/32` and removed afterward; no permanent public SSH rule is
created. HTTP access and SSH access use separate rules and restrictions.

No GitHub PAT, Azure client secret, repository credential or SSH known-host secret
is required. `actions/checkout` accesses the private repository using its built-in
job token with `contents: read` and `persist-credentials: false`; `.git` is excluded
from the application archive. Azure authentication remains OIDC. In Actions,
dispatch with the desired private branch. The workflow logs the deployment outcome
and health checks. Collect external browser/CRUD evidence separately.

## Health and real assessment evidence

On the VM, run `sudo bash /opt/asd-group5/current/scripts/cloud/health-check.sh`. It checks all
frontend pages, backend health, database-backed reads and representative disabled
AI routes. It does not perform write/delete operations or claim full CRUD success.
For diagnosis, use `sudo bash -c 'cd /opt/asd-group5/current && docker compose -p asd-group5-cloud -f docker-compose.cloud.yml ps -a'` and the corresponding `logs` command.
From the allowed external address, open all six URLs printed by deployment.

Collect real evidence later for `reports/cloud-deployment-report.md`:

- Azure platform, resource names, deployment timestamp, deployed commit and real
  successful `.github/workflows/cloud-deployment.yml` run URL.
- External frontend access, backend API access and database connectivity.
- Create/read/update/delete examples for each module, using disposable assessment
  records; confirm persistence after container recreation without deleting volumes.
- Configuration and HTTP evidence that AI Mode, MCP, RAG and Multi-Agent are
  disabled by default, and evidence of frontend navigation/API proxy behavior.
- Human review, completed timestamp, and explicit Accept/Partially Accept/Reject
  release decision, backed by the actual tests and observations.

Follow `shared/RELEASE2_REVIEWS.md` and run only after evidence exists:

```sh
python shared/agentic_loop.py --mode cloud-review \
  --cloud-report reports/cloud-deployment-report.md
```

The preparation contains no fake report and does not change review logic.
A successful health workflow alone is not a Cloud Deployment Review PASS.

## Cost control and cleanup

Deallocate when idle:

```sh
bash scripts/cloud/deallocate-azure-vm.sh
```

Deallocation stops VM compute usage; disk and public-IP costs can remain. Monitor
Azure for Students credit, budget alerts, disk/IP use, and region/SKU availability.
Avoid AI models in this baseline. Do not rely on guest shutdown to deallocate.
Back up SQLite databases consistently before deletion (use SQLite backup or stop
writers first), and export assessment evidence before removing the VM.

After assessment:

```sh
bash scripts/cloud/delete-azure-resources.sh
```

This requires typing the exact deployment target. It permanently removes the VM,
its OS disk/volumes and NIC through lifecycle options, and named IP/NSG/VNet.
It preserves `asd-group5-rg` and unrelated resources. Deletion is not transactional;
inspect the group for leftovers if a step fails. Never delete a shared VNet with
other workloads. HTTP/Flask servers and unauthenticated CRUD are suitable only for
a restricted assessment demo; broader access requires authentication, TLS and
production serving configuration before exposure.
