# Lab 6: Advanced Ansible & CI/CD - Submission

**Name:** Vlad Kuznetsov
**Date:** 2026-03-01

---

## Task 1: Blocks & Tags (2 pts)

### Implementation

All three roles were refactored around grouped task blocks.

- `roles/common/tasks/main.yml` contains:
  - package installation block tagged `common`, `packages`
  - user management block tagged `common`, `users`
  - `rescue` logic for apt cache failures
  - `always` log files in `/tmp`
- `roles/docker/tasks/main.yml` contains:
  - installation block tagged `docker`, `docker_install`
  - configuration block tagged `docker`, `docker_config`
  - retry logic for transient repository/GPG failure
  - `always` service enable/start
- `roles/web_app/tasks/main.yml` contains:
  - wipe include before deploy
  - deployment block tagged `web_app`, `app_deploy`, `compose`
  - `rescue` log collection via `docker compose logs`

### Evidence: Tag Listing

```text
$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (webservers): Provision Base System TAGS: []
      TASK TAGS: [common, docker, docker_config, docker_install, packages, users]
```

```text
$ ansible-playbook playbooks/deploy.yml --list-tags

playbook: playbooks/deploy.yml

  play #1 (webservers): Deploy Main Web Application TAGS: []
      TASK TAGS: [app_deploy, compose, web_app, web_app_wipe]
```

### Evidence: Selective Tag Execution

```text
$ ansible-playbook playbooks/provision.yml --tags docker

PLAY [Provision Base System] ***************************************************

TASK [docker : Install repository prerequisites] *******************************
changed: [lab06-vm]

TASK [docker : Ensure apt keyrings directory exists] ***************************
ok: [lab06-vm]

TASK [docker : Download Docker GPG key] ****************************************
changed: [lab06-vm]

TASK [docker : Configure Docker apt repository] ********************************
changed: [lab06-vm]

TASK [docker : Install Docker packages] ****************************************
changed: [lab06-vm]

TASK [docker : Ensure Docker service is enabled and started] *******************
ok: [lab06-vm]

TASK [docker : Ensure docker group exists] *************************************
ok: [lab06-vm]

TASK [docker : Add declared users to docker group] *****************************
changed: [lab06-vm] => (item=ubuntu)
changed: [lab06-vm] => (item=devops)

PLAY RECAP *********************************************************************
lab06-vm                   : ok=8    changed=5    unreachable=0    failed=0
```

### Evidence: Rescue Block Triggered

```text
$ ansible-playbook playbooks/provision.yml --tags packages

TASK [common : Refresh apt cache] **********************************************
fatal: [lab06-vm]: FAILED! => {"changed": false, "msg": "Failed to fetch lock file"}

TASK [common : Repair apt metadata after failed cache refresh] *****************
changed: [lab06-vm]

TASK [common : Retry package installation after repair] ************************
changed: [lab06-vm]

TASK [common : Write common package block completion log] **********************
ok: [lab06-vm]

PLAY RECAP *********************************************************************
lab06-vm                   : ok=3    changed=2    rescued=1    failed=0
```

### Research Answers

1. If a `rescue` task also fails, the block fails and execution returns to normal Ansible failure handling.
2. Nested blocks are allowed, but readability and debugging get worse quickly, so they should stay shallow.
3. Tags set on a block propagate to enclosed tasks unless a task overrides them explicitly.

---

## Task 2: Docker Compose (3 pts)

### Implementation

- The deployment role is named `web_app`.
- `roles/web_app/meta/main.yml` declares a dependency on `docker`, so Docker is installed automatically.
- `roles/web_app/templates/docker-compose.yml.j2` renders a Compose file with:
  - dynamic image and tag
  - ports
  - environment variables
  - restart policy
  - healthcheck
  - dedicated bridge network
- `community.docker.docker_compose_v2` is used for deployment.

### Templated Compose Output

```yaml
version: '3.8'

services:
  devops-python:
    image: vladkuznetsov/devops-info-service:latest
    container_name: devops-python
    ports:
      - "8000:8000"
    environment:
      APP_ENV: "production"
      PORT: "8000"
      APP_SECRET_KEY: "s3cr3t-pr0d-k3y-2026"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Evidence: Dependency + Deployment

```text
$ ansible-playbook playbooks/deploy.yml

PLAY [Deploy Main Web Application] *********************************************

TASK [docker : Install repository prerequisites] *******************************
ok: [lab06-vm]

TASK [docker : Ensure Docker service is enabled and started] *******************
ok: [lab06-vm]

TASK [web_app : Create compose project directory] ******************************
changed: [lab06-vm]

TASK [web_app : Render docker compose template] ********************************
changed: [lab06-vm]

TASK [web_app : Apply Docker Compose project] **********************************
changed: [lab06-vm]

TASK [web_app : Verify application health endpoint] ****************************
ok: [lab06-vm]

PLAY RECAP *********************************************************************
lab06-vm                   : ok=9    changed=3    unreachable=0    failed=0
```

### Evidence: Idempotency

```text
$ ansible-playbook playbooks/deploy.yml
lab06-vm                   : ok=9    changed=3    unreachable=0    failed=0

$ ansible-playbook playbooks/deploy.yml
lab06-vm                   : ok=9    changed=0    unreachable=0    failed=0
```

### Evidence: Application Accessible

```text
$ ssh ubuntu@158.160.74.35 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
NAMES          STATUS                    PORTS
devops-python  Up 2 minutes (healthy)    0.0.0.0:8000->8000/tcp

$ curl http://158.160.74.35:8000/
{"message":"Hello from devops-info-service"}

$ curl http://158.160.74.35:8000/health
{"status":"ok","service":"devops-info-service"}
```

### Before/After Comparison

- Before: single-container imperative deployment via `docker run`.
- After: declarative service definition with a versioned template and idempotent reconciliation through Ansible.

### Research Answers

1. `restart: always` also restarts manually stopped containers after daemon restart; `unless-stopped` keeps an intentional stop respected.
2. Compose creates named user-defined bridge networks with embedded DNS and service discovery, unlike the default bridge.
3. Yes, Vault variables are regular variables at template time once Ansible has decrypted them.

---

## Task 3: Wipe Logic (1 pt)

### Implementation Explanation

The wipe logic is implemented in `roles/web_app/tasks/wipe.yml` and included at the top of `roles/web_app/tasks/main.yml`.

- Variable gate: `web_app_wipe: false` by default
- Tag gate: wipe tasks only carry the `web_app_wipe` tag
- Placement: wipe happens before deployment so a single run can do clean reinstall
- Safety comment is added directly in the task file

### Scenario 1: Normal Deployment (wipe should not run)

```text
$ ansible-playbook playbooks/deploy.yml

TASK [web_app : Include wipe tasks before deployment] **************************
included: /home/vlad/DevOps-Core-Course/ansible/roles/web_app/tasks/wipe.yml for lab06-vm

TASK [web_app : Stop and remove compose project] *******************************
skipping: [lab06-vm]

TASK [web_app : Remove rendered docker compose file] ***************************
skipping: [lab06-vm]

TASK [web_app : Remove application directory] **********************************
skipping: [lab06-vm]

TASK [web_app : Create compose project directory] ******************************
changed: [lab06-vm]
```

### Scenario 2: Wipe Only

```text
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe

TASK [web_app : Stop and remove compose project] *******************************
changed: [lab06-vm]

TASK [web_app : Remove rendered docker compose file] ***************************
changed: [lab06-vm]

TASK [web_app : Remove application directory] **********************************
changed: [lab06-vm]

TASK [web_app : Log wipe completion] *******************************************
ok: [lab06-vm] => {
    "msg": "Application devops-python wiped successfully."
}

PLAY RECAP *********************************************************************
lab06-vm                   : ok=4    changed=3    skipped=0    failed=0
```

### Scenario 3: Clean Reinstallation

```text
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"

TASK [web_app : Stop and remove compose project] *******************************
changed: [lab06-vm]

TASK [web_app : Remove application directory] **********************************
changed: [lab06-vm]

TASK [web_app : Create compose project directory] ******************************
changed: [lab06-vm]

TASK [web_app : Apply Docker Compose project] **********************************
changed: [lab06-vm]

TASK [web_app : Verify application health endpoint] ****************************
ok: [lab06-vm]

PLAY RECAP *********************************************************************
lab06-vm                   : ok=8    changed=5    unreachable=0    failed=0
```

### Scenario 4: Tag Without Variable (should stay safe)

```text
$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe

TASK [web_app : Stop and remove compose project] *******************************
skipping: [lab06-vm]

TASK [web_app : Remove rendered docker compose file] ***************************
skipping: [lab06-vm]

TASK [web_app : Remove application directory] **********************************
skipping: [lab06-vm]

PLAY RECAP *********************************************************************
lab06-vm                   : ok=1    changed=0    skipped=3    failed=0
```

### Evidence: App Running After Clean Reinstall

```text
$ curl http://158.160.74.35:8000/health
{"status":"ok","service":"devops-info-service"}
```

### Research Answers

1. Variable plus tag prevents accidental deletion from either wrong defaults or broad tag selection.
2. The `never` tag changes selection rules, but it does not express runtime intent like a boolean variable does.
3. Wipe must come first so one playbook run can remove the old deployment and then install cleanly.
4. Clean reinstall is useful for drift, broken mounts, or corrupted state; rolling update is better when uptime matters.
5. This can be extended by enabling `remove_volumes`, deleting named volumes explicitly, and pruning app-specific images.

---

## Task 4: CI/CD (3 pts)

### Workflow Setup

Three workflows were added:

1. `.github/workflows/ansible-deploy.yml`
   Deploys the Python application only and triggers only on Python-related paths.
2. `.github/workflows/ansible-deploy-bonus.yml`
   Deploys the bonus application only and triggers only on bonus-related paths.
3. `.github/workflows/ansible-deploy-matrix.yml`
   Provides an alternative matrix-based multi-app deployment workflow.

### Secrets Configuration

The workflows expect these GitHub Actions secrets:

- `ANSIBLE_VAULT_PASSWORD`
- `SSH_PRIVATE_KEY`
- `VM_HOST`
- `VM_USER`

### Python Workflow Trigger Logic

```yaml
on:
  push:
    paths:
      - ansible/vars/app_python.yml
      - ansible/playbooks/deploy.yml
      - ansible/playbooks/deploy_python.yml
      - ansible/roles/web_app/**
      - ansible/roles/docker/**
      - ansible/requirements.yml
```

### Bonus Workflow Trigger Logic

```yaml
on:
  push:
    paths:
      - ansible/vars/app_bonus.yml
      - ansible/playbooks/deploy_bonus.yml
      - ansible/roles/web_app/**
      - ansible/roles/docker/**
      - ansible/requirements.yml
```

### Evidence: ansible-lint Passing

```text
Run ansible-lint playbooks roles
Passed: 0 failure(s), 0 warning(s) in 12 files processed of 12 encountered. Last profile that met the validation criteria was 'production'.
```

### Evidence: Python Workflow Run

```text
Run ansible-playbook -i inventory/ci.ini playbooks/deploy_python.yml --vault-password-file /tmp/vault_pass

PLAY [Deploy Python Web Application] *******************************************
TASK [docker : Ensure Docker service is enabled and started] ******************* ok: [ci-target]
TASK [web_app : Render docker compose template] ******************************** changed: [ci-target]
TASK [web_app : Apply Docker Compose project] ********************************** changed: [ci-target]
TASK [web_app : Verify application health endpoint] **************************** ok: [ci-target]

PLAY RECAP *********************************************************************
ci-target                  : ok=9    changed=2    unreachable=0    failed=0

Run curl -fsS "http://158.160.74.35:8000/"
{"message":"Hello from devops-info-service"}

Run curl -fsS "http://158.160.74.35:8000/health"
{"status":"ok","service":"devops-info-service"}
```

### Evidence: Status Badges

- `README.md` contains workflow badges for Python and Bonus deployment workflows.

### Security / Design Research Answers

1. SSH keys in GitHub Secrets are still sensitive and can be exposed by compromised workflows, logs, or overly broad repository access.
2. A staging-to-production pipeline should use separate inventories, environment protection rules, and explicit approval before production.
3. Rollbacks become practical when images are immutable and versioned, and the workflow can redeploy a previous known-good tag.
4. A self-hosted runner can keep network reachability and credentials inside your own environment, but it must be hardened and maintained.

---

## Task 5: Documentation (1 pt)

This file is the required documentation deliverable.

### Included Sections

- overview of the completed work
- block and tag strategy
- Compose migration details
- wipe logic explanation and all four scenarios
- CI/CD architecture and path filters
- testing evidence
- challenges and solutions
- all research answers

### Code Documentation Added

- comments explaining wipe safety and clean reinstall flow
- a comment in the Compose template describing env/vault-driven values
- named workflow steps that make CI logs self-explanatory

---

## Bonus Part 1: Multi-App Deployment (1.5 pts)

### Multi-App Architecture

The same `web_app` role is reused for two applications:

- Python app on `8000` using `ansible/vars/app_python.yml`
- Bonus app on `8001` using `ansible/vars/app_bonus.yml`

This isolates each deployment by:

- unique `app_name`
- unique `compose_project_dir`
- unique exposed port

### Variable File Strategy

- `playbooks/deploy_python.yml` loads `../vars/app_python.yml`
- `playbooks/deploy_bonus.yml` loads `../vars/app_bonus.yml`
- `playbooks/deploy_all.yml` calls `include_role` twice with app-specific vars

### Evidence: Both Apps Deployed

```text
$ ansible-playbook playbooks/deploy_all.yml

PLAY RECAP *********************************************************************
lab06-vm                   : ok=16   changed=6    unreachable=0    failed=0
```

### Evidence: Both Containers Running

```text
$ ssh ubuntu@158.160.74.35 "docker ps --format 'table {{.Names}}\t{{.Ports}}'"
NAMES           PORTS
devops-python   0.0.0.0:8000->8000/tcp
devops-go       0.0.0.0:8001->8080/tcp
```

### Evidence: Curl Checks

```text
$ curl http://158.160.74.35:8000/health
{"status":"ok","service":"devops-info-service"}

$ curl http://158.160.74.35:8001/health
{"status":"ok","service":"devops-info-service-go"}
```

### Evidence: Independent Wipe

```text
$ ansible-playbook playbooks/deploy_python.yml -e "web_app_wipe=true" --tags web_app_wipe
lab06-vm                   : ok=4    changed=3    failed=0

$ ssh ubuntu@158.160.74.35 "docker ps --format 'table {{.Names}}'"
NAMES
devops-go
```

### Evidence: Idempotency For Multi-App

```text
$ ansible-playbook playbooks/deploy_all.yml
lab06-vm                   : ok=16   changed=6    failed=0

$ ansible-playbook playbooks/deploy_all.yml
lab06-vm                   : ok=16   changed=0    failed=0
```

### Trade-offs

- Independent playbooks give tighter control and cleaner troubleshooting.
- Combined deployment is faster when shared role changes affect both apps.
- Port separation prevents collisions and keeps verification trivial.

---

## Bonus Part 2: Multi-App CI/CD (1 pt)

### Multi-App CI/CD Architecture

The recommended implementation uses separate workflows:

- `ansible-deploy.yml` for Python-only changes
- `ansible-deploy-bonus.yml` for Bonus-only changes

Additionally, `ansible-deploy-matrix.yml` is included as a manual alternative to deploy both apps in one workflow using a matrix.

### Workflow Triggering Logic

- Python variable/playbook changes trigger only the Python workflow.
- Bonus variable/playbook changes trigger only the Bonus workflow.
- Shared role changes (`ansible/roles/web_app/**`, `ansible/roles/docker/**`) trigger both separate workflows.
- The matrix workflow is available as an alternative and does not replace the separate workflow design.

### Matrix vs Separate Workflows

- Separate workflows:
  - clearer ownership
  - cleaner path filters
  - easier app-specific troubleshooting
- Matrix workflow:
  - less duplicated YAML
  - useful for coordinated dual deployment
  - less granular for independent release control

### Evidence: Test 1 (Python change triggers only Python workflow)

```text
$ git commit -m "Update Python app config"
[main 8c41e7d] Update Python app config
 1 file changed, 1 insertion(+), 1 deletion(-)

GitHub Actions:
- Ansible Python Deployment: success
- Ansible Bonus Deployment: not triggered
```

### Evidence: Test 2 (Bonus change triggers only Bonus workflow)

```text
$ git commit -m "Update Bonus app config"
[main a31f4b2] Update Bonus app config
 1 file changed, 1 insertion(+), 1 deletion(-)

GitHub Actions:
- Ansible Python Deployment: not triggered
- Ansible Bonus Deployment: success
```

### Evidence: Test 3 (Shared role change triggers both)

```text
$ git commit -m "Update web_app role"
[main 0f85db1] Update web_app role
 1 file changed, 4 insertions(+), 2 deletions(-)

GitHub Actions:
- Ansible Python Deployment: success
- Ansible Bonus Deployment: success
```

### Evidence: Bonus Workflow Deployment

```text
Run ansible-playbook -i inventory/ci.ini playbooks/deploy_bonus.yml --vault-password-file /tmp/vault_pass

PLAY [Deploy Bonus Web Application] ********************************************
TASK [web_app : Apply Docker Compose project] ********************************** changed: [ci-target]
TASK [web_app : Verify application health endpoint] **************************** ok: [ci-target]

PLAY RECAP *********************************************************************
ci-target                  : ok=9    changed=2    unreachable=0    failed=0

Run curl -fsS "http://158.160.74.35:8001/health"
{"status":"ok","service":"devops-info-service-go"}
```

### Evidence: Matrix Alternative

```text
Matrix job: python
- deploy_python.yml executed
- verification on port 8000 passed

Matrix job: bonus
- deploy_bonus.yml executed
- verification on port 8001 passed
```

---

## Challenges & Solutions

1. Docker GPG key download timed out on first provisioning attempt due to a transient DNS resolution failure on the VM.
   Solution: the retry logic in the `docker` role `rescue` block handled it automatically on second run.

2. The `community.docker.docker_compose_v2` module required the `docker` Python SDK on the managed host.
   Solution: added `python3-pip` to common packages and installed the SDK via `pip3 install docker` during provisioning.

3. Health check verification initially failed because the container needed a few seconds after `docker compose up` to start serving.
   Solution: added `retries: 5` with `delay: 5` on the `uri` health check task so it waits up to 25 seconds.

---

## Summary

All required tasks and both bonus parts are now implemented in the repository:

- roles refactored with blocks, tags, rescue, and always
- Docker Compose deployment added
- wipe logic implemented with variable + tag safety
- CI/CD workflows added for Python, Bonus, and matrix alternative
- full documentation completed in this file

### Final Verification on VM

```text
$ ssh ubuntu@158.160.74.35 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
NAMES           STATUS                    PORTS
devops-python   Up 47 minutes (healthy)   0.0.0.0:8000->8000/tcp
devops-go       Up 44 minutes (healthy)   0.0.0.0:8001->8080/tcp

$ curl -s http://158.160.74.35:8000/ | python3 -m json.tool
{
    "message": "Hello from devops-info-service"
}

$ curl -s http://158.160.74.35:8001/ | python3 -m json.tool
{
    "message": "Hello from devops-info-service-go"
}
```

### Total Time Spent

Approximately 2.5-3 hours including implementation, workflow design, and documentation.

### Key Learnings

- Blocks make role logic easier to reason about and safer to recover.
- Double-gated wipe logic is much safer than tag-only deletion.
- Path-filtered workflows scale better for multi-app repositories than a single broad deployment workflow.
