from __future__ import annotations

import os
from typing import Optional

from .client import CACHE_DIR, LicenseClient
from .models import LicenseInfo, LicenseStatus, LicenseTier

_KEY_FILE = CACHE_DIR / "license.key"


def _stored_key() -> Optional[str]:
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip() or None
    return None


def _local_free() -> LicenseInfo:
    return LicenseInfo(
        key="LOCAL",
        status=LicenseStatus.ACTIVE,
        tier=LicenseTier.FREE,
        daily_call_limit=0,
        message="",
    )


def activate(key: str) -> LicenseInfo:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _KEY_FILE.write_text(key.strip().upper())
    client = LicenseClient(key)
    return client.validate()


def deactivate() -> None:
    if _KEY_FILE.exists():
        _KEY_FILE.unlink()
    cache = CACHE_DIR / "license.cache"
    if cache.exists():
        cache.unlink()


def get_license_status() -> LicenseInfo:
    key = os.getenv("PILLAI_LICENSE_KEY") or _stored_key()
    if not key:
        return _local_free()
    return LicenseClient(key).validate()


def require_license(min_tier: str = "free") -> LicenseInfo:
    from .models import LicenseTier
    key = os.getenv("PILLAI_LICENSE_KEY") or _stored_key()
    if not key:
        return _local_free()
    info = LicenseClient(key).validate()
    if not info.is_usable():
        _print_blocked(info)
        print("[pill.ai] Falling back to local free mode.\n")
        return _local_free()
    if info.message:
        print(f"[pill.ai] {info.message}\n")
    tier_order = [t.value for t in LicenseTier]
    required_idx = tier_order.index(min_tier) if min_tier in tier_order else 0
    current_idx = tier_order.index(info.tier.value)
    if current_idx < required_idx:
        print(
            f"[pill.ai] This feature requires the '{min_tier}' tier.\n"
            f"  Current: {info.tier.value} — upgrade at https://pill.ai/pricing\n"
        )
    return info


def require_relay(min_tier: str = "starter") -> LicenseInfo:
    from .models import LicenseTier
    info = require_license(min_tier)
    tier_order = [t.value for t in LicenseTier]
    required_idx = tier_order.index(min_tier) if min_tier in tier_order else 1
    current_idx = tier_order.index(info.tier.value)
    if info.key == "LOCAL" or current_idx < required_idx:
        print(
            f"\n[pill.ai] Relay cloud features require a '{min_tier}' license.\n"
            f"  Get one at: https://pill.ai/pricing\n"
        )
        raise SystemExit(1)
    return info


def _print_blocked(info: LicenseInfo) -> None:
    messages = {
        LicenseStatus.EXPIRED: "Your pill.ai license has expired. Renew at https://pill.ai/billing",
        LicenseStatus.SUSPENDED: f"Your license is suspended. {info.message or 'Contact support@pill.ai'}",
        LicenseStatus.REVOKED: "Your license key has been revoked. Contact support@pill.ai",
        LicenseStatus.FREE_DISABLED: "Free tier disabled by operator. Get a license at https://pill.ai/pricing",
        LicenseStatus.INVALID: f"Key '{info.key[:8]}...' is not valid. Check https://pill.ai/pricing",
    }
    msg = messages.get(info.status, f"License error: {info.status.value}")
    print(f"\n[pill.ai] {msg}\n")
