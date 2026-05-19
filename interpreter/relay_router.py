"""
Client-side relay router — calls pill.ai relay server instead of LLM APIs directly.

When PILLAI_RELAY_URL is set (or baked in at build time), all LLM calls go
through the owner's server. Users never need API keys and never see model names.

Usage is automatic — LLMRouter detects relay mode and delegates here.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

# Relay URL: env var overrides baked-in value (baked in by `make exe`)
try:
    from interpreter._relay_config import RELAY_URL as _BAKED_URL
except ImportError:
    _BAKED_URL = None

RELAY_URL: Optional[str] = os.getenv("PILLAI_RELAY_URL") or _BAKED_URL

# Timeout for relay calls (seconds) — generous for complex tasks
_TIMEOUT = 120


class RelayRouter:
    """
    Sends requests to the owner's relay server.
    Drop-in replacement for LiteLLM in relay mode.
    """

    def __init__(self, relay_url: str, license_key: str, hw_id: str):
        self.relay_url = relay_url.rstrip("/")
        self.license_key = license_key
        self.hw_id = hw_id
        self._session_cost = 0.0  # cost tracked server-side; always 0 on client

    def complete(
        self,
        messages: list[dict],
        task_hint: str = "",
        **_kwargs,  # swallow litellm-specific kwargs
    ) -> str:
        payload = {
            "key": self.license_key,
            "hw_id": self.hw_id,
            "messages": messages,
            "task_hint": task_hint,
        }
        try:
            resp = httpx.post(
                f"{self.relay_url}/v1/relay",
                json=payload,
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("content", "")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RuntimeError(
                    "Daily call limit reached. Upgrade at https://pill.ai/pricing"
                ) from e
            if e.response.status_code == 403:
                raise RuntimeError(
                    f"License error: {e.response.json().get('detail', 'unauthorized')}"
                ) from e
            raise RuntimeError(f"Relay server error: {e.response.status_code}") from e
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot reach pill.ai relay server at {self.relay_url}. "
                "Check your internet connection."
            ) from None

    @property
    def session_cost(self) -> float:
        return self._session_cost

    def reset_budget(self):
        pass  # budget enforced server-side


def is_relay_mode() -> bool:
    return bool(RELAY_URL)
