# Lab 15 — StatefulSets & Persistent Storage

Execution date: 2026-04-21  
Cluster context: `kind-devops-labs`

## StatefulSet Overview

StatefulSets are appropriate when each replica needs a stable name and its own persistent storage. That is different from Deployments and Rollouts, which are optimized for stateless replicas and interchangeable pods.

Key differences:

- Deployment pods get replaceable names with random suffixes.
- StatefulSet pods keep ordered ordinal names like `app-0`, `app-1`, `app-2`.
- Deployment-based persistence typically mounts one shared PVC.
- StatefulSet uses `volumeClaimTemplates` so each pod gets its own PVC.
- StatefulSet relies on a headless Service for direct per-pod DNS records.

Examples of StatefulSet workloads:

- databases
- message brokers
- clustered systems with peer discovery

## Chart Changes

Implemented files:

- `k8s/devops-python/templates/statefulset.yaml`
- `k8s/devops-python/templates/service-headless.yaml`
- `k8s/devops-python/values-statefulset.yaml`
- `k8s/devops-python/values-statefulset-partition.yaml`
- `k8s/devops-python/values-statefulset-ondelete.yaml`

Compatibility changes:

- `deployment.yaml` only renders when both `rollout.enabled=false` and `statefulset.enabled=false`
- `rollout.yaml` only renders when `statefulset.enabled=false`
- `pvc.yaml` is disabled for StatefulSet mode because storage comes from `volumeClaimTemplates`

Base installation:

```bash
kubectl create namespace lab15 --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install stateful k8s/devops-python \
  -n lab15 \
  -f k8s/devops-python/values-statefulset.yaml
```

## Resource Verification

```bash
$ kubectl get po,sts,svc,pvc -n lab15
NAME                           READY   STATUS    RESTARTS   AGE
pod/stateful-devops-python-0   1/1     Running   0          55s
pod/stateful-devops-python-1   1/1     Running   0          41s
pod/stateful-devops-python-2   1/1     Running   0          32s

NAME                                      READY   AGE
statefulset.apps/stateful-devops-python   3/3     55s

NAME                                      TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/stateful-devops-python            ClusterIP   10.96.210.216   <none>        80/TCP    55s
service/stateful-devops-python-headless   ClusterIP   None            <none>        80/TCP    55s

NAME                                                         STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/data-volume-stateful-devops-python-0   Bound    pvc-45ed9a5e-85d9-433e-a7a0-13985a4d515a   100Mi      RWO            standard       55s
persistentvolumeclaim/data-volume-stateful-devops-python-1   Bound    pvc-c00b3012-1351-4e6a-a4ff-f3ab4f30b453   100Mi      RWO            standard       41s
persistentvolumeclaim/data-volume-stateful-devops-python-2   Bound    pvc-96912ea3-838f-4ecb-a12a-b3722859a715   100Mi      RWO            standard       32s
```

This verifies:

- stable ordinal pod names
- separate per-pod PVCs
- both a normal ClusterIP service and a headless service

## Network Identity

The headless service is `stateful-devops-python-headless`. Each pod gets a stable DNS name:

- `stateful-devops-python-0.stateful-devops-python-headless.lab15.svc.cluster.local`
- `stateful-devops-python-1.stateful-devops-python-headless.lab15.svc.cluster.local`
- `stateful-devops-python-2.stateful-devops-python-headless.lab15.svc.cluster.local`

Resolution proof from `pod-0`:

```bash
$ kubectl exec -n lab15 stateful-devops-python-0 -- \
  python -c "import socket; print(socket.gethostbyname_ex('stateful-devops-python-1.stateful-devops-python-headless.lab15.svc.cluster.local'))"
('stateful-devops-python-1.stateful-devops-python-headless.lab15.svc.cluster.local', [], ['10.244.1.80'])

$ kubectl exec -n lab15 stateful-devops-python-0 -- \
  python -c "import socket; print(socket.gethostbyname_ex('stateful-devops-python-2.stateful-devops-python-headless.lab15.svc.cluster.local'))"
('stateful-devops-python-2.stateful-devops-python-headless.lab15.svc.cluster.local', [], ['10.244.1.82'])
```

## Per-Pod Storage Isolation

Each pod was accessed directly through its own port-forward, then the `/visits` counter was checked:

```bash
$ curl -s http://127.0.0.1:19080/visits | jq .
{
  "count": 2,
  "storage_file": "/data/visits"
}

$ curl -s http://127.0.0.1:19081/visits | jq .
{
  "count": 1,
  "storage_file": "/data/visits"
}

$ curl -s http://127.0.0.1:19082/visits | jq .
{
  "count": 4,
  "storage_file": "/data/visits"
}
```

The counts differ, which proves each pod keeps its own data on its own volume rather than sharing one common counter file.

## Persistence After Pod Deletion

Visit count was recorded on `pod-0`, then the pod was deleted without touching the StatefulSet:

```bash
$ kubectl exec -n lab15 stateful-devops-python-0 -- cat /data/visits
2

$ kubectl delete pod -n lab15 stateful-devops-python-0
pod "stateful-devops-python-0" deleted

$ kubectl wait --for=condition=ready pod/stateful-devops-python-0 -n lab15 --timeout=180s
pod/stateful-devops-python-0 condition met

$ kubectl exec -n lab15 stateful-devops-python-0 -- cat /data/visits
2
```

The IP changed after recreation, but the ordinal name and stored value stayed the same. That confirms the pod reattached its existing PVC.

## Bonus — Partitioned Rolling Update

Partitioned rollout configuration:

```bash
helm upgrade stateful k8s/devops-python \
  -n lab15 \
  -f k8s/devops-python/values-statefulset.yaml \
  -f k8s/devops-python/values-statefulset-partition.yaml
```

The chart set:

```bash
$ kubectl get sts stateful-devops-python -n lab15 -o jsonpath='{.spec.updateStrategy.type} partition={.spec.updateStrategy.rollingUpdate.partition} currentRevision={.status.currentRevision} updateRevision={.status.updateRevision}{"\n"}'
RollingUpdate partition=2 currentRevision=stateful-devops-python-547bdd7848 updateRevision=stateful-devops-python-85c59dd9f5
```

Pod-level result:

```bash
$ for pod in 0 1 2; do
    printf 'stateful-devops-python-%s ' "$pod"
    kubectl exec -n lab15 stateful-devops-python-$pod -- printenv DEPLOYMENT_TRACK
  done
stateful-devops-python-0 stateful-v1
stateful-devops-python-1 stateful-v1
stateful-devops-python-2 stateful-partition
```

Only pod `2` moved to the new revision. Pods `0` and `1` stayed on the old template, which is exactly what `partition: 2` should do.

## Bonus — OnDelete Strategy

OnDelete configuration:

```bash
helm upgrade stateful k8s/devops-python \
  -n lab15 \
  -f k8s/devops-python/values-statefulset.yaml \
  -f k8s/devops-python/values-statefulset-ondelete.yaml
```

Controller state:

```bash
$ kubectl get sts stateful-devops-python -n lab15 -o yaml | sed -n '1,220p'
...
spec:
  updateStrategy:
    type: OnDelete
...
status:
  currentRevision: stateful-devops-python-547bdd7848
  updateRevision: stateful-devops-python-d6fd66ddf
```

Before manual deletion, pods kept their old revisions:

```bash
stateful-devops-python-0 stateful-v1
stateful-devops-python-1 stateful-v1
stateful-devops-python-2 stateful-partition
```

After deleting only `pod-2`, it came back on the new template while the others still stayed old:

```bash
$ kubectl get pod stateful-devops-python-2 -n lab15 -o jsonpath='{.metadata.labels.controller-revision-hash} {.spec.containers[0].env[?(@.name=="DEPLOYMENT_TRACK")].value}{"\n"}'
stateful-devops-python-d6fd66ddf stateful-ondelete

$ for pod in 0 1 2; do
    printf 'stateful-devops-python-%s ' "$pod"
    kubectl get pod stateful-devops-python-$pod -n lab15 -o jsonpath='{.metadata.labels.controller-revision-hash} {.spec.containers[0].env[?(@.name=="DEPLOYMENT_TRACK")].value}{"\n"}'
  done
stateful-devops-python-0 stateful-devops-python-547bdd7848 stateful-v1
stateful-devops-python-1 stateful-devops-python-547bdd7848 stateful-v1
stateful-devops-python-2 stateful-devops-python-d6fd66ddf stateful-ondelete
```

This demonstrates the core use case for `OnDelete`: template changes do not restart pods until an operator deletes them intentionally.
