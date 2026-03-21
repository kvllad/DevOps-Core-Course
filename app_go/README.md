# DevOps Info Service (Go)

## Overview
Compiled version of the DevOps Info Service used for multi-stage Docker builds. Exposes `/` and `/health` endpoints.

## Prerequisites
- Go 1.21+

## Build
```bash
go mod tidy
go build -o devops-info-service .
```

## Run
```bash
./devops-info-service
# Or with custom config
PORT=9000 ./devops-info-service
HOST=127.0.0.1 PORT=9000 ./devops-info-service
```

## API Endpoints
- `GET /` - Service and system information
- `GET /health` - Health check

## Configuration
| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Port to listen on |
