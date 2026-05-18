from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LicenseTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class LicenseStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"       # owner suspended this key
    REVOKED = "revoked"           # owner permanently revoked
    FREE_DISABLED = "free_disabled"  # owner turned off free tier globally
    INVALID = "invalid"
    GRACE = "grace"               # server unreachable, cached result in use


@dataclass
class LicenseInfo:
    key: str
    status: LicenseStatus
    tier: LicenseTier
    email: str = ""
    owner_id: str = ""
    expires_at: Optional[datetime] = None
    daily_call_limit: int = 100       # -1 = unlimited
    calls_today: int = 0
    features: list[str] = field(default_factory=list)
    message: str = ""                 # message from owner to display on startup
    validated_at: Optional[datetime] = None
    grace_until: Optional[datetime] = None

    def is_usable(self) -> bool:
        return self.status in (LicenseStatus.ACTIVE, LicenseStatus.GRACE)

    def calls_remaining(self) -> int:
        if self.daily_call_limit == -1:
            return 999_999
        return max(0, self.daily_call_limit - self.calls_today)
