# Group 5 Azure deployment preparation

Status: Azure/GitHub authentication preparation is complete. The existing resource
group `asd-group5-rg`, User-Assigned Managed Identity `asd-group5-github-oidc-mi`,
Contributor role assignment and federated identity credential are already configured.
No Azure VM, NSG, VNet, NIC, public IP or OS disk has been created yet. The application
has not been deployed, and Cloud Deployment Review must not be marked PASS.

## Architecture and subscription

GitHub Actions (manual dispatch, Azure OIDC) → Azure Linux VM (Ubuntu 24.04) →
Docker Compose frontend/backend/SQLite baseline. The existing resource group is
`asd-group5-rg`, subscription context **Azure for Students**.
The resource-group metadata location is `australiaeast`; it remains unchanged.
Deployable resources use **East Asia (`eastasia`)** due to the subscription's
Azure for Students region policy. The permitted deployment regions are
`koreacentral`, `centralindia`, `polandcentral`, `indonesiacentral` and `eastasia`.
The resource group's metadata location does not select the deployment region.
Confirm the selected subscription with `az account show` before executing scripts.
The scripts intentionally do not create or delete the shared resource group.

`docker-compose.cloud.yml` contains all five modules plus the shared frontend.
Student 1–4 use internal database APIs. Student 5 has a one-shot database seed
container and a backend that accesses the same named SQLite volume directly;
its database container is not an HTTP service. Five named volumes retain database
data across container recreation. They live on the VM OS disk, not external storage.
The optional bonus overlay adds Ollama, MCP, RAG and multi-agent services for
Students 3 and 5. The Student 5 frontend proxy and MCP container share the backend's
network namespace to reach its loopback-bound API without changing the
`127.0.0.1` binding or publishing port 8005. MCP does not declare exposed or published
ports in Compose or its image because Docker disallows exposed ports for a service
using another container's network namespace. It remains reachable on port 9001
through the Student 5 backend container's network address. The frontend is published
on port 8085; Student 3 reaches MCP using the Student 5 container's internal service address.

Frontend URLs use the VM hostname/IP and existing module ports:

| Module | Public port | Backend (VM loopback only) |
| --- | --- | --- |
| Shared home | 8888 | — |
| Courses | 8081 | 8001 |
| Assignments | 8082 | 8002 |
| Resources | 8083 | 8003 |
| Events | 8080 | 8000 |
| Career | 8085 | Container loopback only; not published |

Nginx proxies browser API requests using Compose DNS names, except the Student 5
proxy, which uses `127.0.0.1:8005` in its shared network namespace. Browser navigation
uses port metadata to build links on the current hostname and protocol. No database
or backend API ports are published. Loopback in health checks refers to the
container/VM itself; it is not a browser or container-to-container address. The cloud file contains no
`host.docker.internal` references. Unused legacy top-level Student Dockerfiles
are empty and are not selected by either Compose file.

## Local versus cloud and disabled AI

The local `docker-compose.yml` remains unchanged and retains Ollama and host
services. Local behavior defaults to AI enabled. The baseline cloud deployment sets
`AI_SERVICES_ENABLED=false` on every backend and clears all AI/MCP/RAG/Multi-Agent
URLs. The bonus workflow overlays that configuration, enables AI on Students 3 and 5,
and connects both backends to the shared bonus services. Other student modules remain
AI-disabled. Existing UI controls may remain visible and report the disabled response.
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
Manual SKU verification with `az vm list-skus` is complete for `eastasia`:
`Standard_B2s` is unavailable for this Azure for Students subscription
(`NotAvailableForSubscription`). `Standard_B2s_v2` returned `Restrictions: None`
and is the selected deployment default; it provides **2 vCPUs and 8 GiB RAM**.
This verification did not create a VM; VM creation has still **not occurred**.

Authenticate with Azure CLI and configure on a developer machine:

```sh
export RESOURCE_GROUP=asd-group5-rg
export LOCATION=eastasia
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
   The bonus workflow additionally packages the bonus Compose overlay, MCP, RAG
   and multi-agent sources.
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

Expected application resources the script would create in `eastasia`, inside the existing group:

- VM `asd-group5-vm`, Ubuntu 24.04, size `Standard_B2s_v2` (2 vCPUs, 8 GiB RAM).
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
The GitHub Environment `azure-assessment` already exists with the deployment
secrets and HTTP CIDR variable configured. The UTS tenant does not allow the student
account to create applications, so authentication uses the existing User-Assigned
Managed Identity rather than an application registration.

The real authentication path is:

GitHub Actions → GitHub OIDC token → User-Assigned Managed Identity
`asd-group5-github-oidc-mi` → Contributor scoped only to `asd-group5-rg` → Azure resources.

The managed identity is in `asd-group5-rg`, location `eastasia`. Its federated
credential is already configured as:

| Setting | Configured value |
| --- | --- |
| Name | `github-azure-assessment` |
| Issuer | `https://token.actions.githubusercontent.com` |
| Subject | `repo:startistsky/enrolment-app-open-ai:environment:azure-assessment` |
| Audience | `api://AzureADTokenExchange` |

`AZURE_CLIENT_ID` is the **client ID of this User-Assigned Managed Identity**.
No Azure client secret is used. `azure/login@v2` exchanges the workflow's GitHub
OIDC token for Azure access using that identity; `contents: read` and
`id-token: write` remain configured. The workflow explicitly supplies
`LOCATION: eastasia` and `RESOURCE_GROUP: asd-group5-rg` to deployment.
Environment approval/branch policies may be reviewed without changing the secrets.
See Microsoft's [Azure GitHub OIDC instructions](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect).

Already configured GitHub Environment secrets (values are not recorded here):

| Secret | Value |
| --- | --- |
| `AZURE_CLIENT_ID` | Client ID of User-Assigned Managed Identity `asd-group5-github-oidc-mi` |
| `AZURE_TENANT_ID` | Directory tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure for Students subscription ID |
| `AZURE_VM_SSH_PUBLIC_KEY` | Matching OpenSSH public key text |
| `AZURE_VM_SSH_PRIVATE_KEY` | Dedicated deployment private key, unencrypted |

Already configured GitHub Environment variable: `AZURE_HTTP_SOURCE_CIDR`, the source CIDR
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

`.github/workflows/azure-bonus-deployment.yml` is also manually dispatched and
deploys the same release with the bonus Compose overlay. Select a pushed branch
containing the bonus configuration and source. It builds the shared Ollama, MCP,
RAG and multi-agent services, indexes both Student 3 resource and Student 5 career
knowledge, and enables the AI integrations for Students 3 and 5. Its VM checks
verify the bonus containers are running and Student 5 can reach the configured
Ollama model. For local validation, use
`docker compose -f docker-compose.cloud.yml -f docker-compose.bonus.yml config`;
for local startup, append `up -d --build` to that command.

## Health and real assessment evidence

On the VM, run `sudo bash /opt/asd-group5/current/scripts/cloud/health-check.sh`. It checks all
frontend pages, backend health, database-backed reads and representative disabled
AI routes; for bonus releases it also verifies the MCP, RAG and multi-agent services
are running and Student 5's Ollama integration is available. It does not perform
write/delete operations or claim full CRUD success.
For diagnosis, use `sudo bash -c 'cd /opt/asd-group5/current && docker compose -p asd-group5-cloud -f docker-compose.cloud.yml ps -a'` and the corresponding `logs` command; add `-f docker-compose.bonus.yml` for bonus releases.
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
