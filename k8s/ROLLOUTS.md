# Lab 14 — Progressive Delivery with Argo Rollouts

Execution date: 2026-04-21  
Cluster context: `kind-devops-labs`

## Argo Rollouts Setup

Argo Rollouts was installed into a dedicated `argo-rollouts` namespace together with the dashboard service and the `kubectl argo rollouts` plugin.

Installation verification:

```bash
$ kubectl get pods -n argo-rollouts
NAME                                      READY   STATUS    RESTARTS   AGE
argo-rollouts-5f64f8d68-gwt9v             1/1     Running   0          23h
argo-rollouts-dashboard-755bbc64c-87w7q   1/1     Running   0          23h

$ kubectl get svc -n argo-rollouts
NAME                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
argo-rollouts-dashboard   ClusterIP   10.96.151.246   <none>        3100/TCP   23h
argo-rollouts-metrics     ClusterIP   10.96.218.98    <none>        8090/TCP   23h

$ kubectl argo rollouts version
kubectl-argo-rollouts: v1.8.3+49fa151
```

Dashboard access:

```bash
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

Rollout vs Deployment:

- `Rollout` keeps the familiar Deployment-style pod template and selector model, but adds progressive delivery strategies.
- Canary adds explicit rollout steps, pauses, weights, and analysis stages.
- Blue-green adds separate active and preview services for instant traffic switching.
- Deployments roll out directly and do not support built-in analysis-driven aborts or preview services.

## Chart Changes

Implemented files:

- `k8s/devops-python/templates/rollout.yaml`
- `k8s/devops-python/templates/service-preview.yaml`
- `k8s/devops-python/templates/analysis-template.yaml`
- `k8s/devops-python/templates/deployment.yaml`
- `k8s/devops-python/templates/_helpers.tpl`
- `k8s/devops-python/values-rollout-canary.yaml`
- `k8s/devops-python/values-rollout-canary-v2.yaml`
- `k8s/devops-python/values-rollout-canary-fail.yaml`
- `k8s/devops-python/values-rollout-bluegreen.yaml`
- `k8s/devops-python/values-rollout-bluegreen-v2.yaml`

Important implementation detail:

- The chart now renders a `Deployment` only when `rollout.enabled=false`.
- The overlay values files for v2 and failure scenarios were made self-contained, so a direct `helm upgrade` still renders a `Rollout` instead of falling back to a plain `Deployment`.

## Canary Deployment

Base canary installation:

```bash
helm upgrade canary k8s/devops-python \
  -n lab14-canary \
  -f k8s/devops-python/values-rollout-canary.yaml
```

Canary strategy:

- 20% traffic, then manual pause
- analysis step using `AnalysisTemplate`
- 40%, 60%, 80% with timed pauses
- 100% full promotion

Manual promotion evidence after updating to `canary-v2`:

```bash
$ kubectl argo rollouts get rollout canary-devops-python -n lab14-canary
Name:            canary-devops-python
Namespace:       lab14-canary
Status:          Paused
Message:         CanaryPauseStep
Strategy:        Canary
  Step:          1/10
  SetWeight:     20
  ActualWeight:  20
```

```bash
$ kubectl argo rollouts promote canary-devops-python -n lab14-canary
rollout 'canary-devops-python' promoted
```

Analysis step success:

```bash
$ kubectl argo rollouts get rollout canary-devops-python -n lab14-canary
...
  Step:          4/10
  SetWeight:     40
  ActualWeight:  40
...
  AnalysisRun  Successful
```

Final healthy state:

```bash
$ kubectl argo rollouts get rollout canary-devops-python -n lab14-canary
Name:            canary-devops-python
Namespace:       lab14-canary
Status:          Healthy
Strategy:        Canary
  Step:          10/10
  SetWeight:     100
  ActualWeight:  100
```

Useful validation commands:

```bash
kubectl get rollout,pods,svc,pvc,analysisrun,replicaset -n lab14-canary
kubectl argo rollouts get rollout canary-devops-python -n lab14-canary
kubectl argo rollouts status canary-devops-python -n lab14-canary --timeout 180s
```

## Blue-Green Deployment

Base blue-green installation:

```bash
helm upgrade bluegreen k8s/devops-python \
  -n lab14-bluegreen \
  -f k8s/devops-python/values-rollout-bluegreen.yaml
```

Blue-green strategy:

- `bluegreen-devops-python` is the active service
- `bluegreen-devops-python-preview` is the preview service
- `autoPromotionEnabled: false` keeps promotion manual

Preview vs active service verification:

```bash
$ curl -s http://127.0.0.1:18080/ | jq '.deployment'
{
  "track": "green-v2",
  "environment": "bluegreen"
}

$ curl -s http://127.0.0.1:18081/ | jq '.deployment'
{
  "track": "blue-v1",
  "environment": "bluegreen"
}
```

Paused preview state before promotion:

```bash
$ kubectl argo rollouts get rollout bluegreen-devops-python -n lab14-bluegreen
Name:            bluegreen-devops-python
Namespace:       lab14-bluegreen
Status:          Paused
Message:         BlueGreenPause
Strategy:        BlueGreen
```

Promotion example:

```bash
$ kubectl argo rollouts promote bluegreen-devops-python -n lab14-bluegreen
rollout 'bluegreen-devops-python' promoted
```

Final healthy state:

```bash
$ kubectl argo rollouts get rollout bluegreen-devops-python -n lab14-bluegreen
Name:            bluegreen-devops-python
Namespace:       lab14-bluegreen
Status:          Healthy
Strategy:        BlueGreen
Images:          devops-info-service-py:lab14 (active, stable)
```

Useful validation commands:

```bash
kubectl get rollout,pods,svc,pvc,replicaset -n lab14-bluegreen
kubectl argo rollouts get rollout bluegreen-devops-python -n lab14-bluegreen
kubectl argo rollouts promote bluegreen-devops-python -n lab14-bluegreen
kubectl port-forward -n lab14-bluegreen svc/bluegreen-devops-python 18080:80
kubectl port-forward -n lab14-bluegreen svc/bluegreen-devops-python-preview 18081:80
```

## Automated Analysis

The bonus task uses a web-based `AnalysisTemplate` instead of Prometheus metrics. It validates `/health` and expects `.status == "healthy"`.

Template behavior:

- `interval: 10s`
- `count: 3`
- `failureLimit: 1`
- `successCondition: result == 'healthy'`

Failing canary scenario:

```bash
helm upgrade canary k8s/devops-python \
  -n lab14-canary \
  -f k8s/devops-python/values-rollout-canary.yaml \
  -f k8s/devops-python/values-rollout-canary-fail.yaml
```

That overlay changes the analysis path to `/does-not-exist`, which forces the rollout to abort while keeping the stable ReplicaSet active.

Failure evidence:

```bash
$ kubectl argo rollouts status canary-devops-python -n lab14-canary --timeout 180s
Degraded - RolloutAborted: Rollout aborted update to revision 2: Step-based analysis phase error/failed: Metric "webcheck" assessed Error due to consecutiveErrors (5) > consecutiveErrorLimit (4): "Error Message: received non 2xx response code: 404"
```

This demonstrates automated rollback behavior: the bad revision never became stable, and the previous healthy ReplicaSet continued serving traffic.

## Strategy Comparison

Canary is better when:

- you want gradual exposure
- you need analysis-driven promotion or rollback
- you are comfortable with longer rollout windows

Blue-green is better when:

- you want an isolated preview before the cutover
- you need instant traffic switching
- you can afford running both versions at the same time

Tradeoffs:

- Canary is safer for unknown risk, but slower and more operationally chatty.
- Blue-green is simpler to reason about during cutover, but doubles runtime capacity during promotion.
- For customer-facing production changes with meaningful risk, I would prefer canary.
- For clean release validation or schema-compatible application swaps, I would prefer blue-green.

## CLI Reference

Commands used during the lab:

```bash
kubectl argo rollouts version
kubectl argo rollouts get rollout <name> -n <namespace>
kubectl argo rollouts status <name> -n <namespace> --timeout 180s
kubectl argo rollouts promote <name> -n <namespace>
helm upgrade <release> k8s/devops-python -n <namespace> -f <values>
kubectl get rollout,pods,svc,pvc,analysisrun,replicaset -n <namespace>
```

## Screenshots

- `k8s/evidence/lab14/rollouts-dashboard-canary.png`
- `k8s/evidence/lab14/rollouts-dashboard-bluegreen.png`
