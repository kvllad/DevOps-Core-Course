# Go Language Justification

## Why Go
- Compiled to a single static binary, perfect for containers
- Fast startup and low memory footprint
- Simple standard library for HTTP services

## Build Notes
```bash
go build -o devops-info-service .
```

## Binary Size (example)
- After build, compare size with Python app (your numbers will vary):
```bash
ls -lh devops-info-service
du -sh ../app_python
```

**Latest measurement:**
- Go binary: 7.6M
- Python app: 49M
