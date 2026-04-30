# Lab 17 — Cloudflare Workers Edge Deployment

Execution date: 2026-04-30

## Overview

Project directory:

- `labs/lab17/edge-api`

Main files:

- `labs/lab17/edge-api/src/index.ts`
- `labs/lab17/edge-api/wrangler.jsonc`
- `labs/lab17/edge-api/.dev.vars.example`
- `labs/lab17/edge-api/.gitignore`

Configured routes:

- `GET /` — app summary and route list
- `GET /health` — health check
- `GET /edge` — request metadata from the Workers edge runtime
- `GET /config` — plaintext vars and secret availability
- `GET /counter` — KV-backed visit counter
- `GET /kv/:key` — fetch arbitrary KV value
- `POST /kv/:key` — store arbitrary KV value

Configured plaintext vars in `wrangler.jsonc`:

- `APP_NAME`
- `COURSE_NAME`
- `APP_VERSION`

Secrets used in the Worker:

- `API_TOKEN`
- `ADMIN_EMAIL`

KV binding:

- `SETTINGS`

Worker URL:

- local dev: `http://127.0.0.1:8787`
- public `workers.dev`: `https://devops-edge-api.vladk6813.workers.dev`

## Local Run

Install dependencies:

```bash
cd labs/lab17/edge-api
npm install
```

Use local secret values for development:

```bash
cp .dev.vars.example .dev.vars
```

Run locally:

```bash
npm run dev
```

I used these local checks:

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/edge
curl http://127.0.0.1:8787/config
curl http://127.0.0.1:8787/counter
curl -X POST http://127.0.0.1:8787/kv/demo-<timestamp> -H 'content-type: application/json' -d '{"value":"fresh-value"}'
curl http://127.0.0.1:8787/kv/demo-<timestamp>
```

Verified responses:

```json
GET /health
{
  "status": "ok",
  "app": "devops-edge-api",
  "version": "v1",
  "timestamp": "2026-04-30T11:38:55.159Z"
}
```

```json
GET /edge
{
  "app": "devops-edge-api",
  "version": "v1",
  "edge": {
    "colo": "AMS",
    "country": "NL",
    "city": "Amsterdam",
    "asn": 216071,
    "httpProtocol": "HTTP/1.1",
    "tlsVersion": "TLSv1.3"
  }
}
```

```json
GET /config
{
  "app": "devops-edge-api",
  "course": "DevOps Core Course",
  "version": "v1",
  "usesPlaintextVars": true,
  "secretsAvailable": {
    "apiTokenConfigured": true,
    "adminEmailConfigured": true
  }
}
```

```json
GET /counter
{
  "visits": 6,
  "persistedIn": "Workers KV"
}
```

```json
POST /kv/demo-1777549170
{
  "key": "demo-1777549170",
  "value": "fresh-value",
  "stored": true
}

GET /kv/demo-1777549170
{
  "key": "demo-1777549170",
  "value": "fresh-value"
}
```

## Edge Behavior

The `/edge` route is designed to expose Cloudflare request metadata directly from `request.cf`, including:

- `colo`
- `country`
- `city`
- `asn`
- `httpProtocol`
- `tlsVersion`

Public `/edge` response during the second deployment (`APP_VERSION=v2`):

```json
{
  "app": "devops-edge-api",
  "version": "v2",
  "edge": {
    "colo": "AMS",
    "country": "NL",
    "city": "Amsterdam",
    "asn": 216071,
    "httpProtocol": "HTTP/2",
    "tlsVersion": "TLSv1.3"
  }
}
```

Workers runs code close to the incoming user. Unlike a VM or regional PaaS deployment, there is no separate step to deploy to multiple regions because Cloudflare handles global edge placement behind the same Worker version.

Routing summary:

- `workers.dev` gives a public Worker URL immediately.
- Routes attach a Worker to traffic on an existing Cloudflare-managed zone.
- Custom Domains let a Worker serve as origin for a chosen domain or subdomain.

## Configuration, Secrets, and Persistence

Plaintext vars are appropriate for non-sensitive configuration such as app name or course name because they are stored in config. They are not suitable for secrets because their values are visible in the Worker configuration and repository history.

Secrets must be created with Wrangler and are not committed:

```bash
npx wrangler secret put API_TOKEN
npx wrangler secret put ADMIN_EMAIL
```

KV namespace setup:

```bash
npx wrangler kv namespace create SETTINGS
```

After creating the namespace, the generated IDs need to be copied into `wrangler.jsonc`.

Real namespace IDs used in the deployment:

- `id`: `3b32eba33ed947608c6b3f0910680c24`
- `preview_id`: `c98834308ca942ae9f767967006f6430`

KV persistence verification across deploy and rollback:

1. On the public Worker with `APP_VERSION=v2`, `GET /counter` returned:

```json
{
  "visits": 2,
  "persistedIn": "Workers KV"
}
```

2. I also stored and fetched a public KV key through the deployed Worker:

```json
POST /kv/prod-demo-1777550027
{
  "key": "prod-demo-1777550027",
  "value": "public-value",
  "stored": true
}

GET /kv/prod-demo-1777550027
{
  "key": "prod-demo-1777550027",
  "value": "public-value"
}
```

3. I rolled the Worker back to the previous deployment.
4. After rollback, `GET /counter` returned:

```json
{
  "visits": 3,
  "persistedIn": "Workers KV"
}
```

The version changed back to `v1`, but the counter continued from the previous value, proving KV state survived the deployment change.

## Observability and Operations

The Worker logs each request with path and edge metadata using `console.log()`.

Local log sample from `wrangler dev`:

```text
request { method: 'GET', path: '/counter', colo: 'AMS', country: 'NL' }
request { method: 'POST', path: '/kv/demo-1777549170', colo: 'AMS', country: 'NL' }
request { method: 'GET', path: '/kv/demo-1777549170', colo: 'AMS', country: 'NL' }
```

Operational commands:

```bash
npx wrangler tail
npx wrangler deployments list
npx wrangler rollback
```

Production log sample from `wrangler tail`:

```text
GET https://devops-edge-api.vladk6813.workers.dev/health - Ok @ 4/30/2026, 2:53:10 PM
  (log) request { method: 'GET', path: '/health', colo: 'AMS', country: 'NL' }
GET https://devops-edge-api.vladk6813.workers.dev/counter - Ok @ 4/30/2026, 2:54:31 PM
  (log) request { method: 'GET', path: '/counter', colo: 'AMS', country: 'NL' }
```

Deployment history from `wrangler deployments list`:

- `d80aaf69-a386-4c70-9875-c4a1aae29d9c` deployed at `2026-04-30T11:48:54.436Z`
- `5e376d32-9d5c-4d0d-8a5b-faff5a3616ee` deployed at `2026-04-30T11:52:09.207Z`
- rollback deployment recorded at `2026-04-30T11:54:10.039Z` with message `rollback to v1 for lab17 verification`

Rollback verification:

```json
GET /health
{
  "status": "ok",
  "app": "devops-edge-api",
  "version": "v1",
  "timestamp": "2026-04-30T11:54:31.179Z"
}
```

Evidence files saved in the repo:

- `labs/lab17/evidence/edge-response.png`
- `labs/lab17/evidence/wrangler-tail.png`
- `labs/lab17/evidence/deployments-list.png`

## Kubernetes vs Cloudflare Workers Comparison

| Aspect | Kubernetes | Cloudflare Workers |
|--------|------------|--------------------|
| Setup complexity | Cluster, manifests, images, ingress, monitoring | Much lower for small HTTP APIs |
| Deployment speed | Slower, image build plus rollout | Very fast once Wrangler is configured |
| Global distribution | You choose and manage regions/clusters | Global edge handled by Cloudflare |
| Cost (for small apps) | Higher baseline operational cost | Usually lower for lightweight request-driven apps |
| State/persistence model | PVCs, databases, caches, operators | KV, Durable Objects, R2, D1 bindings |
| Control/flexibility | Maximum control over runtime and networking | More constrained runtime, less infra control |
| Best use case | Complex services, custom networking, long-running workloads | Lightweight APIs, edge logic, request transformation |

## When to Use Each

Prefer Kubernetes when:

- you need containers or custom runtimes
- you need long-running processes
- you need deep networking, storage, or operator control

Prefer Workers when:

- you need a fast global HTTP API
- latency to end users matters
- the app is request-driven and small enough for the runtime limits

My recommendation:

- use Workers for small public APIs, edge auth, redirects, personalization, and KV-backed lightweight state
- use Kubernetes for multi-service systems, background processing, databases, or workloads that assume a full Linux/container environment

## Reflection

What felt easier than Kubernetes:

- almost no deployment surface area
- no container registry, cluster bootstrap, or ingress work
- global routing is built in

What felt more constrained:

- no Docker host model
- platform bindings must be used for secrets and persistence
- runtime limits shape the design early

What changed because Workers is not a Docker host:

- the app had to be rewritten as a Workers-native fetch handler
- persistence moved from files/PVCs to Workers KV
- operational workflows shifted from `kubectl` and Helm to Wrangler and Cloudflare bindings

## Cloudflare Deployment Steps

The public deployment sequence I used:

1. `cd labs/lab17/edge-api`
2. `npm install`
3. `npx wrangler login`
4. `npx wrangler whoami`
5. `npx wrangler kv namespace create SETTINGS`
6. Replace the placeholder KV IDs in `wrangler.jsonc`
7. `npx wrangler secret put API_TOKEN`
8. `npx wrangler secret put ADMIN_EMAIL`
9. `npx wrangler deploy`
10. `npx wrangler tail`
11. `npx wrangler deployments list`
12. change `APP_VERSION` to `v2` and deploy again
13. `npx wrangler deployments list`
14. `npx wrangler rollback d80aaf69-a386-4c70-9875-c4a1aae29d9c -y -m 'rollback to v1 for lab17 verification'`
