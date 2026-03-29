"""DevOps Info Service (FastAPI)."""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


class JSONFormatter(logging.Formatter):
    """Render application logs as newline-delimited JSON for log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "event",
            "method",
            "path",
            "status_code",
            "client_ip",
            "duration_ms",
            "user_agent",
            "host",
            "port",
            "debug",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def _configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    logger_instance = logging.getLogger("devops-info-service")
    logger_instance.propagate = True
    return logger_instance


logger = _configure_logging()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

START_TIME = datetime.now(timezone.utc)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the service.",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of requests currently being processed.",
)
DEVOPS_INFO_ENDPOINT_CALLS_TOTAL = Counter(
    "devops_info_endpoint_calls_total",
    "Number of application endpoint invocations.",
    ["endpoint"],
)
DEVOPS_INFO_SYSTEM_INFO_COLLECTION_SECONDS = Histogram(
    "devops_info_system_info_collection_seconds",
    "Time spent collecting system information for the root endpoint.",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05),
)

app = FastAPI(
    title="DevOps Info Service",
    version="1.0.0",
    description="DevOps course info service",
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


def _normalize_endpoint(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    return request.url.path


def _record_http_metrics(request: Request, status_code: int, duration_seconds: float) -> None:
    endpoint = _normalize_endpoint(request)
    labels = {
        "method": request.method,
        "endpoint": endpoint,
        "status_code": str(status_code),
    }
    HTTP_REQUESTS_TOTAL.labels(**labels).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration_seconds)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    HTTP_REQUESTS_IN_PROGRESS.inc()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "Unhandled application error",
            extra={
                "event": "http_error",
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
                "duration_ms": duration_ms,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
        response = await internal_error(request, exc)
    finally:
        HTTP_REQUESTS_IN_PROGRESS.dec()

    duration_seconds = time.perf_counter() - start_time
    _record_http_metrics(request, response.status_code, duration_seconds)

    if response.status_code < 500:
        duration_ms = round(duration_seconds * 1000, 2)
        logger.info(
            "HTTP request processed",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
                "duration_ms": duration_ms,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )
    return response


@app.on_event("startup")
async def log_startup() -> None:
    logger.info(
        "Application startup complete",
        extra={
            "event": "startup",
            "host": HOST,
            "port": PORT,
            "debug": DEBUG,
        },
    )


@app.get("/")
async def index(request: Request) -> Dict[str, Any]:
    DEVOPS_INFO_ENDPOINT_CALLS_TOTAL.labels(endpoint="/").inc()
    uptime = _get_uptime()
    system_info_started = time.perf_counter()
    system = _get_system_info()
    DEVOPS_INFO_SYSTEM_INFO_COLLECTION_SECONDS.observe(
        time.perf_counter() - system_info_started
    )
    return {
        "service": {
            "name": "devops-info-service",
            "version": "1.0.0",
            "description": "DevOps course info service",
            "framework": "FastAPI",
        },
        "system": system,
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
                "path": "/error-test",
                "method": "GET",
                "description": "Intentional 500 for logging validation",
            },
            {
                "path": "/metrics",
                "method": "GET",
                "description": "Prometheus metrics endpoint",
            },
        ],
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    DEVOPS_INFO_ENDPOINT_CALLS_TOTAL.labels(endpoint="/health").inc()
    uptime = _get_uptime()
    return {
        "status": "healthy",
        "timestamp": _iso_utc_now(),
        "uptime_seconds": uptime["seconds"],
    }


@app.get("/error-test")
async def error_test() -> Dict[str, Any]:
    DEVOPS_INFO_ENDPOINT_CALLS_TOTAL.labels(endpoint="/error-test").inc()
    raise RuntimeError("Intentional lab error")


@app.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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

    logger.info(
        "Starting ASGI server",
        extra={
            "event": "startup",
            "host": HOST,
            "port": PORT,
            "debug": DEBUG,
        },
    )
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_config=None,
        access_log=False,
    )
