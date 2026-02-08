# Lab 2 — Docker Containerization (Go, Multi-Stage)

## Multi-Stage Build Strategy
- **Stage 1 (builder)**: `golang:1.22.5-alpine` compiles a static Linux binary with `CGO_ENABLED=0`.
- **Stage 2 (runtime)**: `alpine:3.20` copies only the compiled binary. No Go toolchain in final image.

**Why it matters**
- The builder image includes compilers and caches and is large.
- The runtime image is much smaller, faster to pull, and has a reduced attack surface.

**Dockerfile snippets**
```dockerfile
FROM golang:1.22.5-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o /out/devops-info-service ./main.go

FROM alpine:3.20
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=builder /out/devops-info-service /app/devops-info-service
USER app
```

## Image Sizes (Builder vs Final)
**Builder image**
```
IMAGE                            ID             DISK USAGE   CONTENT SIZE   EXTRA
devops-info-service-go:builder   505b59753a16        440MB         89.1MB
```

**Final runtime image**
```
IMAGE                          ID             DISK USAGE   CONTENT SIZE   EXTRA
devops-info-service-go:lab02   4141ff429b1e       20.8MB         6.25MB
```

**Size reduction**
- ~419MB disk usage reduction from builder to runtime.
- Only the compiled binary is shipped in the final image.

## Build & Run Process
**Final image build output**
```
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/

Sending build context to Docker daemon   12.8kB
Step 1/13 : FROM golang:1.22.5-alpine AS builder
1.22.5-alpine: Pulling from library/golang
4f4fb700ef54: Pulling fs layer
690e87867337: Pulling fs layer
39127310aef1: Pulling fs layer
ad54470edeac: Pulling fs layer
cd18ca2ee675: Pulling fs layer
4f4fb700ef54: Download complete
cd18ca2ee675: Download complete
690e87867337: Download complete
39127310aef1: Download complete
ad54470edeac: Download complete
ad54470edeac: Pull complete
4f4fb700ef54: Pull complete
cd18ca2ee675: Pull complete
Digest: sha256:0d3653dd6f35159ec6e3d10263a42372f6f194c3dea0b35235d72aabde86486e
Status: Downloaded newer image for golang:1.22.5-alpine
 ---> 0d3653dd6f35
Step 2/13 : WORKDIR /src
 ---> Running in f5ba1c58c397
 ---> Removed intermediate container f5ba1c58c397
 ---> bb30b78e956c
Step 3/13 : COPY go.mod ./
 ---> 9afac6e4e39e
Step 4/13 : RUN go mod download
 ---> Running in 200bead6a73b
go: no module dependencies to download
 ---> Removed intermediate container 200bead6a73b
 ---> acb2affe6f1d
Step 5/13 : COPY . ./
 ---> 1d908df36856
Step 6/13 : RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64     go build -trimpath -ldflags="-s -w" -o /out/devops-info-service ./main.go
 ---> Running in cd3b5a362181
 ---> Removed intermediate container cd3b5a362181
 ---> 505b59753a16
Step 7/13 : FROM alpine:3.20
3.20: Pulling from library/alpine
83b2d7e29698: Pulling fs layer
83b2d7e29698: Download complete
83b2d7e29698: Pull complete
Digest: sha256:a4f4213abb84c497377b8544c81b3564f313746700372ec4fe84653e4fb03805
Status: Downloaded newer image for alpine:3.20
 ---> a4f4213abb84
Step 8/13 : RUN addgroup -S app && adduser -S -G app app
 ---> Running in 3f64620207ac
 ---> Removed intermediate container 3f64620207ac
 ---> e39a3e7fe41e
Step 9/13 : WORKDIR /app
 ---> Running in 69c5ea5f4f81
 ---> Removed intermediate container 69c5ea5f4f81
 ---> 576249d3d084
Step 10/13 : COPY --from=builder /out/devops-info-service /app/devops-info-service
 ---> 60b91184dfff
Step 11/13 : USER app
 ---> Running in 3efdf794f6a2
 ---> Removed intermediate container 3efdf794f6a2
 ---> 4e867070e086
Step 12/13 : EXPOSE 8080
 ---> Running in 4643074f0dd1
 ---> Removed intermediate container 4643074f0dd1
 ---> 96b364f82e76
Step 13/13 : CMD ["/app/devops-info-service"]
 ---> Running in 354487fc894b
 ---> Removed intermediate container 354487fc894b
 ---> 4141ff429b1e
Successfully built 4141ff429b1e
Successfully tagged devops-info-service-go:lab02
```

**Builder-only build output**
```
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/

Sending build context to Docker daemon   12.8kB
Step 1/6 : FROM golang:1.22.5-alpine AS builder
 ---> 0d3653dd6f35
Step 2/6 : WORKDIR /src
 ---> Using cache
 ---> bb30b78e956c
Step 3/6 : COPY go.mod ./
 ---> Using cache
 ---> 9afac6e4e39e
Step 4/6 : RUN go mod download
 ---> Using cache
 ---> acb2affe6f1d
Step 5/6 : COPY . ./
 ---> Using cache
 ---> 1d908df36856
Step 6/6 : RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64     go build -trimpath -ldflags="-s -w" -o /out/devops-info-service ./main.go
 ---> Using cache
 ---> 505b59753a16
Successfully built 505b59753a16
Successfully tagged devops-info-service-go:builder
```

**Run output**
```
$ docker run -d --name devops-info-go -p 8080:8080 devops-info-service-go:lab02
1f56942c21d32b28551fa4a130682b1f6a545fbebae6bb1b31244d9d4996daf5

$ docker ps --filter name=devops-info-go
CONTAINER ID   IMAGE                          COMMAND                  CREATED         STATUS         PORTS                                         NAMES
1f56942c21d3   devops-info-service-go:lab02   "/app/devops-info-se…"   2 seconds ago   Up 3 seconds   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp   devops-info-go
```

**Endpoint tests (inside container)**
```
$ docker exec devops-info-go wget -qO- http://127.0.0.1:8080/health
{"status":"healthy","timestamp":"2026-02-08T11:21:26Z","uptime_seconds":6}

$ docker exec devops-info-go wget -qO- http://127.0.0.1:8080/ | head -c 300
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"Go net/http"},"system":{"hostname":"1f56942c21d3","platform":"linux","platform_version":"Alpine Linux v3.20","architecture":"amd64","cpu_count":2,"python_version":"go1.22.5"},"runtime":
```

## Technical Notes
- **Static binary**: `CGO_ENABLED=0` allows running on minimal images without libc.
- **Non-root user**: runtime runs as `app` to avoid root privileges.
- **Trade-offs**: Alpine is small but uses musl; for maximum compatibility, a distroless or Debian-slim runtime could be used with a dynamically linked binary.

## Security Benefits
- Smaller runtime image means fewer packages and a smaller attack surface.
- No compilers or build tools in the final container.

