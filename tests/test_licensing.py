"""
Tests for the licensing system.

Uses SQLite in-memory so no MySQL / network needed.
All tests are offline-safe.
"""
from __future__ import annotations

import os
import sys

import pytest

# ── Force SQLite in-memory for all tests ────────────────────────────────────
os.environ.setdefault("PILLAI_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("PILLAI_ADMIN_SECRET", "test-secret")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient backed by an in-memory SQLite DB."""
    pytest.importorskip("fastapi", reason="fastapi not installed")
    pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
    from fastapi.testclient import TestClient

    # Re-import server fresh so _init_db() runs against in-memory DB
    if "licensing.server" in sys.modules:
        del sys.modules["licensing.server"]
    from licensing.server import app
    return TestClient(app)


@pytest.fixture
def admin_headers():
    return {"x-admin-secret": "test-secret"}


# ── /health ──────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Free tier ────────────────────────────────────────────────────────────────

def test_free_tier_validate(client):
    r = client.post("/v1/validate", json={
        "key": "FREE", "hw_id": "hw-1", "install_id": "inst-1"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "active"
    assert data["tier"] == "free"
    assert data["daily_call_limit"] > 0


def test_free_tier_case_insensitive(client):
    r = client.post("/v1/validate", json={
        "key": "free", "hw_id": "hw-1", "install_id": "inst-1"
    })
    assert r.json()["tier"] == "free"


def test_unknown_key_returns_invalid(client):
    r = client.post("/v1/validate", json={
        "key": "PILLAI-FAKE-KEY-XXXX", "hw_id": "hw-1", "install_id": "inst-1"
    })
    assert r.json()["status"] == "invalid"


# ── Admin: create key ────────────────────────────────────────────────────────

def test_create_key(client, admin_headers):
    r = client.post("/admin/keys", json={
        "email": "test@example.com", "tier": "starter", "daily_call_limit": 1000
    }, headers=admin_headers)
    assert r.status_code == 200
    key = r.json()["key"]
    assert key.startswith("PILLAI-")
    return key


def test_create_key_forbidden_without_secret(client):
    r = client.post("/admin/keys", json={
        "email": "x@y.com", "tier": "free", "daily_call_limit": 100
    }, headers={"x-admin-secret": "wrong"})
    assert r.status_code == 403


# ── Validate real key ────────────────────────────────────────────────────────

def test_validate_real_key(client, admin_headers):
    # Create
    key = client.post("/admin/keys", json={
        "email": "user@pill.ai", "tier": "pro", "daily_call_limit": 10_000
    }, headers=admin_headers).json()["key"]

    # Validate
    r = client.post("/v1/validate", json={
        "key": key, "hw_id": "hw-abc", "install_id": "inst-abc",
        "version": "0.1.0", "platform": "linux"
    })
    data = r.json()
    assert data["status"] == "active"
    assert data["tier"] == "pro"
    assert data["daily_call_limit"] == 10_000
    assert data["email"] == "user@pill.ai"


# ── Update key ───────────────────────────────────────────────────────────────

def test_update_key_tier(client, admin_headers):
    key = client.post("/admin/keys", json={
        "email": "upgrade@pill.ai", "tier": "starter", "daily_call_limit": 1000
    }, headers=admin_headers).json()["key"]

    client.patch(f"/admin/keys/{key}", json={
        "tier": "pro", "daily_call_limit": 10_000
    }, headers=admin_headers)

    r = client.post("/v1/validate", json={
        "key": key, "hw_id": "hw-x", "install_id": "inst-x"
    })
    assert r.json()["tier"] == "pro"


# ── Revoke key ───────────────────────────────────────────────────────────────

def test_revoke_key(client, admin_headers):
    key = client.post("/admin/keys", json={
        "email": "revoke@pill.ai", "tier": "starter", "daily_call_limit": 1000
    }, headers=admin_headers).json()["key"]

    client.delete(f"/admin/keys/{key}", headers=admin_headers)

    r = client.post("/v1/validate", json={
        "key": key, "hw_id": "hw-r", "install_id": "inst-r"
    })
    assert r.json()["status"] == "revoked"


# ── Usage reporting ──────────────────────────────────────────────────────────

def test_report_usage(client, admin_headers):
    key = client.post("/admin/keys", json={
        "email": "usage@pill.ai", "tier": "starter", "daily_call_limit": 1000
    }, headers=admin_headers).json()["key"]

    r = client.post("/v1/usage", json={"key": key, "hw_id": "hw-u", "calls": 3})
    assert r.json()["ok"] is True

    stats = client.get("/admin/usage", params={"key": key}, headers=admin_headers)
    assert stats.status_code == 200
    total = sum(row["calls"] for row in stats.json())
    assert total == 3


# ── Global settings ──────────────────────────────────────────────────────────

def test_disable_free_tier(client, admin_headers):
    client.put("/admin/settings/free_tier_enabled", json={"value": "false"},
               headers=admin_headers)
    r = client.post("/v1/validate", json={
        "key": "FREE", "hw_id": "hw-f", "install_id": "inst-f"
    })
    assert r.json()["status"] == "free_disabled"

    # Re-enable for other tests
    client.put("/admin/settings/free_tier_enabled", json={"value": "true"},
               headers=admin_headers)


def test_change_free_daily_limit(client, admin_headers):
    client.put("/admin/settings/free_daily_limit", json={"value": "50"},
               headers=admin_headers)
    r = client.post("/v1/validate", json={
        "key": "FREE", "hw_id": "hw-l", "install_id": "inst-l"
    })
    assert r.json()["daily_call_limit"] == 50

    # Restore
    client.put("/admin/settings/free_daily_limit", json={"value": "100"},
               headers=admin_headers)


# ── List keys ────────────────────────────────────────────────────────────────

def test_list_keys(client, admin_headers):
    r = client.get("/admin/keys", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Activation dedup ─────────────────────────────────────────────────────────

def test_activation_upsert(client, admin_headers):
    """Same install_id validates twice — should not duplicate rows."""
    key = client.post("/admin/keys", json={
        "email": "act@pill.ai", "tier": "starter", "daily_call_limit": 1000
    }, headers=admin_headers).json()["key"]

    payload = {"key": key, "hw_id": "hw-dup", "install_id": "inst-dup"}
    client.post("/v1/validate", json=payload)
    client.post("/v1/validate", json=payload)

    r = client.get(f"/admin/activations/{key}", headers=admin_headers)
    assert len(r.json()) == 1  # dedup worked
