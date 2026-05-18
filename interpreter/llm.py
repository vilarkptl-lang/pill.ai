"""
Fork of OpenInterpreter llm.py — extended with LiteLLM ultra-cheap routing.

Strategy (90% cheap, 10% fallback):
  - Reasoning/code:  deepseek/deepseek-chat   (~$0.14/M tokens)
  - Vision:          gemini/gemini-2.0-flash   (~$0.10/M tokens)
  - Fallback:        gpt-4o-mini               (~$0.15/M tokens)
"""
from __future__ import annotations

import os
from typing import Any, Iterator, Optional

try:
    import litellm
    litellm.drop_params = True
    litellm.set_verbose = False
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False


COST_PER_MODEL = {
    "deepseek/deepseek-chat": {"input": 0.00000014, "output": 0.00000028},
    "gemini/gemini-2.0-flash": {"input": 0.00000010, "output": 0.00000040},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.00000060},
}


class LLMRouter:
    """
    Wraps LiteLLM with:
    - Automatic model selection based on task type
    - Per-task budget enforcement
    - Usage tracking
    """

    def __init__(
        self,
        default_model: str = "deepseek/deepseek-chat",
        vision_model: str = "gemini/gemini-2.0-flash",
        fallback_model: str = "gpt-4o-mini",
        budget_per_task: float = 0.50,
    ):
        self.default_model = default_model
        self.vision_model = vision_model
        self.fallback_model = fallback_model
        self.budget_per_task = budget_per_task
        self._session_cost = 0.0

    def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        has_images: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> str | Iterator[str]:
        if not HAS_LITELLM:
            raise ImportError("litellm is required: pip install litellm")

        chosen = model or (self.vision_model if has_images else self.default_model)

        try:
            resp = litellm.completion(
                model=chosen,
                messages=messages,
                stream=stream,
                **kwargs,
            )
        except Exception as e:
            if chosen != self.fallback_model:
                resp = litellm.completion(
                    model=self.fallback_model,
                    messages=messages,
                    stream=stream,
                    **kwargs,
                )
                chosen = self.fallback_model
            else:
                raise

        if not stream:
            self._track_cost(chosen, resp)
            return resp.choices[0].message.content
        return self._stream_and_track(chosen, resp)

    def _stream_and_track(self, model: str, resp) -> Iterator[str]:
        total_tokens = {"input": 0, "output": 0}
        for chunk in resp:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
            if chunk.usage:
                total_tokens["input"] = chunk.usage.prompt_tokens
                total_tokens["output"] = chunk.usage.completion_tokens
        self._session_cost += _calc_cost(model, total_tokens)

    def _track_cost(self, model: str, resp) -> None:
        tokens = {
            "input": resp.usage.prompt_tokens,
            "output": resp.usage.completion_tokens,
        }
        cost = _calc_cost(model, tokens)
        self._session_cost += cost
        if self._session_cost > self.budget_per_task:
            raise BudgetExceeded(
                f"Task budget of ${self.budget_per_task:.2f} exceeded "
                f"(spent ${self._session_cost:.4f})"
            )

    @property
    def session_cost(self) -> float:
        return self._session_cost

    def reset_budget(self):
        self._session_cost = 0.0


def _calc_cost(model: str, tokens: dict) -> float:
    rates = COST_PER_MODEL.get(model, {"input": 0.000001, "output": 0.000002})
    return tokens["input"] * rates["input"] + tokens["output"] * rates["output"]


class BudgetExceeded(Exception):
    pass
