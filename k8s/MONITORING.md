# Lab 16 — Kubernetes Monitoring & Init Containers

Execution date: 2026-04-30  
Cluster context: `kind-devops-labs`

## Stack Components

- Prometheus Operator manages the Prometheus, Alertmanager, and ServiceMonitor custom resources.
- Prometheus scrapes metrics from cluster components and application endpoints.
- Alertmanager receives alerts from Prometheus and groups or routes them.
- Grafana provides dashboards on top of Prometheus data.
- `kube-state-metrics` exposes Kubernetes object state like pod and StatefulSet metadata.
- `node-exporter` exposes node-level OS metrics such as memory and CPU.

## Installation Evidence

Installation:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

Verification:

```bash
$ kubectl get po,svc -n monitoring
NAME                                                         READY   STATUS    RESTARTS       AGE
pod/alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   0              7m25s
pod/monitoring-grafana-54c7d77c6c-7jkwn                      3/3     Running   1              8m28s
pod/monitoring-kube-prometheus-operator-64d78955c8-s96vb     1/1     Running   3              8m28s
pod/monitoring-kube-state-metrics-67d5f7bf68-vvhg2           1/1     Running   2              8m28s
pod/monitoring-prometheus-node-exporter-mkcr5                1/1     Running   0              8m22s
pod/monitoring-prometheus-node-exporter-wd6mb                1/1     Running   0              8m28s
pod/prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   0              7m22s

NAME                                              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)                      AGE
service/alertmanager-operated                     ClusterIP   None            <none>        9093/TCP,9094/TCP,9094/UDP   7m26s
service/monitoring-grafana                        ClusterIP   10.96.182.190   <none>        80/TCP                       8m35s
service/monitoring-kube-prometheus-alertmanager   ClusterIP   10.96.233.10    <none>        9093/TCP,8080/TCP            8m35s
service/monitoring-kube-prometheus-operator       ClusterIP   10.96.188.107   <none>        443/TCP                      8m35s
service/monitoring-kube-prometheus-prometheus     ClusterIP   10.96.100.121   <none>        9090/TCP,8080/TCP            8m35s
service/monitoring-kube-state-metrics             ClusterIP   10.96.181.88    <none>        8080/TCP                     8m35s
service/monitoring-prometheus-node-exporter       ClusterIP   10.96.124.12    <none>        9100/TCP                     8m35s
service/prometheus-operated                       ClusterIP   None            <none>        9090/TCP                     7m22s
```

Access commands:

```bash
kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090
kubectl port-forward svc/monitoring-kube-prometheus-alertmanager -n monitoring 9093:9093
kubectl get secret monitoring-grafana -n monitoring -o jsonpath='{.data.admin-password}' | base64 -d
```

Grafana admin password retrieved during validation:

```text
sb2i1VhqjGidgqOVNCwr4OtVH2127t3T04BPCFZd
```

## Dashboard Answers

### 1. Pod Resources for the StatefulSet

The monitored StatefulSet in `lab16` is `monitored-devops-python`.

CPU usage from Prometheus:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=sum(rate(container_cpu_usage_seconds_total{namespace="lab16",pod=~"monitored-devops-python-.*",container="devops-python"}[5m])) by (pod)' | jq '.data.result'
[
  { "metric": { "pod": "monitored-devops-python-1" }, "value": [ ..., "0.017006049999999998" ] },
  { "metric": { "pod": "monitored-devops-python-0" }, "value": [ ..., "0.007109396250000001" ] },
  { "metric": { "pod": "monitored-devops-python-2" }, "value": [ ..., "0.015036544" ] }
]
```

Memory usage from Prometheus:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=sum(container_memory_working_set_bytes{namespace="lab16",pod=~"monitored-devops-python-.*",container="devops-python"}) by (pod)' | jq '.data.result'
[
  { "metric": { "pod": "monitored-devops-python-1" }, "value": [ ..., "42508288" ] },
  { "metric": { "pod": "monitored-devops-python-0" }, "value": [ ..., "39641088" ] },
  { "metric": { "pod": "monitored-devops-python-2" }, "value": [ ..., "38141952" ] }
]
```

Interpretation:

- highest CPU: `monitored-devops-python-1` at about `0.017` CPU cores
- lowest CPU: `monitored-devops-python-0` at about `0.007` CPU cores
- highest memory: `monitored-devops-python-1` at about `40.5 MiB`
- lowest memory: `monitored-devops-python-2` at about `36.4 MiB`

### 2. Default Namespace CPU Analysis

At capture time there were no application pods in the `default` namespace:

```bash
$ kubectl get pods -n default
No resources found in default namespace.
```

Prometheus confirmed there were no CPU results there either:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=sort_desc(sum(rate(container_cpu_usage_seconds_total{namespace="default",container!="",pod!=""}[5m])) by (pod))' | jq '.data.result'
[]
```

So the correct answer for this cluster snapshot is that there are no pods using CPU in `default`.

### 3. Node Metrics

Node memory usage percentage:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100' | jq '.data.result'
[
  { "metric": { "instance": "172.18.0.3:9100", "pod": "monitoring-prometheus-node-exporter-mkcr5" }, "value": [ ..., "62.522445148051695" ] },
  { "metric": { "instance": "172.18.0.2:9100", "pod": "monitoring-prometheus-node-exporter-wd6mb" }, "value": [ ..., "62.48048837486775" ] }
]
```

Node memory used in MiB:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024' | jq '.data.result'
[
  { "metric": { "instance": "172.18.0.3:9100", "pod": "monitoring-prometheus-node-exporter-mkcr5" }, "value": [ ..., "4687.93359375" ] },
  { "metric": { "instance": "172.18.0.2:9100", "pod": "monitoring-prometheus-node-exporter-wd6mb" }, "value": [ ..., "4950.3046875" ] }
]
```

CPU cores:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=machine_cpu_cores' | jq '.data.result'
[
  { "metric": { "node": "devops-labs-control-plane" }, "value": [ ..., "4" ] },
  { "metric": { "node": "devops-labs-worker" }, "value": [ ..., "4" ] }
]
```

### 4. Kubelet Managed Pods and Containers

Running pods:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=kubelet_running_pods' | jq '.data.result'
[
  { "metric": { "node": "devops-labs-control-plane" }, "value": [ ..., "10" ] },
  { "metric": { "node": "devops-labs-worker" }, "value": [ ..., "43" ] }
]
```

Running containers:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=kubelet_running_containers' | jq '.data.result'
...
{ "metric": { "node": "devops-labs-control-plane", "container_state": "running" }, "value": [ ..., "10" ] }
{ "metric": { "node": "devops-labs-worker", "container_state": "running" }, "value": [ ..., "47" ] }
...
```

### 5. Network Traffic for Default Namespace

There was no pod traffic in `default` because the namespace had no running pods.
I verified this directly with `kubectl` and Prometheus queries. In Grafana the namespace dashboard falls back to `All` when a namespace has no matching series, so the direct queries are the clearest proof for this case:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=sum(rate(container_network_receive_bytes_total{namespace="default",pod!=""}[5m])) by (pod)' | jq '.data.result'
[]

$ curl -sG 'http://127.0.0.1:19090/api/v1/query' \
  --data-urlencode 'query=sum(rate(container_network_transmit_bytes_total{namespace="default",pod!=""}[5m])) by (pod)' | jq '.data.result'
[]
```

### 6. Alerts

Alertmanager reported active alerts at capture time:

```bash
$ curl -s http://127.0.0.1:19093/api/v2/alerts | jq '[.[] | {status:.status.state, alertname:.labels.alertname, severity:.labels.severity}]'
[
  { "status": "active", "alertname": "TargetDown", "severity": "warning" },
  { "status": "active", "alertname": "etcdInsufficientMembers", "severity": "critical" },
  { "status": "active", "alertname": "TargetDown", "severity": "warning" },
  { "status": "active", "alertname": "TargetDown", "severity": "warning" },
  { "status": "active", "alertname": "Watchdog", "severity": "none" },
  { "status": "active", "alertname": "TargetDown", "severity": "warning" }
]
```

## Init Containers

The lab16 workload was deployed as a StatefulSet with both required init-container patterns enabled.

Helm values file:

- `k8s/devops-python/values-monitoring.yaml`

Implementation details:

- `init-download` uses `wget` to save `https://example.com` into `/init-data/index.html`
- `wait-for-service` waits until `monitoring-grafana.monitoring.svc.cluster.local` resolves
- the main container mounts the same `emptyDir` at `/init-data`

Pod-level proof:

```bash
$ kubectl describe pod monitored-devops-python-0 -n lab16
Init Containers:
  init-download:
    State:          Terminated
      Reason:       Completed
      Exit Code:    0
  wait-for-service:
    State:          Terminated
      Reason:       Completed
      Exit Code:    0
```

Download log:

```bash
$ kubectl logs monitored-devops-python-0 -n lab16 -c init-download
Connecting to example.com (8.6.112.0:443)
wget: note: TLS certificate validation not implemented
saving to '/init-data/index.html'
index.html           100% |********************************|   528  0:00:00 ETA
'/init-data/index.html' saved
```

Wait-for-service proof:

```bash
$ kubectl logs monitored-devops-python-0 -n lab16 -c wait-for-service
Server:		10.96.0.10
Address:	10.96.0.10:53

Name:	monitoring-grafana.monitoring.svc.cluster.local
Address: 10.96.182.190
```

Shared volume proof from the main container:

```bash
$ kubectl exec -n lab16 monitored-devops-python-0 -- sh -c "ls -l /init-data && head -n 3 /init-data/index.html"
total 4
-rw-r--r-- 1 1000 1000 528 Apr 21 16:38 index.html
<!doctype html><html lang="en"><head><title>Example Domain</title>...
```

## Bonus — Custom Metrics & ServiceMonitor

App changes:

- added `prometheus-client` dependency
- added `/metrics` endpoint in `app_python/app.py`
- instrumented request counter, request duration histogram, visits gauge, and build info gauge

Kubernetes changes:

- added `templates/servicemonitor.yaml`
- enabled `serviceMonitor.enabled=true` in `k8s/devops-python/values-monitoring.yaml`

Runtime verification:

```bash
$ curl -s http://127.0.0.1:19500/metrics | rg 'devops_info_(http_requests_total|visits_count|build_info)'
# HELP devops_info_http_requests_total Total HTTP requests handled by the application.
# TYPE devops_info_http_requests_total counter
devops_info_http_requests_total{method="GET",path="/health",status_code="200"} 35.0
devops_info_http_requests_total{method="GET",path="/metrics",status_code="200"} 4.0
# HELP devops_info_visits_count Current persisted visits counter value.
# TYPE devops_info_visits_count gauge
devops_info_visits_count 0.0
# HELP devops_info_build_info Static application metadata.
# TYPE devops_info_build_info gauge
devops_info_build_info{deployment_track="monitoring",environment="monitoring",framework="FastAPI",version="1.0.0"} 1.0
```

Prometheus target discovery:

```bash
$ curl -s 'http://127.0.0.1:19090/api/v1/targets' | jq '.data.activeTargets[] | select(.labels.service=="monitored-devops-python") | {health:.health, scrapeUrl:.scrapeUrl, namespace:.labels.namespace, pod:.labels.pod}'
{
  "health": "up",
  "scrapeUrl": "http://10.244.1.95:5000/metrics",
  "namespace": "lab16",
  "pod": "monitored-devops-python-0"
}
{
  "health": "up",
  "scrapeUrl": "http://10.244.1.97:5000/metrics",
  "namespace": "lab16",
  "pod": "monitored-devops-python-1"
}
{
  "health": "up",
  "scrapeUrl": "http://10.244.1.99:5000/metrics",
  "namespace": "lab16",
  "pod": "monitored-devops-python-2"
}
```

Prometheus query proof:

```bash
$ curl -sG 'http://127.0.0.1:19090/api/v1/query' --data-urlencode 'query=devops_info_visits_count' | jq '.data.result'
[
  ...
  { "metric": { "namespace": "lab16", "pod": "monitored-devops-python-0", "service": "monitored-devops-python" }, "value": [ ..., "0" ] },
  { "metric": { "namespace": "lab16", "pod": "monitored-devops-python-1", "service": "monitored-devops-python" }, "value": [ ..., "0" ] },
  { "metric": { "namespace": "lab16", "pod": "monitored-devops-python-2", "service": "monitored-devops-python" }, "value": [ ..., "0" ] }
]
```

## Screenshots

- `k8s/evidence/lab16/grafana-statefulset-pods.png`
- `k8s/evidence/lab16/grafana-node-metrics.png`
- `k8s/evidence/lab16/grafana-kubelet.png`
- `k8s/evidence/lab16/grafana-default-namespace-network.png`
- `k8s/evidence/lab16/alertmanager-alerts.png`
