"""
Hardware fingerprint — anonymous, stable per-machine ID.
Used for relay rate-limiting. Never includes personal data.
"""
from __future__ import annotations

import hashlib
import platform
import uuid


def get_hw_id() -> str:
    """
    Stable anonymous ID based on machine characteristics.
    Same machine always produces the same ID.
    """
    components = [
        platform.node(),
        platform.machine(),
        platform.processor(),
        str(uuid.getnode()),   # MAC address integer
    ]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
