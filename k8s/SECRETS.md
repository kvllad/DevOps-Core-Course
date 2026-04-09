# Lab 11 — Kubernetes Secrets & HashiCorp Vault

Execution date: 2026-04-09  
Cluster context: `kind-lab11`  
Namespaces: `lab11`, `vault`

## 1. Kubernetes Secrets Fundamentals

### Secret created via imperative `kubectl`

```bash
$ kubectl -n lab11 create secret generic app-credentials \
    --from-literal=username=lab11-user \
    --from-literal=password='Lab11-Pass-2026'
secret/app-credentials created
```

### Secret inspected in YAML

```bash
$ kubectl -n lab11 get secret app-credentials -o yaml
apiVersion: v1
data:
  password: TGFiMTEtUGFzcy0yMDI2
  username: bGFiMTEtdXNlcg==
kind: Secret
metadata:
  name: app-credentials
  namespace: lab11
type: Opaque
```

### Base64 values decoded

```bash
$ kubectl -n lab11 get secret app-credentials -o jsonpath='{.data.username}' | base64 --decode
lab11-user

$ kubectl -n lab11 get secret app-credentials -o jsonpath='{.data.password}' | base64 --decode
Lab11-Pass-2026
```

### Encoding vs encryption

- Base64 in Kubernetes Secret manifests is encoding for transport/storage format, not cryptographic protection.
- Anyone with API read access to the Secret can decode the value immediately.
- Real protection requires encryption at rest + strict RBAC + network and audit controls.

### Are K8s Secrets encrypted at rest by default?

- By default, Kubernetes stores Secret data in etcd without application-level encryption unless encryption at rest is explicitly configured on `kube-apiserver`.
- In this lab cluster, no `--encryption-provider-config` flag is present in API server manifest:

```bash
$ docker exec lab11-control-plane sh -c \
  "grep -n -- '--encryption-provider-config' /etc/kubernetes/manifests/kube-apiserver.yaml || true"
# (no output)
```

### What is etcd encryption and when to enable it?

- etcd encryption at rest uses an encryption provider config (for example AES-CBC or KMS provider) so Secrets are encrypted before persistence in etcd.
- Enable it in every non-trivial environment, especially shared clusters, cloud multi-tenant environments, and anything with compliance requirements.

## 2. Helm-Managed Secrets

### Chart structure with `secrets.yaml`

```bash
$ find k8s/devops-python/templates -maxdepth 2 -type f | sort
k8s/devops-python/templates/NOTES.txt
k8s/devops-python/templates/_helpers.tpl
k8s/devops-python/templates/deployment.yaml
k8s/devops-python/templates/hooks/post-install-job.yaml
k8s/devops-python/templates/hooks/pre-install-job.yaml
k8s/devops-python/templates/secrets.yaml
k8s/devops-python/templates/service.yaml
k8s/devops-python/templates/serviceaccount.yaml
```

### Secret template and values

- Added `k8s/devops-python/templates/secrets.yaml` (templated name/labels, `stringData` from values).
- Added `secrets.*` defaults in `k8s/devops-python/values.yaml` with placeholders only.

### Secrets consumed in deployment

- `envFrom.secretRef` is used in `k8s/devops-python/templates/deployment.yaml`.
- The Deployment references the templated Secret name helper.

### Deployment verification (without revealing values)

Installed chart:

```bash
$ helm upgrade --install devops-python k8s/devops-python -n lab11 \
  -f k8s/devops-python/values-dev.yaml \
  --set-string secrets.data.username=helm-user \
  --set-string secrets.data.password='Helm-Pass-2026' \
  --wait
```

Secret created by Helm:

```bash
$ kubectl get secret -n lab11 devops-python-app-credentials -o yaml
apiVersion: v1
data:
  password: SGVsbS1QYXNzLTIwMjY=
  username: aGVsbS11c2Vy
kind: Secret
...
```

Environment variables exist in the pod (names only):

```bash
$ kubectl exec -n lab11 <pod> -c devops-python -- \
  sh -c 'printenv | cut -d= -f1 | sort | grep -E "^(APP_ENV|LOG_LEVEL|DEPLOYMENT_TRACK|username|password)$"'
APP_ENV
DEPLOYMENT_TRACK
LOG_LEVEL
password
username
```

`kubectl describe pod` does not expose secret values:

```bash
Environment Variables from:
  devops-python-app-credentials  Secret  Optional: false
Environment:
  PORT:              5000
  APP_ENV:           dev
  LOG_LEVEL:         debug
  DEPLOYMENT_TRACK:  dev
```

## 3. Resource Management

### Configured requests/limits

`values-dev.yaml`:

```yaml
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 100m
    memory: 128Mi
```

Applied in cluster:

```bash
$ kubectl get deploy -n lab11 devops-python \
  -o jsonpath='{.spec.template.spec.containers[0].resources}'
{"limits":{"cpu":"100m","memory":"128Mi"},"requests":{"cpu":"50m","memory":"64Mi"}}
```

### Requests vs limits

- `requests`: scheduler guarantee used for placement and baseline QoS.
- `limits`: hard cap enforced by cgroups.
- CPU throttles at limit; memory can trigger OOM kill when limit is exceeded.

### Choosing values

- Start from observed baseline (`kubectl top`, request latency, restart behavior).
- Set requests near steady-state usage.
- Set limits to allow burst headroom without risking node stability.
- Keep environment-specific overrides (`values-dev.yaml`, `values-prod.yaml`).

## 4. HashiCorp Vault Integration

### Vault installation verification

```bash
$ helm repo add hashicorp https://helm.releases.hashicorp.com
$ helm repo update
$ helm upgrade --install vault hashicorp/vault -n vault \
  --create-namespace \
  --set server.dev.enabled=true \
  --set injector.enabled=true \
  --wait
```

```bash
$ kubectl get pods -n vault
NAME                                   READY   STATUS    RESTARTS   AGE
vault-0                                1/1     Running   0          31s
vault-agent-injector-8c76487db-c7s25   1/1     Running   0          31s
```

### Vault configuration (KV, policy, role)

Kubernetes auth enabled/configured:

```bash
$ kubectl exec -n vault vault-0 -- sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; \
   vault auth enable kubernetes || true; \
   vault write auth/kubernetes/config \
     token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
     kubernetes_host="https://kubernetes.default.svc:443" \
     kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
```

Secret stored:

```bash
$ kubectl exec -n vault vault-0 -- sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; \
   vault kv put secret/myapp/config username="vault-user" password="Vault-Pass-2026" api_key="vault-api-key-2026"'
```

Policy (sanitized):

```bash
$ kubectl exec -n vault vault-0 -- sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; \
   vault policy read devops-python-policy'
path "secret/data/myapp/config" {
  capabilities = ["read"]
}
```

Role bound to app service account:

```bash
$ kubectl exec -n vault vault-0 -- sh -c \
  'export VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root; \
   vault read auth/kubernetes/role/devops-python-role'
bound_service_account_names       [devops-python]
bound_service_account_namespaces  [lab11]
policies                          [devops-python-policy]
ttl                               24h
```

### Vault Agent injection proof

Deployment upgraded with Vault annotations:

```bash
$ helm upgrade devops-python k8s/devops-python -n lab11 \
  -f k8s/devops-python/values-dev.yaml \
  --set vault.enabled=true \
  --set vault.role=devops-python-role \
  --set vault.secretPath=secret/data/myapp/config \
  --wait
```

Injected containers:

```bash
$ kubectl get pod -n lab11 <pod> -o jsonpath='{.spec.initContainers[*].name}{"\n"}{.spec.containers[*].name}{"\n"}'
vault-agent-init
devops-python vault-agent
```

Injected file exists at expected path:

```bash
$ kubectl exec -n lab11 <pod> -c devops-python -- ls -l /vault/secrets/config
-r--r----- 1 100 1000 84 Apr  9 19:15 /vault/secrets/config
```

Rendered file content (redacted):

```bash
$ kubectl exec -n lab11 <pod> -c devops-python -- sh -c 'cat /vault/secrets/config' | sed -E 's/=.*/=<redacted>/'
APP_USERNAME=<redacted>
APP_PASSWORD=<redacted>
APP_API_KEY=<redacted>
```

### Sidecar injection pattern explained

- Mutating webhook (Vault injector) adds:
  - `vault-agent-init` init container for initial auth/template setup.
  - `vault-agent` sidecar for token lifecycle and template rendering.
  - Shared in-memory volume mounted at `/vault/secrets`.
- Application reads rendered files locally and does not need embedded Vault client code.

## 5. Security Analysis

### Kubernetes Secrets vs Vault

- Kubernetes Secrets:
  - Native, simple, low operational overhead.
  - Good for basic cluster-local secret distribution.
  - Security depends heavily on RBAC + encryption at rest config.
- Vault:
  - Centralized secret system with policies, auth methods, audit, dynamic secrets, and rotation workflows.
  - Better fit for production and compliance-heavy environments.
  - Operationally more complex (HA, storage backend, unseal, backup, upgrades).

### When to use which

- Use Kubernetes Secrets for simple local/dev use cases and low-risk credentials.
- Use Vault when you need centralized governance, strong auditability, dynamic credentials, and controlled secret distribution across apps/clusters.

### Production recommendations

- Always enable Kubernetes encryption at rest for Secrets.
- Apply least-privilege RBAC (`get/list/watch` only where required).
- Avoid long-lived static credentials; rotate frequently.
- Use Vault (or cloud secret managers) for sensitive production credentials.
- Keep secrets out of Git; commit placeholders only.

## Bonus — Vault Agent Templates

### 1. Template annotation implemented

Implemented in `k8s/devops-python/templates/deployment.yaml`:

```yaml
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: "devops-python-role"
vault.hashicorp.com/agent-inject-secret-config: "secret/data/myapp/config"
vault.hashicorp.com/agent-inject-template-config: |
  {{- with secret "secret/data/myapp/config" -}}
  APP_USERNAME={{ .Data.data.username }}
  APP_PASSWORD={{ .Data.data.password }}
  APP_API_KEY={{ .Data.data.api_key }}
  {{- end }}
vault.hashicorp.com/agent-inject-command-config: "chmod 0440 /vault/secrets/config"
```

- Multiple secrets are rendered into one `.env`-style file (`/vault/secrets/config`).

### 2. Dynamic secret rotation research

- Vault Agent continuously manages auth token lifecycle in the sidecar.
- For leased/dynamic secrets, templates are re-rendered when the secret/token is renewed or changed.
- For static KV values, refresh is interval-based (injector annotation: `vault.hashicorp.com/template-static-secret-render-interval`, example: `"2m"`).
- `vault.hashicorp.com/agent-inject-command-*` runs after template rendering, useful for app reload hooks (for example sending `SIGHUP`, running `kill -HUP`, or file permission hardening).

### 3. Named template in `_helpers.tpl` (DRY)

Implemented `k8s/devops-python/templates/_helpers.tpl`:

```yaml
{{- define "devops-python.envVars" -}}
- name: PORT
  value: {{ .Values.containerPort | quote }}
- name: APP_ENV
  value: {{ .Values.app.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.app.logLevel | quote }}
{{- range $name, $value := .Values.env }}
- name: {{ $name }}
  value: {{ $value | quote }}
{{- end }}
{{- end -}}
```

Used from deployment:

```yaml
env:
  {{- include "devops-python.envVars" . | nindent 12 }}
```

Benefits:
- avoids duplicated env variable blocks across templates.
- keeps environment schema centralized in values.
- reduces drift and review overhead.

## Official references

- Kubernetes Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- Kubernetes encryption at rest: https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/
- Vault Helm on Kubernetes: https://developer.hashicorp.com/vault/docs/platform/k8s/helm
- Vault injector annotations/examples: https://developer.hashicorp.com/vault/docs/platform/k8s/injector/examples
