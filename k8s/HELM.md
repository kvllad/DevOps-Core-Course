# Lab 10 — Helm Package Manager

## Chart Overview

Helm value proposition in one sentence: it turns static Kubernetes YAML into reusable, versioned, configurable application packages with install, upgrade, rollback, and dependency management built in.

Helm fundamentals evidence:

```bash
$ helm version
version.BuildInfo{Version:"v4.1.3", GitCommit:"c94d381b03be117e7e57908edbf642104e00eb8f", GitTreeState:"clean", GoVersion:"go1.26.1", KubeClientVersion:"v1.35"}
```

```bash
$ helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
$ helm repo update
$ helm search repo prometheus-community/prometheus --versions | head -5
NAME                                     CHART VERSION APP VERSION DESCRIPTION
prometheus-community/prometheus          28.14.1       v3.10.0    Prometheus is a monitoring system and time seri...
prometheus-community/prometheus          28.14.0       v3.10.0    Prometheus is a monitoring system and time seri...
prometheus-community/prometheus          28.13.0       v3.10.0    Prometheus is a monitoring system and time seri...
prometheus-community/prometheus          28.12.0       v3.10.0    Prometheus is a monitoring system and time seri...
```

```bash
$ helm show chart prometheus-community/prometheus | sed -n '1,25p'
apiVersion: v2
appVersion: v3.10.0
dependencies:
- condition: alertmanager.enabled
  name: alertmanager
  repository: https://prometheus-community.github.io/helm-charts
  version: 1.34.*
- condition: kube-state-metrics.enabled
  name: kube-state-metrics
  repository: https://prometheus-community.github.io/helm-charts
  version: 7.2.*
description: Prometheus is a monitoring system and time series database.
home: https://prometheus.io/
keywords:
- monitoring
- prometheus
name: prometheus
type: application
version: 28.14.1
```

Implemented chart structure:

```text
k8s/
├── common-lib/
│   ├── Chart.yaml
│   └── templates/_helpers.tpl
├── devops-go/
│   ├── Chart.yaml
│   ├── Chart.lock
│   ├── charts/common-lib-0.1.0.tgz
│   ├── templates/
│   │   ├── NOTES.txt
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── values.yaml
└── devops-python/
    ├── Chart.yaml
    ├── Chart.lock
    ├── charts/common-lib-0.1.0.tgz
    ├── templates/
    │   ├── NOTES.txt
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   └── hooks/
    │       ├── post-install-job.yaml
    │       └── pre-install-job.yaml
    ├── values.yaml
    ├── values-dev.yaml
    └── values-prod.yaml
```

Key template files:
- `common-lib/templates/_helpers.tpl`: shared naming and label helpers for both application charts.
- `devops-python/templates/deployment.yaml`: templated Python deployment with probes, resources, env vars, and security context.
- `devops-python/templates/service.yaml`: templated Service with configurable type/port/nodePort.
- `devops-python/templates/hooks/*.yaml`: lifecycle jobs for pre-install validation and post-install smoke test.
- `devops-go/templates/*.yaml`: second application chart for the bonus task using the same library helpers.

Values organization strategy:
- `values.yaml` holds sane defaults and full schema for each chart.
- `values-dev.yaml` overrides for lightweight local development.
- `values-prod.yaml` overrides for higher replica count, stronger resources, and `LoadBalancer`-ready service config.
- Shared helper logic is not duplicated in app charts and lives in `common-lib`.

## Configuration Guide

Important values in `k8s/devops-python/values.yaml`:
- `replicaCount`: desired number of pods.
- `image.repository` / `image.tag` / `image.pullPolicy`: container image source.
- `service.type`, `service.port`, `service.targetPort`, `service.nodePort`: service exposure settings.
- `resources.requests` / `resources.limits`: CPU and memory guarantees/caps.
- `podSecurityContext` and `containerSecurityContext`: non-root execution and capability dropping.
- `probes.startup`, `probes.liveness`, `probes.readiness`: health checks, kept enabled and configurable.
- `hooks.*`: pre/post install job toggles, image, weights, and cleanup policy.

Environment-specific overrides:

`values-dev.yaml`
- `replicaCount: 1`
- `service.type: NodePort`
- `service.nodePort: 31080`
- relaxed resources
- `DEPLOYMENT_TRACK=dev`

`values-prod.yaml`
- `replicaCount: 3`
- `service.type: LoadBalancer`
- stronger CPU/memory settings
- more conservative probe timings
- `DEPLOYMENT_TRACK=prod`

Example install and upgrade commands:

```bash
# Development install
helm install devops-python k8s/devops-python -n lab10 --create-namespace -f k8s/devops-python/values-dev.yaml --wait

# Production upgrade
helm upgrade devops-python k8s/devops-python -n lab10 -f k8s/devops-python/values-prod.yaml --wait

# Second application for bonus
helm install devops-go k8s/devops-go -n lab10 --wait
```

## Hook Implementation

Implemented hooks in `devops-python` chart:
- `pre-install` hook: validation job using `busybox:1.36`
- `post-install` hook: in-cluster smoke test against `http://devops-python:80/health`

Execution order and weights:
- pre-install weight: `-5`
- post-install weight: `5`
- lower weight executes first, so validation runs before regular resources and smoke test runs after install

Deletion policy:
- `before-hook-creation,hook-succeeded`
- this removes stale hook resources before the next run and cleans them up automatically after successful completion

Observed pre-install hook while running:

```bash
$ kubectl get jobs -n lab10
NAME                        STATUS    COMPLETIONS   DURATION   AGE
devops-python-pre-install   Running   0/1           6s         6s
```

```bash
$ kubectl describe job -n lab10 devops-python-pre-install
Name:             devops-python-pre-install
Namespace:        lab10
Annotations:      helm.sh/hook: pre-install
                  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
                  helm.sh/hook-weight: -5
Pods Statuses:    1 Active / 0 Succeeded / 0 Failed
Container:        pre-install-validation
Image:            busybox:1.36
Environment:
  RELEASE_NAME=devops-python
  RELEASE_NAMESPACE=lab10
  REPLICA_COUNT=1
```

```bash
$ kubectl logs -n lab10 job/devops-python-pre-install
Validating release devops-python in namespace lab10
replicas=1 image=vladk6813050/devops-info-service-py:lab02 serviceType=NodePort
```

Evidence that both hooks executed:

```bash
$ kubectl get events -n lab10 --sort-by=.lastTimestamp | grep 'post-install\|pre-install\|Completed\|SuccessfulCreate'
Normal  SuccessfulCreate  job/devops-python-pre-install  Created pod: devops-python-pre-install-2mnzn
Normal  Completed         job/devops-python-pre-install  Job completed
Normal  SuccessfulCreate  job/devops-python-post-install Created pod: devops-python-post-install-kmrmw
Normal  Completed         job/devops-python-post-install Job completed
```

Evidence that deletion policy worked:

```bash
$ kubectl get jobs -n lab10
No resources found in lab10 namespace.
```

## Installation Evidence

Installed releases:

```bash
$ helm list -A
NAME          NAMESPACE REVISION UPDATED                              STATUS   CHART               APP VERSION
devops-go     lab10     1        2026-03-29 15:45:56.758167 +0300 MSK deployed devops-go-0.1.0     1.0.0
devops-python lab10     2        2026-03-29 15:45:04.29024 +0300 MSK  deployed devops-python-0.1.0 1.0.0
```

Deployed Kubernetes resources:

```bash
$ kubectl get all -n lab10
NAME                                 READY   STATUS    RESTARTS   AGE
pod/devops-go-5c878547ff-p7xzr       1/1     Running   0          16s
pod/devops-go-5c878547ff-qt8gw       1/1     Running   0          16s
pod/devops-python-6ff9df5f74-gf8sc   1/1     Running   0          58s
pod/devops-python-6ff9df5f74-hd4kp   1/1     Running   0          48s
pod/devops-python-6ff9df5f74-hw959   1/1     Running   0          68s

NAME                    TYPE           CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
service/devops-go       NodePort       10.96.10.223   <none>        80:31081/TCP   16s
service/devops-python   LoadBalancer   10.96.84.132   <pending>     80:31080/TCP   2m1s

NAME                            READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-go       2/2     2            2           16s
deployment.apps/devops-python   3/3     3            3           2m1s
```

Development values before upgrade:

```bash
$ helm get values devops-python -n lab10 --all
...
env:
  DEPLOYMENT_TRACK: dev
replicaCount: 1
resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
service:
  nodePort: 31080
  port: 80
  targetPort: 5000
  type: NodePort
```

Production values after upgrade:

```bash
$ helm get values devops-python -n lab10 --all
...
env:
  DEPLOYMENT_TRACK: prod
replicaCount: 3
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 200m
    memory: 256Mi
service:
  port: 80
  targetPort: 5000
  type: LoadBalancer
```

Cluster-side verification of the production upgrade:

```bash
$ kubectl describe deployment -n lab10 devops-python
Replicas:               3 desired | 3 updated | 4 total | 3 available | 1 unavailable
Image:                  vladk6813050/devops-info-service-py:lab02
Limits:                 cpu 500m, memory 512Mi
Requests:               cpu 200m, memory 256Mi
Environment:            PORT=5000, DEPLOYMENT_TRACK=prod
```

## Operations

Commands used in this lab:

```bash
# dependency packaging
helm dependency update k8s/devops-python
helm dependency update k8s/devops-go

# lint
helm lint k8s/devops-python
helm lint k8s/devops-go

# render locally
helm template devops-python k8s/devops-python -f k8s/devops-python/values-dev.yaml
helm template devops-go k8s/devops-go

# dry-run install
helm install --dry-run --debug devops-python k8s/devops-python -n lab10 --create-namespace -f k8s/devops-python/values-dev.yaml

# live install / upgrade
helm install devops-python k8s/devops-python -n lab10 --create-namespace -f k8s/devops-python/values-dev.yaml --wait
helm upgrade devops-python k8s/devops-python -n lab10 -f k8s/devops-python/values-prod.yaml --wait
helm install devops-go k8s/devops-go -n lab10 --wait
```

How to rollback:

```bash
helm history devops-python -n lab10
helm rollback devops-python 1 -n lab10 --wait
```

Actual release history:

```bash
$ helm history devops-python -n lab10
REVISION UPDATED                  STATUS     CHART               APP VERSION DESCRIPTION
1        Sun Mar 29 15:43:49 2026 superseded devops-python-0.1.0 1.0.0       Install complete
2        Sun Mar 29 15:45:04 2026 deployed   devops-python-0.1.0 1.0.0       Upgrade complete
```

How to uninstall:

```bash
helm uninstall devops-go -n lab10
helm uninstall devops-python -n lab10
kubectl delete namespace lab10
```

## Testing & Validation

Linting:

```bash
$ helm lint k8s/devops-python
1 chart(s) linted, 0 chart(s) failed

$ helm lint k8s/devops-go
1 chart(s) linted, 0 chart(s) failed
```

Template verification:

```bash
$ helm template devops-python k8s/devops-python -f k8s/devops-python/values-dev.yaml
# renders Service, Deployment, pre-install Job, post-install Job
```

Dry-run verification:

```bash
$ helm install --dry-run --debug devops-python k8s/devops-python -n lab10 --create-namespace -f k8s/devops-python/values-dev.yaml
STATUS: pending-install
HOOKS:
  Job/devops-python-pre-install
  Job/devops-python-post-install
MANIFEST:
  Service/devops-python
  Deployment/devops-python
```

Application accessibility verification:

```bash
$ kubectl port-forward -n lab10 service/devops-python 8080:80
$ curl -s http://127.0.0.1:8080/health
{"status":"healthy","timestamp":"2026-03-29T12:46:26.798865Z","uptime_seconds":80}
```

```bash
$ curl -s http://127.0.0.1:8080/ | jq '{service: .service, request: .request}'
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "FastAPI"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  }
}
```

```bash
$ kubectl port-forward -n lab10 service/devops-go 8081:80
$ curl -s http://127.0.0.1:8081/ | jq '{service: .service, request: .request}'
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Go net/http"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  }
}
```

## Bonus — Library Chart

Library chart:
- path: `k8s/common-lib`
- type: `library`
- purpose: shared helper templates for names and labels

Shared templates implemented:
- `common.name`
- `common.chart`
- `common.fullname`
- `common.selectorLabels`
- `common.labels`

Both charts use the library as a dependency:

```bash
$ helm dependency list k8s/devops-python
NAME       VERSION REPOSITORY           STATUS
common-lib 0.1.0   file://../common-lib ok

$ helm dependency list k8s/devops-go
NAME       VERSION REPOSITORY           STATUS
common-lib 0.1.0   file://../common-lib ok
```

Dependency packages produced by Helm:

```bash
$ ls -1 k8s/devops-python/charts k8s/devops-go/charts
k8s/devops-go/charts:
common-lib-0.1.0.tgz

k8s/devops-python/charts:
common-lib-0.1.0.tgz
```

Benefits of the library chart approach:
- DRY: naming/label logic exists in one place
- consistency: both charts render the same metadata shape
- maintainability: chart helper changes are made once and reused everywhere
- extensibility: future charts can consume the same library without copy/paste

## Notes

Two practical issues came up during implementation:
- existing NodePorts from lab09 already occupied `30080/30081`, so Helm charts were moved to `31080/31081`
- the Go chart uses a local image `devops-info-service-go:lab10`, so before installation I built it locally and loaded it into the `kind` cluster with `kind load docker-image`
