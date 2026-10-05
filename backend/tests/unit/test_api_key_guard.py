import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings

client = TestClient(app)


def test_get_companies_works_without_key():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200


def test_get_discovery_health_works_without_key():
    response = client.get("/api/v1/discovery/health")
    assert response.status_code == 200


# Write endpoint 1: DELETE /api/v1/companies/{slug}
def test_delete_company_returns_401_without_key():
    response = client.delete("/api/v1/companies/test?confirm=test")
    assert response.status_code == 401


def test_delete_company_returns_401_with_wrong_key():
    response = client.delete(
        "/api/v1/companies/test?confirm=test",
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


# Write endpoint 2: POST /api/v1/discovery/resolve
def test_post_discovery_resolve_returns_401_without_key():
    response = client.post(
        "/api/v1/discovery/resolve",
        json={"company_name": "Test", "founder_names": ["Test"]}
    )
    assert response.status_code == 401


def test_post_discovery_resolve_returns_401_with_wrong_key():
    response = client.post(
        "/api/v1/discovery/resolve",
        headers={"X-API-Key": "invalid-key"},
        json={"company_name": "Test", "founder_names": ["Test"]}
    )
    assert response.status_code == 401


# Write endpoint 3: POST /api/v1/discovery/jobs
def test_post_discovery_jobs_returns_401_without_key():
    response = client.post(
        "/api/v1/discovery/jobs",
        json={"company_name": "Test", "founder_names": ["Test"]}
    )
    assert response.status_code == 401


def test_post_discovery_jobs_returns_401_with_wrong_key():
    response = client.post(
        "/api/v1/discovery/jobs",
        headers={"X-API-Key": "invalid-key"},
        json={"company_name": "Test", "founder_names": ["Test"]}
    )
    assert response.status_code == 401


# Write endpoint 4: POST /api/v1/reports/import
def test_post_reports_import_returns_401_without_key():
    response = client.post(
        "/api/v1/reports/import",
        json={"name": "test"}
    )
    assert response.status_code == 401


def test_post_reports_import_returns_401_with_wrong_key():
    response = client.post(
        "/api/v1/reports/import",
        headers={"X-API-Key": "invalid-key"},
        json={"name": "test"}
    )
    assert response.status_code == 401


# Production plain HTTP refusal vs HTTPS / localhost
def test_production_refuses_admin_over_plain_http_from_remote(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Valid key, but over plain HTTP from a public IP -> 403 Forbidden
    response = client.delete(
        "/api/v1/companies/test?confirm=test",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "http",
            "X-Forwarded-For": "203.0.113.195",
            "Host": "api.vset.example.com",
        }
    )
    assert response.status_code == 403
    assert "refused in production" in response.json().get("detail", "")


def test_production_permits_admin_over_https(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Valid key over HTTPS -> passes security guard (404 because company 'test' does not exist)
    response = client.delete(
        "/api/v1/companies/test?confirm=test",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-For": "203.0.113.195",
        }
    )
    # The auth/https guard passes, reaching application service which returns 404
    assert response.status_code == 404


def test_production_permits_admin_from_localhost_over_http(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Valid key from localhost via SSH tunnel -> passes guard
    response = client.delete(
        "/api/v1/companies/test?confirm=test",
        headers={
            "X-API-Key": settings.IMPORT_API_KEY,
            "X-Forwarded-Proto": "http",
            "X-Forwarded-For": "127.0.0.1",
            "Host": "localhost",
        }
    )
    assert response.status_code == 404

