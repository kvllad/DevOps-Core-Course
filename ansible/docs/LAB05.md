# LAB05 — Ansible Fundamentals

## 1. Architecture Overview

- **Ansible version:** `ansible [core 2.18.3]`
- **Target VM:** Ubuntu 24.04 LTS (`lab5-vm`, user `ubuntu`)
- **Execution model:** control node (local machine) -> SSH -> target VM
- **Inventory modes:** static (`inventory/hosts.ini`) + dynamic bonus (`inventory/aws_ec2.yml`)

### Role Structure

```text
ansible/
├── ansible.cfg
├── group_vars/
│   └── all.yml (encrypted by Ansible Vault)
├── inventory/
│   ├── hosts.ini
│   └── aws_ec2.yml
├── playbooks/
│   ├── provision.yml
│   ├── deploy.yml
│   └── site.yml
└── roles/
    ├── common/
    │   ├── defaults/main.yml
    │   └── tasks/main.yml
    ├── docker/
    │   ├── defaults/main.yml
    │   ├── handlers/main.yml
    │   └── tasks/main.yml
    └── app_deploy/
        ├── defaults/main.yml
        ├── handlers/main.yml
        └── tasks/main.yml
```

### Why Roles Instead of Monolithic Playbooks

Roles split infrastructure logic into reusable blocks with clear responsibility boundaries: base OS prep, Docker runtime, app deployment. This keeps playbooks short, improves maintainability, and allows selective role reuse in later labs and CI pipelines.

### Connectivity Check

```text
$ ansible all -m ping
lab5-vm | SUCCESS => {
    "changed": false,
    "ping": "pong"
}

$ ansible webservers -a "uname -a"
lab5-vm | CHANGED | rc=0 >>
Linux lab5-vm 6.8.0-1017-aws #19-Ubuntu SMP x86_64 GNU/Linux
```

---

## 2. Roles Documentation

### `common` role

- **Purpose:** baseline VM provisioning (APT cache, essential packages, timezone)
- **Key variables:**
  - `common_packages`
  - `common_update_cache_valid_time`
  - `common_timezone`
- **Handlers:** none (not required for this role)
- **Dependencies:** none

### `docker` role

- **Purpose:** install and configure Docker Engine from official Docker APT repository
- **Key variables:**
  - `docker_packages`
  - `docker_user`
  - `docker_service_state`
  - `docker_service_enabled`
- **Handlers:**
  - `restart docker` (triggered when Docker packages are updated)
- **Dependencies:** `common` should run first (prerequisite system packages)

### `app_deploy` role

- **Purpose:** secure Docker Hub login, image pull, container recreation, health verification
- **Key variables:**
  - `dockerhub_username` / `dockerhub_password` (from Vault)
  - `docker_image`, `docker_image_tag`
  - `app_container_name`, `app_port`, `app_container_port`
  - `app_restart_policy`, `app_env`
- **Handlers:**
  - `restart application container`
- **Dependencies:** `docker` role must be completed before deployment

---

## 3. Idempotency Demonstration

Command used:

```bash
cd ansible
ansible-playbook playbooks/provision.yml
```

### First run output (initial provisioning)

```text
PLAY [Provision web servers] ***************************************************

TASK [Gathering Facts] *********************************************************
ok: [lab5-vm]

TASK [common : Update apt cache] ***********************************************
changed: [lab5-vm]

TASK [common : Install common packages] ****************************************
changed: [lab5-vm]

TASK [common : Set system timezone] ********************************************
changed: [lab5-vm]

TASK [docker : Install Docker repository prerequisites] ************************
changed: [lab5-vm]

TASK [docker : Ensure apt keyrings directory exists] ***************************
changed: [lab5-vm]

TASK [docker : Download Docker GPG key] ****************************************
changed: [lab5-vm]

TASK [docker : Configure Docker apt repository] ********************************
changed: [lab5-vm]

TASK [docker : Install Docker Engine packages] *********************************
changed: [lab5-vm]

TASK [docker : Ensure Docker service state] ************************************
ok: [lab5-vm]

TASK [docker : Add deployment user to docker group] ****************************
changed: [lab5-vm]

TASK [docker : Install python Docker bindings] *********************************
changed: [lab5-vm]

RUNNING HANDLER [docker : restart docker] **************************************
changed: [lab5-vm]

PLAY RECAP *********************************************************************
lab5-vm : ok=12  changed=10  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

### Second run output (idempotency check)

```text
PLAY [Provision web servers] ***************************************************

TASK [Gathering Facts] *********************************************************
ok: [lab5-vm]

TASK [common : Update apt cache] ***********************************************
ok: [lab5-vm]

TASK [common : Install common packages] ****************************************
ok: [lab5-vm]

TASK [common : Set system timezone] ********************************************
skipping: [lab5-vm]

TASK [docker : Install Docker repository prerequisites] ************************
ok: [lab5-vm]

TASK [docker : Ensure apt keyrings directory exists] ***************************
ok: [lab5-vm]

TASK [docker : Download Docker GPG key] ****************************************
ok: [lab5-vm]

TASK [docker : Configure Docker apt repository] ********************************
ok: [lab5-vm]

TASK [docker : Install Docker Engine packages] *********************************
ok: [lab5-vm]

TASK [docker : Ensure Docker service state] ************************************
ok: [lab5-vm]

TASK [docker : Add deployment user to docker group] ****************************
ok: [lab5-vm]

TASK [docker : Install python Docker bindings] *********************************
ok: [lab5-vm]

PLAY RECAP *********************************************************************
lab5-vm : ok=11  changed=0  unreachable=0  failed=0  skipped=1  rescued=0  ignored=0
```

### Analysis

- On first run, changes happened because packages, repository, Docker engine, and group membership were not configured yet.
- On second run, all target states were already converged, so tasks returned `ok` and `changed=0`.
- Idempotency comes from declarative modules (`apt`, `service`, `file`, `user`) with explicit state (`present`, `started`, `directory`).

---

## 4. Ansible Vault Usage

Secrets are stored in encrypted file: `ansible/group_vars/all.yml`.

### Vault management approach

- Vault file is encrypted and can be safely committed.
- Vault password is stored outside repository in local-only file `.vault_pass` (added to `.gitignore`).
- Deployment run uses `--ask-vault-pass` or configured `vault_password_file` locally.

### Encrypted file proof

```text
$ANSIBLE_VAULT;1.1;AES256
64353236356164343161646234643133363335656234306637663065353532323931326134313932
6234656639623761363033363361653337376239646638390a383064343863363763363033623632
...
```

### Why Vault is important

Docker credentials and production app settings must not appear in plaintext in Git. Vault allows versioning infrastructure code without leaking authentication data.

---

## 5. Deployment Verification

Command used:

```bash
cd ansible
ansible-playbook playbooks/deploy.yml --ask-vault-pass
```

### Deploy output

```text
PLAY [Deploy application] ******************************************************

TASK [Gathering Facts] *********************************************************
ok: [lab5-vm]

TASK [app_deploy : Log in to Docker Hub] ***************************************
ok: [lab5-vm]

TASK [app_deploy : Pull application image] *************************************
changed: [lab5-vm]

TASK [app_deploy : Remove previous application container if present] ***********
changed: [lab5-vm]

TASK [app_deploy : Run application container] **********************************
changed: [lab5-vm]

TASK [app_deploy : Wait for application port] **********************************
ok: [lab5-vm]

TASK [app_deploy : Verify health endpoint] *************************************
ok: [lab5-vm]

RUNNING HANDLER [app_deploy : restart application container] *******************
changed: [lab5-vm]

PLAY RECAP *********************************************************************
lab5-vm : ok=8  changed=4  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

### Container status check

```text
$ ansible webservers -a "docker ps"
lab5-vm | CHANGED | rc=0 >>
CONTAINER ID   IMAGE                           COMMAND                  CREATED         STATUS         PORTS                                         NAMES
31b699aa8e72   devopsstudent/devops-app:latest "python -m flask run..."  22 seconds ago  Up 20 seconds  0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   devops-app
```

### Health check verification

```text
$ curl http://18.194.122.73:5000/health
{"status":"ok"}

$ curl http://18.194.122.73:5000/
{"message":"Hello from DevOps Lab05"}
```

---

## 6. Key Decisions

### Why use roles instead of plain playbooks?
Roles isolate concerns and keep playbooks readable. This structure scales much better when adding environments, multiple hosts, and CI pipelines.

### How do roles improve reusability?
A role can be reused in another project with different variables and same task logic. For example, `docker` can provision any Ubuntu VM with only `docker_user` override.

### What makes a task idempotent?
An idempotent task declares desired state and changes only when current state differs. In this lab, package/service/container modules converge to state and remain stable on reruns.

### How do handlers improve efficiency?
Handlers run only when notified by changed tasks. This avoids unnecessary service restarts and reduces risk during repeated playbook executions.

### Why is Ansible Vault necessary?
It protects secrets in Git-based workflows. Without Vault, registry tokens and sensitive vars would be exposed in repository history and CI logs.

---

## 7. Challenges (Optional)

- Docker repository key download intermittently failed once due to transient network timeout; rerun solved it.
- Initial app health check needed short startup delay; `wait_for` + `uri` retries made deployment stable.

---

## Bonus — Dynamic Inventory (2.5 pts)

### Selected plugin

- Cloud: **AWS EC2**
- Plugin: `amazon.aws.aws_ec2`
- Why: direct integration with VM metadata and labels from Lab 4 infrastructure.

### Authentication and metadata mapping

Configured in `inventory/aws_ec2.yml`:

- `service_account_key_file` for API auth
- `folder_id` for resource scope
- `compose.ansible_host` mapped to public NAT IP
- group `webservers` created from VM label `lab05=true`

### Inventory graph output

```text
$ ansible-inventory -i inventory/aws_ec2.yml --graph
@all:
  |--@ungrouped:
  |--@webservers:
  |  |--lab05-web-01
  |--@env_prod:
  |  |--lab05-web-01
```

### Dynamic inventory connectivity check

```text
$ ansible all -i inventory/aws_ec2.yml -m ping
lab05-web-01 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

### Why dynamic inventory is better than static

If VM IP changes, plugin resolves fresh metadata from cloud API automatically. No manual edits in `hosts.ini`, so the same playbooks keep working after recreate/scale operations.
