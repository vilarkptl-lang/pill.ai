"""
pill.ai License Server — deploy this on YOUR infrastructure.

Database:
  Set PILLAI_DB_URL to a SQLAlchemy connection URL.
  MySQL (production):  mysql+pymysql://user:pass@localhost/pillai
  SQLite  (local dev): sqlite:///license.db  ← default

Run with:
    uvicorn licensing.server:app --host 0.0.0.0 --port 8080

Protect the /admin endpoints with PILLAI_ADMIN_SECRET env var.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import Depends, FastAPI, HTTPException, Request, Header
    from pydantic import BaseModel
    from sqlalchemy import (
        Column, Integer, String, Text, create_engine, text
    )
    from sqlalchemy.orm import declarative_base, Session, sessionmaker
    HAS_SERVER_DEPS = True
except ImportError:
    HAS_SERVER_DEPS = False
    FastAPI = object  # type: ignore
    BaseModel = object  # type: ignore

ADMIN_SECRET = os.getenv("PILLAI_ADMIN_SECRET", "change-me-in-production")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# DB_URL: MySQL in prod, SQLite for local dev
_DB_PATH = os.getenv("PILLAI_DB", "license.db")
DB_URL = os.getenv("PILLAI_DB_URL", f"sqlite:///{_DB_PATH}")

# ── SQLAlchemy setup ─────────────────────────────────────────────────────────

Base = declarative_base()


class License(Base):
    __tablename__ = "licenses"
    key              = Column(String(64), primary_key=True)
    status           = Column(String(20), nullable=False, default="active")
    tier             = Column(String(20), nullable=False, default="free")
    email            = Column(String(255))
    owner_id         = Column(String(64))
    daily_call_limit = Column(Integer, default=100)
    features         = Column(Text, default="[]")
    message          = Column(Text, default="")
    expires_at       = Column(String(40))
    created_at       = Column(String(40), nullable=False)
    updated_at       = Column(String(40), nullable=False)


class Activation(Base):
    __tablename__ = "activations"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String(64), nullable=False)
    hw_id       = Column(String(128), nullable=False)
    install_id  = Column(String(128), nullable=False)
    platform    = Column(String(64))
    version     = Column(String(32))
    first_seen  = Column(String(40), nullable=False)
    last_seen   = Column(String(40), nullable=False)


class UsageLog(Base):
    __tablename__ = "usage_log"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    license_key = Column(String(64), nullable=False)
    hw_id       = Column(String(128), nullable=False)
    calls       = Column(Integer, default=1)
    ts          = Column(Integer, nullable=False)


class GlobalSetting(Base):
    __tablename__ = "global_settings"
    key   = Column(String(64), primary_key=True)
    value = Column(Text)


def _make_engine():
    is_mysql = DB_URL.startswith("mysql")
    if DB_URL == "sqlite:///:memory:":
        from sqlalchemy.pool import StaticPool
        return create_engine(
            DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    kwargs = {"pool_pre_ping": True} if is_mysql else {}
    return create_engine(DB_URL, **kwargs)


def _init_db(engine):
    Base.metadata.create_all(engine)
    # Seed default global settings
    with Session(engine) as s:
        for k, v in [("free_tier_enabled", "true"), ("free_daily_limit", "100")]:
            if not s.get(GlobalSetting, k):
                s.add(GlobalSetting(key=k, value=v))
        s.commit()


def _upsert_activation(s: Session, key: str, hw_id: str, install_id: str,
                       platform: str, version: str, now: str):
    row = s.query(Activation).filter_by(
        license_key=key, install_id=install_id
    ).first()
    if row:
        row.last_seen = now
        row.version = version
    else:
        s.add(Activation(
            license_key=key, hw_id=hw_id, install_id=install_id,
            platform=platform, version=version, first_seen=now, last_seen=now,
        ))


# ── FastAPI app ──────────────────────────────────────────────────────────────

if HAS_SERVER_DEPS:
    _engine = _make_engine()
    _init_db(_engine)
    _SessionLocal = sessionmaker(bind=_engine)

    app = FastAPI(title="pill.ai License Server", version="1.0.0")

    def _db() -> Session:
        return _SessionLocal()

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
        with _db() as s:
            free_setting = s.get(GlobalSetting, "free_tier_enabled")
            free_enabled = (free_setting.value == "true") if free_setting else True

            if req.key.upper() == "FREE":
                if not free_enabled:
                    return {"status": "free_disabled", "tier": "free",
                            "message": "Free tier is currently disabled. Visit https://pill.ai/pricing"}
                limit_setting = s.get(GlobalSetting, "free_daily_limit")
                free_limit = int(limit_setting.value) if limit_setting else 100
                return {"status": "active", "tier": "free",
                        "daily_call_limit": free_limit, "features": [], "message": ""}

            row = s.get(License, req.key.upper())
            if not row:
                return {"status": "invalid", "tier": "free", "message": "Unknown license key."}

            _upsert_activation(s, req.key.upper(), req.hw_id, req.install_id,
                               req.platform, req.version, now)
            s.commit()

            return {
                "status": row.status,
                "tier": row.tier,
                "email": row.email or "",
                "owner_id": row.owner_id or "",
                "daily_call_limit": row.daily_call_limit,
                "features": json.loads(row.features or "[]"),
                "message": row.message or "",
                "expires_at": row.expires_at,
            }

    class UsageRequest(BaseModel):
        key: str
        hw_id: str
        calls: int = 1
        ts: int = 0

    @app.post("/v1/usage")
    def report_usage(req: UsageRequest):
        with _db() as s:
            s.add(UsageLog(
                license_key=req.key.upper(),
                hw_id=req.hw_id,
                calls=req.calls,
                ts=req.ts or int(time.time()),
            ))
            s.commit()
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
        key = "PILLAI-" + "-".join(secrets.token_hex(3).upper() for _ in range(4))
        now = datetime.now(timezone.utc).isoformat()
        with _db() as s:
            s.add(License(
                key=key, status="active", tier=req.tier,
                email=req.email, owner_id=req.owner_id,
                daily_call_limit=req.daily_call_limit,
                features=json.dumps(req.features),
                message=req.message, expires_at=req.expires_at,
                created_at=now, updated_at=now,
            ))
            s.commit()
        return {"key": key}

    class UpdateKeyRequest(BaseModel):
        status: Optional[str] = None
        tier: Optional[str] = None
        daily_call_limit: Optional[int] = None
        message: Optional[str] = None
        features: Optional[list[str]] = None

    @app.patch("/admin/keys/{key}", dependencies=[Depends(_require_admin)])
    def update_key(key: str, req: UpdateKeyRequest):
        now = datetime.now(timezone.utc).isoformat()
        with _db() as s:
            row = s.get(License, key.upper())
            if not row:
                raise HTTPException(status_code=404, detail="Key not found")
            if req.status is not None:           row.status = req.status
            if req.tier is not None:             row.tier = req.tier
            if req.daily_call_limit is not None: row.daily_call_limit = req.daily_call_limit
            if req.message is not None:          row.message = req.message
            if req.features is not None:         row.features = json.dumps(req.features)
            row.updated_at = now
            s.commit()
        return {"ok": True}

    @app.delete("/admin/keys/{key}", dependencies=[Depends(_require_admin)])
    def revoke_key(key: str):
        now = datetime.now(timezone.utc).isoformat()
        with _db() as s:
            row = s.get(License, key.upper())
            if row:
                row.status = "revoked"
                row.updated_at = now
                s.commit()
        return {"ok": True}

    class GlobalSettingRequest(BaseModel):
        value: str

    @app.put("/admin/settings/{key}", dependencies=[Depends(_require_admin)])
    def set_global(key: str, req: GlobalSettingRequest):
        with _db() as s:
            row = s.get(GlobalSetting, key)
            if row:
                row.value = req.value
            else:
                s.add(GlobalSetting(key=key, value=req.value))
            s.commit()
        return {"ok": True}

    @app.get("/admin/keys", dependencies=[Depends(_require_admin)])
    def list_keys(limit: int = 100, offset: int = 0):
        with _db() as s:
            rows = s.query(License).order_by(License.created_at.desc())\
                     .limit(limit).offset(offset).all()
        return [
            {c.name: getattr(r, c.name) for c in License.__table__.columns}
            for r in rows
        ]

    @app.get("/admin/usage", dependencies=[Depends(_require_admin)])
    def usage_stats(key: Optional[str] = None):
        with _db() as s:
            if key:
                rows = s.query(UsageLog)\
                        .filter_by(license_key=key.upper())\
                        .order_by(UsageLog.ts.desc()).limit(500).all()
                return [
                    {c.name: getattr(r, c.name) for c in UsageLog.__table__.columns}
                    for r in rows
                ]
            else:
                rows = s.execute(text(
                    "SELECT license_key, SUM(calls) as total_calls, COUNT(*) as pings "
                    "FROM usage_log GROUP BY license_key ORDER BY total_calls DESC"
                )).fetchall()
                return [dict(r._mapping) for r in rows]

    @app.get("/admin/activations/{key}", dependencies=[Depends(_require_admin)])
    def list_activations(key: str):
        with _db() as s:
            rows = s.query(Activation)\
                    .filter_by(license_key=key.upper())\
                    .order_by(Activation.last_seen.desc()).all()
        return [
            {c.name: getattr(r, c.name) for c in Activation.__table__.columns}
            for r in rows
        ]

    # ── Stripe webhook ───────────────────────────────────────────────────────

    _STRIPE_TIER_MAP = {
        "starter":    ("starter",    1_000),
        "pro":        ("pro",        10_000),
        "enterprise": ("enterprise", -1),
    }

    @app.post("/webhooks/stripe")
    async def stripe_webhook(request: Request):
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(status_code=503, detail="Stripe webhook not configured")
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
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
        email      = subscription.get("customer_email") or ""
        metadata   = subscription.get("metadata", {})
        license_key = metadata.get("license_key", "").upper()
        tier_name  = metadata.get("pill_tier", "starter")
        tier, daily_limit = _STRIPE_TIER_MAP.get(tier_name, ("starter", 1_000))
        now = datetime.now(timezone.utc).isoformat()
        with _db() as s:
            row = s.get(License, license_key)
            if row:
                row.status = "active"
                row.tier = tier
                row.daily_call_limit = daily_limit
                row.updated_at = now
            else:
                new_key = license_key or "PILLAI-" + "-".join(
                    secrets.token_hex(3).upper() for _ in range(4)
                )
                s.add(License(
                    key=new_key, status="active", tier=tier,
                    email=email, daily_call_limit=daily_limit,
                    features="[]", message="", created_at=now, updated_at=now,
                ))
            s.commit()

    def _handle_subscription_cancelled(subscription: dict):
        license_key = subscription.get("metadata", {}).get("license_key", "").upper()
        if not license_key:
            return
        now = datetime.now(timezone.utc).isoformat()
        with _db() as s:
            row = s.get(License, license_key)
            if row:
                row.status = "suspended"
                row.tier = "free"
                row.daily_call_limit = 100
                row.updated_at = now
                s.commit()

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "pill.ai-license"}

    @app.get("/version")
    def version():
        """Latest client version info — polled by the .exe and Tauri Orb on startup."""
        latest = os.getenv("PILLAI_CLIENT_VERSION", "0.1.0")
        notes  = os.getenv("PILLAI_RELEASE_NOTES", "")
        base   = "https://github.com/vilarkptl-lang/pill.ai/releases/latest/download"
        return {
            "version":      latest,
            "notes":        notes,
            "download_url": {
                "win":   f"{base}/pillai.exe",
                "mac":   f"{base}/pillai-mac",
                "linux": f"{base}/pillai-linux",
            },
            "tauri_updater": f"{base}/latest.json",
        }

    # ── Relay endpoint ───────────────────────────────────────────────────────

    class RelayRequest(BaseModel):
        key: str
        hw_id: str
        messages: list
        task_hint: str = ""

    @app.post("/v1/relay")
    def relay(req: RelayRequest):
        """
        Proxy LLM calls through the owner's API keys.
        - Validates license (free tier always allowed)
        - Picks model automatically based on task complexity
        - Returns response text only — model name never sent to client
        """
        from licensing.relay import relay_complete

        # Validate license (reuse existing logic)
        with _db() as s:
            free_setting = s.get(GlobalSetting, "free_tier_enabled")
            free_enabled = (free_setting.value == "true") if free_setting else True

            if req.key.upper() == "FREE":
                if not free_enabled:
                    raise HTTPException(status_code=403, detail="Free tier disabled")
            else:
                row = s.get(License, req.key.upper())
                if not row or row.status not in ("active",):
                    raise HTTPException(status_code=403, detail="Invalid or inactive license")

                # Rate limiting: check daily usage
                limit_setting = s.get(GlobalSetting, "free_daily_limit")
                limit = row.daily_call_limit
                if limit > 0:
                    import time
                    day_start = int(time.time()) - 86_400
                    usage_today = s.query(UsageLog).filter(
                        UsageLog.license_key == req.key.upper(),
                        UsageLog.ts >= day_start,
                    ).with_entities(__import__("sqlalchemy").func.sum(UsageLog.calls)).scalar() or 0
                    if usage_today >= limit:
                        raise HTTPException(status_code=429, detail="Daily call limit reached")

        # Call LLM with server-side keys — response only, no model info
        content = relay_complete(req.messages, req.task_hint)

        # Log usage
        import time
        with _db() as s:
            s.add(UsageLog(
                license_key=req.key.upper(),
                hw_id=req.hw_id,
                calls=1,
                ts=int(time.time()),
            ))
            s.commit()

        return {"content": content}
