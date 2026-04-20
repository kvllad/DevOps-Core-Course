# Lab 13 — GitOps with ArgoCD

Execution date: 2026-04-20  
Cluster context: `kind-devops-labs`

## ArgoCD Setup

ArgoCD was installed via the official Helm chart into the `argocd` namespace. The setup includes:

- `argocd-server` for the web UI and API
- `argocd-repo-server` for Git and Helm rendering
- `argocd-application-controller` for reconciliation
- `argocd-applicationset-controller` for ApplicationSet generation
- `argocd-dex-server` and `argocd-redis`

UI access method:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

CLI login:

```bash
argocd login localhost:8080 --username admin --password '<initial-password>' --insecure
```

Installation verification:

```text
PENDING
```

## Application Configuration

Manifests:

- `k8s/argocd/application.yaml` — initial manual-sync application into namespace `lab13`
- `k8s/argocd/application-dev.yaml` — dev environment with auto-sync, prune, and self-heal
- `k8s/argocd/application-prod.yaml` — prod environment with manual sync
- `k8s/argocd/applicationset.yaml` — bonus ApplicationSet list generator for dev and prod

Source configuration:

- `repoURL`: `https://github.com/kvllad/DevOps-Core-Course.git`
- `targetRevision`: `lab13`
- `path`: `k8s/devops-python`

Environment value files:

- dev: `values-dev.yaml`
- prod: `values-prod.yaml`

## Multi-Environment

`dev` and `prod` deploy the same Helm chart with different values:

- dev uses lower resource requests/limits and auto-sync
- prod uses higher resource requests/limits and manual sync
- namespaces stay isolated, so resources and PVCs do not overlap

Why prod stays manual:

- change review happens before production rollout
- release timing stays controlled
- the operator can inspect the diff before syncing

## Self-Healing Evidence

Manual scale drift test:

```text
PENDING
```

Pod deletion test:

```text
PENDING
```

Configuration drift test:

```text
PENDING
```

Sync behavior summary:

- Kubernetes heals missing pods because the workload controller keeps the desired replica count.
- ArgoCD heals configuration drift when the live object no longer matches Git and `selfHeal` is enabled.
- ArgoCD polls Git on a roughly 3 minute interval by default, unless sync is triggered manually or via webhook.

## Screenshots

- ArgoCD applications overview: `PENDING`
- Application details view: `PENDING`
- ApplicationSet-generated apps: `PENDING`

## Bonus — ApplicationSet

The bonus implementation uses a List generator to produce dev and prod Applications from one template. The template varies:

- namespace
- Helm values file
- release name
- auto-sync policy

This pattern scales better than hand-writing one Application per environment when:

- the repo contains many similar environments
- naming and sync policy follow a fixed pattern
- you want one source of truth for the app definition

Individual Applications remain useful when:

- environments need materially different spec structure
- per-environment review and ownership are separate
- you do not want generator-driven updates
