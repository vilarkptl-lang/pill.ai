"""
CLI helpers for activation / deactivation.
Called by the installer and by `pillai activate <KEY>`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from .client import CACHE_DIR, LicenseClient
from .models import LicenseInfo, LicenseStatus

_KEY_FILE = CACHE_DIR / "license.key"


def _stored_key() -> Optional[str]:
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip() or None
    return None


def activate(key: str) -> LicenseInfo:
    """
    Activate this installation with `key`.
    Persists the key locally and validates immediately.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(key.strip().upper())
    client = LicenseClient(key)
    info = client.validate()
    return info


def deactivate() -> None:
    """Remove stored key (allows the seat to be reused on another machine)."""
    if _KEY_FILE.exists():
        _KEY_FILE.unlink()
    cache = CACHE_DIR / "license.cache"
    if cache.exists():
        cache.unlink()


def get_license_status() -> LicenseInfo:
    """
    Return current license info.
    - If PILLAI_LICENSE_KEY env var is set, that takes priority.
    - Otherwise reads from the stored key file.
    - If neither, returns a FREE anonymous license.
    """
    key = os.getenv("PILLAI_LICENSE_KEY") or _stored_key() or "FREE"
    client = LicenseClient(key)
    return client.validate()


def require_license(min_tier: str = "free") -> LicenseInfo:
    """
    Call this at interpreter startup.
    Raises SystemExit with a human-friendly message if the license is not usable
    or below the required tier.
    """
    from .models import LicenseTier

    tier_order = [t.value for t in LicenseTier]
    info = get_license_status()

    if not info.is_usable():
        _print_blocked(info)
        raise SystemExit(1)

    if info.message:
        print(f"\n[pill.ai] {info.message}\n")

    required_idx = tier_order.index(min_tier) if min_tier in tier_order else 0
    current_idx = tier_order.index(info.tier.value)
    if current_idx < required_idx:
        print(
            f"\n[pill.ai] This feature requires the '{min_tier}' tier or above.\n"
            f"  Current tier: {info.tier.value}\n"
            f"  Upgrade at: https://pill.ai/pricing\n"
        )
        raise SystemExit(1)

    return info


def _print_blocked(info: LicenseInfo) -> None:
    messages = {
        LicenseStatus.EXPIRED: (
            "Your pill.ai license has expired.\n"
            "  Renew at: https://pill.ai/billing"
        ),
        LicenseStatus.SUSPENDED: (
            f"Your pill.ai license has been suspended.\n"
            f"  {info.message or 'Contact support: support@pill.ai'}"
        ),
        LicenseStatus.REVOKED: (
            "Your pill.ai license key has been revoked.\n"
            "  Contact support: support@pill.ai"
        ),
        LicenseStatus.FREE_DISABLED: (
            "The free tier of pill.ai has been disabled.\n"
            "  Purchase a license at: https://pill.ai/pricing"
        ),
        LicenseStatus.INVALID: (
            f"License key '{info.key[:8]}...' is not valid.\n"
            "  Get a key at: https://pill.ai/pricing"
        ),
    }
    msg = messages.get(info.status, f"License error: {info.status.value}")
    print(f"\n[pill.ai] {msg}\n")
