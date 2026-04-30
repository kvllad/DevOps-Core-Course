from __future__ import annotations


def test_root_structure(client):
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "service" in data
    assert "deployment" in data
    assert "system" in data
    assert "runtime" in data
    assert "request" in data
    assert "visits" in data
    assert "endpoints" in data

    service = data["service"]
    assert service["name"] == "devops-info-service"
    assert service["framework"] == "FastAPI"

    deployment = data["deployment"]
    assert isinstance(deployment["track"], str)
    assert isinstance(deployment["environment"], str)

    runtime = data["runtime"]
    assert runtime["timezone"] == "UTC"
    assert isinstance(runtime["uptime_seconds"], int)

    endpoints = data["endpoints"]
    assert isinstance(endpoints, list)
    assert any(ep["path"] == "/" for ep in endpoints)
    assert any(ep["path"] == "/health" for ep in endpoints)
    assert any(ep["path"] == "/visits" for ep in endpoints)
    assert any(ep["path"] == "/metrics" for ep in endpoints)


def test_visits_counter_persists_to_file(client):
    assert client.get("/visits").json()["count"] == 0

    first = client.get("/")
    second = client.get("/")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["visits"]["count"] == 1
    assert second.json()["visits"]["count"] == 2
    assert client.get("/visits").json()["count"] == 2


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data["uptime_seconds"], int)
    assert "timestamp" in data


def test_metrics_endpoint(client):
    client.get("/")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "devops_info_http_requests_total" in body
    assert "devops_info_visits_count" in body


def test_not_found(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404

    data = response.json()
    assert data["error"] == "Not Found"
    assert "message" in data
