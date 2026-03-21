# LAB01 — DevOps Info Service (Go)

## Overview
This is the compiled-language version of the DevOps Info Service implemented in Go using `net/http`.

## Build & Run
```bash
go mod tidy
go build -o devops-info-service .
./devops-info-service
```

## API Examples
```bash
curl -s http://127.0.0.1:8080/ | jq
curl -s http://127.0.0.1:8080/health | jq
```

## JSON Structure Parity
The Go service matches the Python JSON structure for `/` and `/health`.

## Screenshots
- `app_go/docs/screenshots/01-main-endpoint.png`
- `app_go/docs/screenshots/02-health-check.png`
- `app_go/docs/screenshots/03-formatted-output.png`

## Binary Size Comparison
Record size after build and compare with the Python app:
```bash
ls -lh devops-info-service
# Python (venv example)
du -sh ../app_python
```

**Comparison notes:**
- Go binary size: 7.6M
- Python app size: 49M

## Challenges & Solutions
- **Challenge:** Matching Python JSON field names exactly.
  **Solution:** Used struct tags for explicit JSON keys.
