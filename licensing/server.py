"""
pill.ai License Server — deploy this on YOUR infrastructure.

This is the control plane. You (the owner) use it to:
  - Issue license keys
  - Suspend / revoke keys
  - Disable the free tier globally
  - Set per-key call limits and feature flags
  - View usage analytics

Run with:
    uvicorn licensing.server:app --host 0.0.0.0 --port 8080

Protect the /admin endpoints with PILLAI_ADMIN_SECRET env var.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import Depends, FastAPI, HTTPException, Request, Header
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import sqlite3
    HAS_SERVER_DEPS = True
except ImportError:
    HAS_SERVER_DEPS = False
    # Graceful degradation — server deps only needed when hosting the server
    FastAPI = object  # type: ignore
    BaseModel = object  # type: ignore

ADMIN_SECRET = os.getenv("PILLAI_ADMIN_SECRET", "change-me-in-production")
DB_PATH = os.getenv("PILLAI_DB", "license.db")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ── Database ────────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    with _db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'active',
            tier TEXT NOT NULL DEFAULT 'free',
            email TEXT,
            owner_id TEXT,
            daily_call_limit INTEGER DEFAULT 100,
            features TEXT DEFAULT '[]',
            message TEXT DEFAULT '',
            expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            hw_id TEXT NOT NULL,
            install_id TEXT NOT NULL,
            platform TEXT,
            version TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(license_key, install_id)
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            hw_id TEXT NOT NULL,
            calls INTEGER DEFAULT 1,
            ts INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS global_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        INSERT OR IGNORE INTO global_settings VALUES ('free_tier_enabled', 'true');
        INSERT OR IGNORE INTO global_settings VALUES ('free_daily_limit', '100');
        """)


# ── FastAPI app ─────────────────────────────────────────────────────────────

if HAS_SERVER_DEPS:
    app = FastAPI(title="pill.ai License Server", version="1.0.0")
    _init_db()

    # ── Auth helper ─────────────────────────────────────────────────────────

    def _require_admin(x_admin_secret: str = Header(...)):
        if not hmac.compare_digest(x_admin_secret, ADMIN_SECRET):
            raise HTTPException(status_code=403, detail="Forbidden")

    # ── Public endpoints ─────────────────────────────────────────────────────

    class ValidateRequest(BaseModel):
        key: str
        hw_id: str
        install_id: str
        version: str = ""
        platform: str = ""
        ts: int = 0

    @app.post("/v1/validate")
    def validate(req: ValidateRequest):
        now = datetime.now(timezone.utc).isoformat()
        with _db() as conn:
            # Check free tier global switch
            free_enabled = conn.execute(
                "SELECT value FROM global_settings WHERE key='free_tier_enabled'"
            ).fetchone()["value"] == "true"

            row = conn.execute(
                "SELECT * FROM licenses WHERE key=?", (req.key.upper(),)
            ).fetchone()

            if req.key.upper() == "FREE":
                if not free_enabled:
                    return {"status": "free_disabled", "tier": "free",
                            "message": "Free tier is currently disabled. Visit https://pill.ai/pricing"}
                free_limit = int(conn.execute(
                    "SELECT value FROM global_settings WHERE key='free_daily_limit'"
                ).fetchone()["value"])
                return {
                    "status": "active",
                    "tier": "free",
                    "daily_call_limit": free_limit,
                    "features": [],
                    "message": "",
                }

            if not row:
                return {"status": "invalid", "tier": "free", "message": "Unknown license key."}

            # Upsert activation record
            conn.execute("""
                INSERT INTO activations (license_key, hw_id, install_id, platform, version, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(license_key, install_id) DO UPDATE SET last_seen=excluded.last_seen, version=excluded.version
            """, (req.key.upper(), req.hw_id, req.install_id, req.platform, req.version, now, now))

            import json
            return {
                "status": row["status"],
                "tier": row["tier"],
                "email": row["email"] or "",
                "owner_id": row["owner_id"] or "",
                "daily_call_limit": row["daily_call_limit"],
                "features": json.loads(row["features"] or "[]"),
                "message": row["message"] or "",
                "expires_at": row["expires_at"],
            }

    class UsageRequest(BaseModel):
        key: str
        hw_id: str
        calls: int = 1
        ts: int = 0

    @app.post("/v1/usage")
    def report_usage(req: UsageRequest):
        with _db() as conn:
            conn.execute(
                "INSERT INTO usage_log (license_key, hw_id, calls, ts) VALUES (?,?,?,?)",
                (req.key.upper(), req.hw_id, req.calls, req.ts or int(time.time())),
            )
        return {"ok": True}

    # ── Admin endpoints ──────────────────────────────────────────────────────

    class CreateKeyRequest(BaseModel):
        email: str
        tier: str = "free"
        daily_call_limit: int = 100
        features: list[str] = []
        expires_at: Optional[str] = None
        owner_id: str = ""
        message: str = ""

    @app.post("/admin/keys", dependencies=[Depends(_require_admin)])
    def create_key(req: CreateKeyRequest):
        import json
        key = "PILLAI-" + "-".join(
            secrets.token_hex(3).upper() for _ in range(4)
        )
        now = datetime.now(timezone.utc).isoformat()
        with _db() as conn:
            conn.execute("""
                INSERT INTO licenses (key, status, tier, email, owner_id, daily_call_limit,
                    features, message, expires_at, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (key, "active", req.tier, req.email, req.owner_id,
                  req.daily_call_limit, json.dumps(req.features),
                  req.message, req.expires_at, now, now))
        return {"key": key}

    class UpdateKeyRequest(BaseModel):
        status: Optional[str] = None
        tier: Optional[str] = None
        daily_call_limit: Optional[int] = None
        message: Optional[str] = None
        features: Optional[list[str]] = None

    @app.patch("/admin/keys/{key}", dependencies=[Depends(_require_admin)])
    def update_key(key: str, req: UpdateKeyRequest):
        import json
        now = datetime.now(timezone.utc).isoformat()
        updates = {k: v for k, v in req.dict().items() if v is not None}
        if "features" in updates:
            updates["features"] = json.dumps(updates["features"])
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k}=?" for k in updates)
        with _db() as conn:
            conn.execute(
                f"UPDATE licenses SET {set_clause} WHERE key=?",
                list(updates.values()) + [key.upper()],
            )
        return {"ok": True}

    @app.delete("/admin/keys/{key}", dependencies=[Depends(_require_admin)])
    def revoke_key(key: str):
        """Permanently revoke a license key."""
        now = datetime.now(timezone.utc).isoformat()
        with _db() as conn:
            conn.execute(
                "UPDATE licenses SET status='revoked', updated_at=? WHERE key=?",
                (now, key.upper()),
            )
        return {"ok": True}

    class GlobalSettingRequest(BaseModel):
        value: str

    @app.put("/admin/settings/{key}", dependencies=[Depends(_require_admin)])
    def set_global(key: str, req: GlobalSettingRequest):
        """
        Key settings:
          free_tier_enabled = true|false   → disable free tier for everyone
          free_daily_limit  = 100          → change free tier call limit
        """
        with _db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO global_settings (key, value) VALUES (?,?)",
                (key, req.value),
            )
        return {"ok": True}

    @app.get("/admin/keys", dependencies=[Depends(_require_admin)])
    def list_keys(limit: int = 100, offset: int = 0):
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM licenses ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    @app.get("/admin/usage", dependencies=[Depends(_require_admin)])
    def usage_stats(key: Optional[str] = None):
        with _db() as conn:
            if key:
                rows = conn.execute(
                    "SELECT * FROM usage_log WHERE license_key=? ORDER BY ts DESC LIMIT 500",
                    (key.upper(),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT license_key, SUM(calls) as total_calls, COUNT(*) as pings "
                    "FROM usage_log GROUP BY license_key ORDER BY total_calls DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    @app.get("/admin/activations/{key}", dependencies=[Depends(_require_admin)])
    def list_activations(key: str):
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM activations WHERE license_key=? ORDER BY last_seen DESC",
                (key.upper(),),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Stripe webhook ───────────────────────────────────────────────────────

    # Tier mapping: Stripe price IDs → pill.ai tiers
    _STRIPE_TIER_MAP = {
        "starter": ("starter", 1_000),
        "pro":     ("pro",     10_000),
        "enterprise": ("enterprise", -1),
    }

    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        """
        Receive Stripe events and update license tiers automatically.
        Signature is verified with STRIPE_WEBHOOK_SECRET before any processing.
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(status_code=503, detail="Stripe webhook not configured")

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        # Verify signature — prevents anyone from forging activation requests
        try:
            import stripe as stripe_lib
            event = stripe_lib.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            _handle_subscription_active(data)
        elif event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
            _handle_subscription_cancelled(data)

        return {"ok": True}

    def _handle_subscription_active(subscription: dict):
        import json
        email = subscription.get("customer_email") or ""
        metadata = subscription.get("metadata", {})
        license_key = metadata.get("license_key", "").upper()
        tier_name = metadata.get("pill_tier", "starter")

        tier, daily_limit = _STRIPE_TIER_MAP.get(tier_name, ("starter", 1_000))
        now = datetime.now(timezone.utc).isoformat()

        with _db() as conn:
            existing = conn.execute(
                "SELECT key FROM licenses WHERE key=?", (license_key,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE licenses SET status='active', tier=?, daily_call_limit=?, updated_at=? WHERE key=?",
                    (tier, daily_limit, now, license_key),
                )
            else:
                # Auto-create key on first subscription if not pre-issued
                new_key = license_key or "PILLAI-" + "-".join(
                    secrets.token_hex(3).upper() for _ in range(4)
                )
                conn.execute("""
                    INSERT OR IGNORE INTO licenses
                    (key, status, tier, email, daily_call_limit, features, message, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (new_key, "active", tier, email, daily_limit, "[]", "", now, now))

    def _handle_subscription_cancelled(subscription: dict):
        metadata = subscription.get("metadata", {})
        license_key = metadata.get("license_key", "").upper()
        if not license_key:
            return
        now = datetime.now(timezone.utc).isoformat()
        with _db() as conn:
            conn.execute(
                "UPDATE licenses SET status='suspended', tier='free', daily_call_limit=100, updated_at=? WHERE key=?",
                (now, license_key),
            )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "pill.ai-license"}
