from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure app_python is on the import path for tests
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import app as app_module  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture(autouse=True)
def visits_file(tmp_path, monkeypatch) -> None:
    visits_path = tmp_path / "visits"
    monkeypatch.setattr(app_module, "VISITS_FILE", visits_path)
    monkeypatch.setattr(app_module, "VISITS_LOCK_FILE", tmp_path / "visits.lock")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
