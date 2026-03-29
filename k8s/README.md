# Lab 09 — Kubernetes Fundamentals

## Architecture Overview

I used `kind` because it is lightweight, deterministic, Docker-based, and easy to automate with a checked-in cluster config. That made it a better fit here than `minikube`, especially because the bonus task needs predictable Ingress wiring on a local cluster.

Core Kubernetes concepts used in this lab:
- `Pod`: the runtime unit for each app replica.
- `Deployment`: keeps the desired replica count and performs rolling updates/rollbacks.
- `Service`: provides a stable virtual IP and NodePort access for local testing.
- `Namespace`: isolates all lab resources inside `lab09`.

Deployment layout:
- Namespace: `lab09`
- App 1: Python FastAPI service, `Deployment` with `3` replicas, exposed by `Service/devops-info-py`
- App 2: Go HTTP service, `Deployment` with `2` replicas, exposed by `Service/devops-info-go`
- Ingress: `Ingress/devops-course-ingress` with TLS for `local.example.com`
- Ingress controller: `ingress-nginx` deployed in `ingress-nginx` namespace

Networking flow:

```text
Client
  -> NodePort service (Task 3 direct access / port-forward)
  -> ingress-nginx (Bonus HTTPS entrypoint on localhost:443)
      -> /app1 -> Service/devops-info-py -> Python Pods
      -> /app2 -> Service/devops-info-go -> Go Pods
```

Resource allocation strategy:
- Python app: `requests` `100m` CPU / `128Mi`, `limits` `250m` CPU / `256Mi`
- Go app: `requests` `50m` CPU / `64Mi`, `limits` `150m` CPU / `128Mi`
- Rationale: enough headroom for local orchestration and probes without overcommitting the test cluster

## Local Kubernetes Setup

Installed and used:
- `kubectl` client: preinstalled locally
- `kind`: installed via Homebrew
- container runtime: `colima` with Docker runtime

Cluster creation files:
- `k8s/kind-config.yml` configures a 2-node `kind` cluster
- port mappings `80` and `443` are exposed on the host
- `ingress-ready=true` is applied to the control-plane node for the bonus task

Cluster setup evidence:

```bash
$ kubectl cluster-info --context kind-lab09
Kubernetes control plane is running at https://127.0.0.1:53973
CoreDNS is running at https://127.0.0.1:53973/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

```bash
$ kubectl get nodes -o wide
NAME                  STATUS   ROLES           AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE                         KERNEL-VERSION     CONTAINER-RUNTIME
lab09-control-plane   Ready    control-plane   30s   v1.33.1   172.18.0.3    <none>        Debian GNU/Linux 12 (bookworm)   6.8.0-64-generic   containerd://2.1.1
lab09-worker          Ready    <none>          16s   v1.33.1   172.18.0.2    <none>        Debian GNU/Linux 12 (bookworm)   6.8.0-64-generic   containerd://2.1.1
```

## Manifest Files

- `k8s/namespace.yml`: dedicated `lab09` namespace for isolation.
- `k8s/kind-config.yml`: local cluster config with host ports `80/443` and `ingress-ready=true`.
- `k8s/deployment.yml`: production-style Python deployment with 3 replicas, rolling update strategy, probes, resource requests/limits, and explicit numeric UID/GID.
- `k8s/deployment-v2.yml`: rollout variant used to demonstrate config-based rolling updates.
- `k8s/service.yml`: NodePort service for the Python app on `30080`.
- `k8s/go-deployment.yml`: second app for the bonus task, deployed as a Go service.
- `k8s/go-service.yml`: NodePort service for the Go app on `30081`.
- `k8s/ingress.yml`: path-based routing and TLS termination for `/app1` and `/app2`.

Key configuration choices:
- `replicas: 3` for the main app because the lab explicitly requires at least 3 replicas.
- `maxUnavailable: 0` and `maxSurge: 1` to keep the service available during rollouts.
- `startupProbe`, `livenessProbe`, and `readinessProbe` all target `/health`.
- `runAsUser: 1000`, `runAsGroup: 1000`, `runAsNonRoot: true` were added because the original image uses a named user, which kubelet could not verify as non-root.
- `NodePort` was kept for local direct access, while Ingress provides the bonus HTTPS routing layer.

## Deployment Evidence

Current workload state:

```bash
$ kubectl get all -n lab09
NAME                                  READY   STATUS    RESTARTS   AGE
pod/devops-info-go-7fdc6c6747-dkhc5   1/1     Running   0          2m49s
pod/devops-info-go-7fdc6c6747-kskzg   1/1     Running   0          2m49s
pod/devops-info-py-7ff4d6b99-9m45s    1/1     Running   0          3m22s
pod/devops-info-py-7ff4d6b99-gzk25    1/1     Running   0          3m27s
pod/devops-info-py-7ff4d6b99-hkwg5    1/1     Running   0          3m17s

NAME                     TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
service/devops-info-go   NodePort   10.96.16.236   <none>        80:30081/TCP   2m49s
service/devops-info-py   NodePort   10.96.252.91   <none>        80:30080/TCP   8m54s

NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-info-go   2/2     2            2           2m49s
deployment.apps/devops-info-py   3/3     3            3           8m54s
```

Detailed pod and service view:

```bash
$ kubectl get pods,svc -n lab09 -o wide
NAME                                  READY   STATUS    RESTARTS   AGE     IP            NODE           NOMINATED NODE   READINESS GATES
pod/devops-info-go-7fdc6c6747-dkhc5   1/1     Running   0          2m39s   10.244.1.24   lab09-worker   <none>           <none>
pod/devops-info-go-7fdc6c6747-kskzg   1/1     Running   0          2m39s   10.244.1.25   lab09-worker   <none>           <none>
pod/devops-info-py-7ff4d6b99-9m45s    1/1     Running   0          3m12s   10.244.1.22   lab09-worker   <none>           <none>
pod/devops-info-py-7ff4d6b99-gzk25    1/1     Running   0          3m17s   10.244.1.21   lab09-worker   <none>           <none>
pod/devops-info-py-7ff4d6b99-hkwg5    1/1     Running   0          3m7s    10.244.1.23   lab09-worker   <none>           <none>

NAME                     TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE     SELECTOR
service/devops-info-go   NodePort   10.96.16.236   <none>        80:30081/TCP   2m39s   app.kubernetes.io/name=devops-info-go
service/devops-info-py   NodePort   10.96.252.91   <none>        80:30080/TCP   8m44s   app.kubernetes.io/name=devops-info-py
```

Deployment description excerpt:

```bash
$ kubectl describe deployment devops-info-py -n lab09
Name:                   devops-info-py
Namespace:              lab09
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
RollingUpdateStrategy:  0 max unavailable, 1 max surge
Image:                  vladk6813050/devops-info-service-py:lab02
Limits:                 cpu 250m, memory 256Mi
Requests:               cpu 100m, memory 128Mi
Liveness:               http-get /health
Readiness:              http-get /health
Startup:                http-get /health
Environment:            PORT=5000, DEPLOYMENT_TRACK=v1
```

Application verification:

Direct service verification via `port-forward`:

```bash
$ kubectl port-forward -n lab09 service/devops-info-py 8080:80
Forwarding from 127.0.0.1:8080 -> 5000
```

```bash
$ curl -s http://127.0.0.1:8080/health
{"status":"healthy","timestamp":"2026-03-29T12:21:57.081895Z","uptime_seconds":32}
```

```bash
$ curl -s http://127.0.0.1:8080/ | jq '{service: .service, runtime: .runtime, request: .request}'
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "FastAPI"
  },
  "runtime": {
    "uptime_seconds": 32,
    "uptime_human": "0 hours, 0 minutes",
    "current_time": "2026-03-29T12:21:57.085526Z",
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "127.0.0.1",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  }
}
```

## Operations Performed

### Deploy

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
kubectl rollout status deployment/devops-info-py -n lab09
```

### Scaling Demo

Scaled the deployment to 5 replicas imperatively:

```bash
$ kubectl scale deployment/devops-info-py -n lab09 --replicas=5
deployment.apps/devops-info-py scaled

$ kubectl get deployment devops-info-py -n lab09
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
devops-info-py   5/5     5            5           105s
```

Then returned to the declarative baseline with:

```bash
kubectl apply -f k8s/deployment.yml
```

### Rolling Update Demo

The rollout was triggered by changing a pod template environment variable from `DEPLOYMENT_TRACK=v1` to `DEPLOYMENT_TRACK=v2` in `k8s/deployment-v2.yml`.

```bash
$ kubectl apply -f k8s/deployment-v2.yml
deployment.apps/devops-info-py configured

$ kubectl rollout status deployment/devops-info-py -n lab09
deployment "devops-info-py" successfully rolled out
```

### Rollback Demo

Working rollback was demonstrated after restoring the corrected stable manifest:

```bash
$ kubectl rollout undo deployment/devops-info-py -n lab09
deployment.apps/devops-info-py rolled back

$ kubectl get deployment devops-info-py -n lab09 -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="DEPLOYMENT_TRACK")].value}'
v1
```

Rollout history:

```bash
$ kubectl rollout history deployment/devops-info-py -n lab09
deployment.apps/devops-info-py
REVISION  CHANGE-CAUSE
2         Apply k8s/deployment-v2.yml with DEPLOYMENT_TRACK=v2
3         Apply k8s/deployment-v2.yml with DEPLOYMENT_TRACK=v2
4         Restore stable v1 manifest with explicit UID/GID
6         Apply k8s/deployment-v2.yml after stable restore
7         Apply k8s/deployment-v2.yml after stable restore
```

### Zero-Downtime Verification

`port-forward` itself had one transient `Empty reply` during an update, which is a tunnel artifact and not a service outage. To verify the service path correctly, I ran 20 consecutive in-cluster requests through the Kubernetes Service during rollback:

```bash
$ kubectl logs -n lab09 zero-downtime-check
request_1=ok
request_2=ok
request_3=ok
request_4=ok
request_5=ok
request_6=ok
request_7=ok
request_8=ok
request_9=ok
request_10=ok
request_11=ok
request_12=ok
request_13=ok
request_14=ok
request_15=ok
request_16=ok
request_17=ok
request_18=ok
request_19=ok
request_20=ok
```

### Service Access Method

For `kind`, the direct local access method used for Task 3 was `kubectl port-forward`. For the bonus task, traffic went through `Ingress` on host ports `80/443`.

## Bonus — Ingress with TLS

Second application deployment:
- `Deployment/devops-info-go`
- `Service/devops-info-go`

Ingress controller installation:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx
```

Ingress state:

```bash
$ kubectl get ingress -n lab09 -o wide
NAME                    CLASS   HOSTS               ADDRESS     PORTS     AGE
devops-course-ingress   nginx   local.example.com   localhost   80, 443   2m11s
```

TLS secret creation:

```bash
cat >/tmp/lab09-tls/openssl.cnf <<'EOF'
[req]
distinguished_name = dn
x509_extensions = v3_req
prompt = no

[dn]
CN = local.example.com
O = local.example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = local.example.com
EOF

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /tmp/lab09-tls/tls.key \
  -out /tmp/lab09-tls/tls.crt \
  -config /tmp/lab09-tls/openssl.cnf \
  -extensions v3_req

kubectl create secret tls apps-tls -n lab09 \
  --key /tmp/lab09-tls/tls.key \
  --cert /tmp/lab09-tls/tls.crt \
  --dry-run=client -o yaml | kubectl apply -f -
```

Routing verification:

HTTP redirects to HTTPS:

```bash
$ curl -si --noproxy '*' --resolve local.example.com:80:127.0.0.1 http://local.example.com/app1
HTTP/1.1 308 Permanent Redirect
Location: https://local.example.com/app1
```

HTTPS to app1:

```bash
$ curl -ski --noproxy '*' --resolve local.example.com:443:127.0.0.1 https://local.example.com/app1
HTTP/2 200
...
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"request":{"client_ip":"10.244.0.5","user_agent":"curl/8.7.1","method":"GET","path":"/"}}
```

HTTPS to app1 health endpoint:

```bash
$ curl -sk --noproxy '*' --resolve local.example.com:443:127.0.0.1 https://local.example.com/app1/health
{"status":"healthy","timestamp":"2026-03-29T12:29:03.339809Z","uptime_seconds":168}
```

HTTPS to app2:

```bash
$ curl -sk --noproxy '*' --resolve local.example.com:443:127.0.0.1 https://local.example.com/app2 | jq '{service: .service, request: .request}'
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "Go net/http"
  },
  "request": {
    "client_ip": "10.244.0.5",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  }
}
```

Why Ingress is better than plain NodePort here:
- one HTTPS entrypoint instead of exposing every application separately
- path-based routing for multiple backends on one host
- centralized TLS termination
- closer to production traffic-management patterns

## Production Considerations

Health checks:
- `startupProbe` prevents premature restarts during app boot
- `readinessProbe` removes unready pods from service endpoints
- `livenessProbe` lets Kubernetes self-heal unhealthy containers

Resource limits rationale:
- requests guarantee schedulable minimums
- limits prevent a single lab workload from starving the node
- values are conservative because these are small stateless APIs

How I would improve this for production:
- add `HorizontalPodAutoscaler`
- add `PodDisruptionBudget`
- distribute replicas with `topologySpreadConstraints` or anti-affinity
- move runtime config to `ConfigMap` and secrets to external secret management
- pin image digests instead of mutable tags
- replace local self-signed TLS with cert-manager and trusted CA
- use Gateway API instead of `ingress-nginx` for future-proof traffic management

Monitoring and observability:
- scrape `/health` and application metrics with Prometheus
- centralize logs via Loki or Elasticsearch
- add tracing with OpenTelemetry
- create alerts on pod restarts, readiness failures, and rollout failures

## Challenges & Solutions

1. `CreateContainerConfigError` on the Python deployment.
   Cause: the image runs as a named user `app`, and kubelet could not verify that as non-root when `runAsNonRoot` was enabled.
   Fix: set explicit `runAsUser: 1000` and `runAsGroup: 1000` in the pod security context.

2. Ingress returned an empty response from host `80/443`.
   Cause: `kind` host port mappings were on the control-plane node, but `ingress-nginx-controller` was scheduled on the worker node.
   Fix: patch the controller deployment with `nodeSelector: ingress-ready=true`.

3. TLS secret was initially accepted with warnings.
   Cause: the first self-signed cert used only `CN`, while newer validation expects SAN.
   Fix: regenerate the certificate with `subjectAltName = DNS:local.example.com`.

4. The earliest rollback revision restored a pre-fix broken replica set.
   Cause: revision history already contained the initial security-context mistake.
   Fix: restore the corrected stable manifest and then demonstrate a clean working rollback from the corrected history.

What I learned:
- local Kubernetes debugging is mostly `kubectl describe`, `kubectl logs`, `kubectl get events`, and checking controller placement
- a Service-level zero-downtime check is more reliable than judging availability through `port-forward`
- `kind` is excellent for repeatable local labs, but you still need to understand where host ports actually land
