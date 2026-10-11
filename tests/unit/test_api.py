"""
BugHunter — API endpoint tests
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_validate_url_valid():
    response = client.post("/api/validate-url", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_url_invalid():
    response = client.post("/api/validate-url", json={"url": "ftp://bad-scheme"})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "error" in data
