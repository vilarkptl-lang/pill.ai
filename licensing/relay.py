"""
Server-side relay — model routing logic for /v1/relay.

The owner puts their API keys in .env on the server.
Users never see model names — only receive the response text.

Configure via env vars (in .env on the server):
  PILLAI_MODEL_FAST    = gemini/gemini-2.0-flash-exp    (default)
  PILLAI_MODEL_MEDIUM  = deepseek/deepseek-chat          (default)
  PILLAI_MODEL_PRO     = deepseek/deepseek-chat          (default)
  GEMINI_API_KEY       = ...
  DEEPSEEK_API_KEY     = ...
"""
from __future__ import annotations

import os
from typing import Iterator

try:
    import litellm
    litellm.drop_params = True
    litellm.set_verbose = False
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

# Model aliases — owner configures these in .env, users never see them
_MODEL_FAST   = os.getenv("PILLAI_MODEL_FAST",   "gemini/gemini-2.0-flash-exp")
_MODEL_MEDIUM = os.getenv("PILLAI_MODEL_MEDIUM",  "deepseek/deepseek-chat")
_MODEL_PRO    = os.getenv("PILLAI_MODEL_PRO",     "deepseek/deepseek-chat")

# Keyword signals for model selection
_PRO_SIGNALS = {
    "debug", "refactor", "architecture", "optimize", "algorithm",
    "implement", "async", "database", "traceback", "exception",
    "performance", "security", "unittest", "pytest", "benchmark",
    "concurrency", "thread", "memory leak", "race condition",
}
_MEDIUM_SIGNALS = {
    "write", "code", "script", "python", "javascript", "typescript",
    "explain", "analyze", "compare", "summarize", "function",
    "import", "class", "def ", "sql", "api", "json", "regex",
}


def pick_model(messages: list[dict], task_hint: str) -> str:
    """
    Choose model transparently. Never exposed to the client.
    """
    text = (task_hint + " " + " ".join(
        str(m.get("content", ""))[-300:] for m in messages[-6:]
    )).lower()

    pro_score    = sum(1 for s in _PRO_SIGNALS    if s in text)
    medium_score = sum(1 for s in _MEDIUM_SIGNALS if s in text)
    total_chars  = sum(len(str(m.get("content", ""))) for m in messages)

    if pro_score >= 2 or total_chars > 4_000:
        return _MODEL_PRO
    if medium_score >= 1 or pro_score == 1 or total_chars > 600:
        return _MODEL_MEDIUM
    return _MODEL_FAST


def relay_complete(messages: list[dict], task_hint: str = "") -> str:
    """
    Call the appropriate LLM with the owner's API keys.
    Returns only the response text — model name never leaves this function.
    """
    if not HAS_LITELLM:
        raise RuntimeError("litellm not installed on server")

    model = pick_model(messages, task_hint)

    try:
        resp = litellm.completion(model=model, messages=messages)
        return resp.choices[0].message.content or ""
    except Exception as e:
        # Fallback: if the chosen model fails, try medium then fast
        for fallback in (_MODEL_MEDIUM, _MODEL_FAST):
            if fallback == model:
                continue
            try:
                resp = litellm.completion(model=fallback, messages=messages)
                return resp.choices[0].message.content or ""
            except Exception:
                continue
        raise RuntimeError(f"All models failed. Last error: {e}") from e
