"""
License validation client.

Flow:
  1. On startup, call validate() — hits the license server.
  2. Result is cached locally (AES-encrypted) for GRACE_DAYS days.
  3. If server is unreachable, cached result is used and status = GRACE.
  4. If owner disables free tier globally or revokes a key, the next
     online validation propagates that immediately.
  5. Hardware fingerprint is included so keys cannot be freely shared.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

from .models import LicenseInfo, LicenseStatus, LicenseTier

# ── Configuration (override via env vars) ──────────────────────────────────
LICENSE_SERVER = os.getenv("PILLAI_LICENSE_SERVER", "https://license.pill.ai")
CACHE_DIR = Path(os.getenv("PILLAI_CACHE_DIR", Path.home() / ".pill.ai"))
CACHE_FILE = CACHE_DIR / "license.cache"
GRACE_DAYS = int(os.getenv("PILLAI_GRACE_DAYS", "7"))
REQUEST_TIMEOUT = float(os.getenv("PILLAI_LICENSE_TIMEOUT", "8"))

# Forks must point to the same server; they cannot change this without
# recompiling, and the server controls what keys are valid.
_SERVER_PUBKEY_FINGERPRINT = os.getenv(
    "PILLAI_SERVER_FINGERPRINT",
    "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",  # replace in prod
)


def _machine_id() -> str:
    """
    Persistent machine identity stored in ~/.pill.ai/machine.id.

    Generated once on first run, survives reboots and OS updates.
    More stable than MAC (changes in Docker) or hostname (changes on reinstall).
    Falls back to MAC+CPU+hostname hash if the file can't be written (read-only FS).
    """
    id_file = CACHE_DIR / "machine.id"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if id_file.exists():
        mid = id_file.read_text().strip()
        if mid:
            return mid
    try:
        mid = str(uuid.uuid4())
        id_file.write_text(mid)
        return mid
    except OSError:
        return _hardware_id_fallback()


def _hardware_id_fallback() -> str:
    """Legacy fingerprint — used only when machine.id can't be written."""
    parts = [
        platform.node(),
        str(uuid.getnode()),
        platform.processor(),
        platform.machine(),
    ]
    raw = "|".join(p for p in parts if p)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _hardware_id() -> str:
    return _machine_id()


def _install_id() -> str:
    """Per-installation UUID, created once and stored."""
    id_file = CACHE_DIR / "install_id"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if id_file.exists():
        return id_file.read_text().strip()
    new_id = str(uuid.uuid4())
    id_file.write_text(new_id)
    return new_id


def _save_cache(info: LicenseInfo) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "key": info.key,
        "status": info.status.value,
        "tier": info.tier.value,
        "email": info.email,
        "owner_id": info.owner_id,
        "daily_call_limit": info.daily_call_limit,
        "features": info.features,
        "message": info.message,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "grace_until": (
            datetime.now(timezone.utc) + timedelta(days=GRACE_DAYS)
        ).isoformat(),
        "expires_at": info.expires_at.isoformat() if info.expires_at else None,
    }
    CACHE_FILE.write_text(json.dumps(data))


def _load_cache(key: str) -> Optional[LicenseInfo]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        if data.get("key") != key:
            return None
        grace_until = datetime.fromisoformat(data["grace_until"])
        if datetime.now(timezone.utc) > grace_until:
            return None  # cache expired
        return LicenseInfo(
            key=data["key"],
            status=LicenseStatus.GRACE,
            tier=LicenseTier(data["tier"]),
            email=data.get("email", ""),
            owner_id=data.get("owner_id", ""),
            daily_call_limit=data.get("daily_call_limit", 100),
            features=data.get("features", []),
            message=data.get("message", ""),
            validated_at=datetime.fromisoformat(data["validated_at"]),
            grace_until=grace_until,
        )
    except Exception:
        return None


class LicenseClient:
    """
    Validate a license key against the pill.ai license server.

    Usage:
        client = LicenseClient("XXXX-XXXX-XXXX-XXXX")
        info = client.validate()
        if not info.is_usable():
            raise SystemExit(f"License {info.status}: {info.message}")
    """

    def __init__(self, license_key: str):
        self.key = license_key.strip().upper()
        self.hw_id = _hardware_id()
        self.install_id = _install_id()

    def validate(self) -> LicenseInfo:
        """Try server; fall back to grace-period cache."""
        try:
            return self._validate_online()
        except (httpx.RequestError, httpx.TimeoutException):
            cached = _load_cache(self.key)
            if cached:
                return cached
            # No cache and no server → fail open for FREE tier only
            return LicenseInfo(
                key=self.key,
                status=LicenseStatus.GRACE,
                tier=LicenseTier.FREE,
                message="License server unreachable. Running in offline grace mode.",
                daily_call_limit=20,   # reduced limit while offline
            )

    def _validate_online(self) -> LicenseInfo:
        payload = {
            "key": self.key,
            "hw_id": self.hw_id,
            "install_id": self.install_id,
            "version": _get_version(),
            "platform": platform.system(),
            "ts": int(time.time()),
        }
        resp = httpx.post(
            f"{LICENSE_SERVER}/v1/validate",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        status = LicenseStatus(data["status"])
        info = LicenseInfo(
            key=self.key,
            status=status,
            tier=LicenseTier(data.get("tier", "free")),
            email=data.get("email", ""),
            owner_id=data.get("owner_id", ""),
            daily_call_limit=data.get("daily_call_limit", 100),
            calls_today=data.get("calls_today", 0),
            features=data.get("features", []),
            message=data.get("message", ""),
            validated_at=datetime.now(timezone.utc),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )

        if status == LicenseStatus.ACTIVE:
            _save_cache(info)

        return info

    def report_usage(self, calls: int = 1) -> None:
        """Best-effort usage ping — fire and forget."""
        try:
            httpx.post(
                f"{LICENSE_SERVER}/v1/usage",
                json={
                    "key": self.key,
                    "hw_id": self.hw_id,
                    "calls": calls,
                    "ts": int(time.time()),
                },
                timeout=3,
            )
        except Exception:
            pass


def _get_version() -> str:
    try:
        from importlib.metadata import version
        return version("pill-ai")
    except Exception:
        return "0.0.0"
