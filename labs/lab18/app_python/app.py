"""DevOps Info Service (FastAPI)."""
from __future__ import annotations

import logging
import os
import platform
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("devops-info-service")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
VISITS_FILE = Path(os.getenv("VISITS_FILE", "/data/visits"))
VISITS_LOCK_FILE = Path(os.getenv("VISITS_LOCK_FILE", f"{VISITS_FILE}.lock"))

START_TIME = datetime.now(timezone.utc)
VISITS_LOCK = Lock()
HTTP_REQUESTS_TOTAL = Counter(
    "devops_info_http_requests_total",
    "Total HTTP requests handled by the application.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "devops_info_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
VISITS_COUNT_GAUGE = Gauge(
    "devops_info_visits_count",
    "Current persisted visits counter value.",
)
APP_INFO_GAUGE = Gauge(
    "devops_info_build_info",
    "Static application metadata.",
    ["version", "framework", "environment", "deployment_track"],
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    visits = get_visits_count()
    VISITS_COUNT_GAUGE.set(visits)
    APP_INFO_GAUGE.labels(
        version="1.0.0",
        framework="FastAPI",
        environment=os.getenv("APP_ENV", ""),
        deployment_track=os.getenv("DEPLOYMENT_TRACK", ""),
    ).set(1)
    logger.info("Visits counter initialized at %s from %s", visits, VISITS_FILE)
    yield


app = FastAPI(
    title="DevOps Info Service",
    version="1.0.0",
    description="DevOps course info service",
    lifespan=lifespan,
)


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_uptime() -> Dict[str, Any]:
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {
        "seconds": seconds,
        "human": f"{hours} hours, {minutes} minutes",
    }


def _get_system_info() -> Dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.platform(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count() or 0,
        "python_version": platform.python_version(),
    }


def _read_visits_unlocked() -> int:
    try:
        raw_value = VISITS_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return 0

    if not raw_value:
        return 0

    try:
        return max(0, int(raw_value))
    except ValueError:
        logger.warning("Invalid visits counter value in %s; treating as 0", VISITS_FILE)
        return 0


def _write_visits_unlocked(count: int) -> None:
    VISITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = VISITS_FILE.with_name(f"{VISITS_FILE.name}.tmp")
    tmp_file.write_text(f"{count}\n", encoding="utf-8")
    os.replace(tmp_file, VISITS_FILE)


def _with_visits_lock(callback):
    import fcntl

    VISITS_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with VISITS_LOCK:
        with VISITS_LOCK_FILE.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                return callback()
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def get_visits_count() -> int:
    return _with_visits_lock(_read_visits_unlocked)


def increment_visits_count() -> int:
    def update_count() -> int:
        count = _read_visits_unlocked() + 1
        _write_visits_unlocked(count)
        return count

    return _with_visits_lock(update_count)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("Request: %s %s", request.method, request.url.path)
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=request.method,
        path=request.url.path,
    ).observe(duration)
    return response


@app.get("/")
async def index(request: Request) -> Dict[str, Any]:
    uptime = _get_uptime()
    visits = increment_visits_count()
    VISITS_COUNT_GAUGE.set(visits)
    return {
        "service": {
            "name": "devops-info-service",
            "version": "1.0.0",
            "description": "DevOps course info service",
            "framework": "FastAPI",
        },
        "deployment": {
            "track": os.getenv("DEPLOYMENT_TRACK", ""),
            "environment": os.getenv("APP_ENV", ""),
        },
        "system": _get_system_info(),
        "runtime": {
            "uptime_seconds": uptime["seconds"],
            "uptime_human": uptime["human"],
            "current_time": _iso_utc_now(),
            "timezone": "UTC",
        },
        "request": {
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "path": request.url.path,
        },
        "visits": {
            "count": visits,
            "storage_file": str(VISITS_FILE),
        },
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "description": "Service information",
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Health check",
            },
            {
                "path": "/visits",
                "method": "GET",
                "description": "Current root endpoint visit count",
            },
            {
                "path": "/metrics",
                "method": "GET",
                "description": "Prometheus metrics",
            },
        ],
    }


@app.get("/visits")
async def visits() -> Dict[str, Any]:
    count = get_visits_count()
    VISITS_COUNT_GAUGE.set(count)
    return {
        "count": count,
        "storage_file": str(VISITS_FILE),
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    uptime = _get_uptime()
    return {
        "status": "healthy",
        "timestamp": _iso_utc_now(),
        "uptime_seconds": uptime["seconds"],
    }


@app.get("/metrics")
async def metrics() -> Response:
    VISITS_COUNT_GAUGE.set(get_visits_count())
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(404)
async def not_found(_request: Request, _exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Not Found", "message": "Endpoint does not exist"},
    )


@app.exception_handler(500)
async def internal_error(_request: Request, _exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting app on %s:%s (debug=%s)", HOST, PORT, DEBUG)
    uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)
