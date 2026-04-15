# Lab 12 — ConfigMaps & Persistent Volumes

Execution date: 2026-04-15  
Cluster context: `kind-lab12`  
Namespace: `lab12`

## Application Changes

The FastAPI service now tracks root endpoint visits in a file-backed counter.

- `GET /` increments the visits counter and returns the current value in the response.
- `GET /visits` returns the current count without incrementing it.
- Counter storage is controlled by `VISITS_FILE`; default is `/data/visits`.
- File updates are protected by an in-process lock and `fcntl.flock`, then written atomically with `os.replace`.
- The Docker image creates `/data` and exposes it as a volume.

Local tests:

```bash
$ python3 -m pytest -q app_python/tests -c app_python/pytest.ini
4 passed in 0.06s
```

Docker Compose persistence evidence:

```bash
$ docker compose -f app_python/docker-compose.yml up --build -d
Container app_python-devops-info-service-1 Started

$ curl -s http://127.0.0.1:5000/ | python3 -m json.tool
"visits": {
    "count": 1,
    "storage_file": "/data/visits"
}

$ cat app_python/data/visits
1

$ docker compose -f app_python/docker-compose.yml restart devops-info-service
Container app_python-devops-info-service-1 Started

$ curl -s http://127.0.0.1:5000/visits | python3 -m json.tool
{
    "count": 1,
    "storage_file": "/data/visits"
}
```

## ConfigMap Implementation

Chart files added:

```text
k8s/devops-python/files/config.json
k8s/devops-python/templates/configmap.yaml
```

`config.json`:

```json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev"
  },
  "features": {
    "visitsCounter": true,
    "configHotReload": true
  },
  "settings": {
    "visitsFile": "/data/visits",
    "timezone": "UTC"
  }
}
```

The chart creates two ConfigMaps:

- `devops-python-config`: file-based ConfigMap loaded with `.Files.Get "files/config.json"`.
- `devops-python-env`: key-value ConfigMap injected with `envFrom.configMapRef`.

Mounted file and environment wiring:

```yaml
volumeMounts:
  - name: config-volume
    mountPath: /config
    readOnly: true
envFrom:
  - configMapRef:
      name: devops-python-env
```

Verification:

```bash
$ kubectl get configmap,pvc -n lab12
NAME                             DATA   AGE
configmap/devops-python-config   1      44s
configmap/devops-python-env      5      44s
configmap/kube-root-ca.crt       1      66s

NAME                                       STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/devops-python-data   Bound    pvc-2fdc4ea2-d0c0-4f51-ae1d-8c6a850d0b94   100Mi      RWO            standard
```

```bash
$ kubectl exec -n lab12 <pod> -c devops-python -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev"
  },
  "features": {
    "visitsCounter": true,
    "configHotReload": true
  },
  "settings": {
    "visitsFile": "/data/visits",
    "timezone": "UTC"
  }
}
```

```bash
$ kubectl exec -n lab12 <pod> -c devops-python -- \
  sh -c 'printenv | sort | grep -E "^(APP_NAME|APP_ENV|LOG_LEVEL|FEATURE_VISITS_COUNTER|VISITS_FILE|DEPLOYMENT_TRACK)="'
APP_ENV=dev
APP_NAME=devops-info-service
DEPLOYMENT_TRACK=dev
FEATURE_VISITS_COUNTER=true
LOG_LEVEL=debug
VISITS_FILE=/data/visits
```

## Persistent Volume

Chart file added:

```text
k8s/devops-python/templates/pvc.yaml
```

Values:

```yaml
persistence:
  enabled: true
  mountPath: /data
  accessModes:
    - ReadWriteOnce
  size: 100Mi
  storageClass: ""
```

`ReadWriteOnce` is appropriate for this single-writer counter. The empty storage class uses the cluster default; in `kind` this resolved to `standard`.

The Deployment mounts the PVC:

```yaml
volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: devops-python-data
volumeMounts:
  - name: data-volume
    mountPath: /data
```

Persistence test:

```bash
$ curl -s http://127.0.0.1:8080/visits | python3 -m json.tool
{
    "count": 2,
    "storage_file": "/data/visits"
}

$ kubectl exec -n lab12 <pod> -c devops-python -- cat /data/visits
2
```

Pod deletion and replacement:

```bash
$ kubectl delete pod -n lab12 devops-python-64494c85d9-v9np7
pod "devops-python-64494c85d9-v9np7" deleted

$ kubectl wait --for=condition=Ready pod -n lab12 \
  -l app.kubernetes.io/instance=devops-python --timeout=180s
pod/devops-python-64494c85d9-xbqkw condition met
```

Counter after new pod started:

```bash
$ kubectl exec -n lab12 devops-python-64494c85d9-xbqkw -c devops-python -- cat /data/visits
2

$ curl -s http://127.0.0.1:8080/visits | python3 -m json.tool
{
    "count": 2,
    "storage_file": "/data/visits"
}
```

## ConfigMap vs Secret

Use ConfigMaps for non-sensitive configuration:

- feature flags
- log levels
- app names
- endpoint URLs that are not credentials
- JSON/YAML/TOML configuration files

Use Secrets for sensitive data:

- passwords
- tokens
- private keys
- database credentials
- API keys

Key differences:

- ConfigMaps are plain configuration objects.
- Secrets are intended for sensitive data and can integrate with Secret-specific RBAC and encryption-at-rest controls.
- Neither should be treated as secure without appropriate RBAC; Secrets are still only base64-encoded in manifests unless encryption at rest is configured.

## Bonus — ConfigMap Hot Reload

### Default Mounted ConfigMap Update

The chart mounts the ConfigMap as a directory (`/config`), not with `subPath`, so Kubernetes can update the projected file.

Update test:

```bash
$ kubectl patch configmap -n lab12 devops-python-config --type merge -p '{"data":{"config.json":"... hot-reload ..."}}'
configmap/devops-python-config patched

$ kubectl exec -n lab12 <pod> -c devops-python -- grep -o 'hot-reload' /config/config.json
# immediate check: no output

$ kubectl exec -n lab12 <pod> -c devops-python -- grep -o 'hot-reload' /config/config.json
hot-reload
```

Measured delay:

```text
delay_seconds=41
mounted_value=hot-reload
```

Kubelet updates mounted ConfigMaps asynchronously. The delay depends on kubelet sync and cache behavior, and can take up to a few minutes.

### `subPath` Limitation

ConfigMap keys mounted with `subPath` do not receive live updates because Kubernetes bind-mounts a specific file copy into the container. Use a full ConfigMap directory mount when live updates matter. Use `subPath` only when a fixed file path is more important than receiving automatic updates.

### Reload Mechanism Implemented

The chart implements the checksum annotation rollout pattern:

```yaml
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

When Helm-rendered ConfigMap content changes, the pod template annotation changes. Kubernetes then creates a new ReplicaSet and restarts the pod.

Rollout evidence:

```bash
$ kubectl get deploy -n lab12 devops-python \
  -o go-template='{{ index .spec.template.metadata.annotations "checksum/config" }}{{ "\n" }}'
e18af3a6de1140132bd3a5114ba34791bd6580d1d4b93c5642e239615c6ab2ce

$ helm upgrade devops-python k8s/devops-python -n lab12 \
  -f k8s/devops-python/values-dev.yaml \
  --set image.repository=devops-info-service-py \
  --set image.pullPolicy=IfNotPresent \
  --set configMaps.env.data.LOG_LEVEL=warn \
  --wait

$ kubectl get rs,pods -n lab12 -l app.kubernetes.io/instance=devops-python
NAME                                       DESIRED   CURRENT   READY   AGE
replicaset.apps/devops-python-64494c85d9   0         0         0       3m56s
replicaset.apps/devops-python-cf4ff96d4    1         1         1       20s

NAME                                READY   STATUS    RESTARTS   AGE
pod/devops-python-cf4ff96d4-sp78x   1/1     Running   0          20s

$ kubectl exec -n lab12 devops-python-cf4ff96d4-sp78x -c devops-python -- printenv LOG_LEVEL
warn
```
