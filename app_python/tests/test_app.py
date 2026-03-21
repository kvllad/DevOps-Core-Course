from __future__ import annotations


def test_root_structure(client):
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "service" in data
    assert "system" in data
    assert "runtime" in data
    assert "request" in data
    assert "endpoints" in data

    service = data["service"]
    assert service["name"] == "devops-info-service"
    assert service["framework"] == "FastAPI"

    runtime = data["runtime"]
    assert runtime["timezone"] == "UTC"
    assert isinstance(runtime["uptime_seconds"], int)

    endpoints = data["endpoints"]
    assert isinstance(endpoints, list)
    assert any(ep["path"] == "/" for ep in endpoints)
    assert any(ep["path"] == "/health" for ep in endpoints)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["uptime_seconds"], int)
    assert "timestamp" in data


def test_not_found(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404

    data = response.json()
    assert data["error"] == "Not Found"
    assert "message" in data


def test_metrics_endpoint(client):
    client.get("/")
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds_bucket" in body
    assert "http_requests_in_progress" in body
    assert "devops_info_endpoint_calls_total" in body
    assert 'endpoint="/"' in body
    assert 'endpoint="/health"' in body
