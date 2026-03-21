# LAB01 — DevOps Info Service (FastAPI)

## Framework Selection
**Chosen:** FastAPI

**Why:**
- Modern async framework with high performance
- Built-in OpenAPI/Swagger docs
- Type hints help keep the code clean and maintainable

**Comparison**
| Framework | Pros | Cons | Verdict |
|---|---|---|---|
| FastAPI | Async, auto-docs, type-friendly | Slightly more setup than Flask | **Selected** |
| Flask | Minimal and simple | Fewer batteries included | Not chosen |
| Django | Full-featured | Heavyweight for this task | Not chosen |

## Best Practices Applied
1. **Clean organization**
   - Separate helper functions for uptime/system info in `app_python/app.py`.

2. **PEP 8 / readability**
   - Clear naming, grouped imports, minimal comments.

3. **Error handling**
   - Custom handlers for 404 and 500 returning JSON.

4. **Logging**
   - Configured `logging.basicConfig` and request logging middleware.

**Code examples (from `app_python/app.py`):**
```python
@app.exception_handler(404)
async def not_found(_request: Request, _exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "message": "Endpoint does not exist"},
    )
```

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Request: %s %s", request.method, request.url.path)
    response = await call_next(request)
    return response
```

## API Documentation
### `GET /`
**Example request:**
```bash
curl -s http://127.0.0.1:5000/ | jq
```

**Example response (shape):**
```json
{
  "service": {"name": "devops-info-service", "version": "1.0.0"},
  "system": {"hostname": "...", "platform": "..."},
  "runtime": {"uptime_seconds": 123, "current_time": "..."},
  "request": {"client_ip": "127.0.0.1", "method": "GET"},
  "endpoints": [
    {"path": "/", "method": "GET"},
    {"path": "/health", "method": "GET"}
  ]
}
```

### `GET /health`
**Example request:**
```bash
curl -s http://127.0.0.1:5000/health | jq
```

**Example response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T00:00:00Z",
  "uptime_seconds": 123
}
```

## Testing Evidence
**Screenshots (replace placeholders with real screenshots):**
- `app_python/docs/screenshots/01-main-endpoint.png`
- `app_python/docs/screenshots/02-health-check.png`
- `app_python/docs/screenshots/03-formatted-output.png`

**Terminal output (sample):**
```text
INFO - Request: GET /
INFO - Request: GET /health
```

## Challenges & Solutions
- **Challenge:** Formatting uptime in a human-readable way.
  **Solution:** Calculated hours/minutes from total seconds in a helper function.

## GitHub Community
- Starring repositories helps signal useful projects, improves discoverability, and supports maintainers.
- Following developers helps track progress, learn from their work, and improve collaboration.

**Checklist (complete manually):**
- [ ] Starred course repo
- [ ] Starred `simple-container-com/api`
- [ ] Followed professor and TAs
- [ ] Followed at least 3 classmates
