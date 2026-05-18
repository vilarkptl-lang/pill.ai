"""
Fork of OpenInterpreter/open-interpreter — interpreter/interpreter.py

Top-level public API — API-compatible with Open Interpreter:
  from interpreter import interpreter   # ← same import path as OI
  from interpreter import Interpreter   # ← class for custom instances

OI instantiated a singleton at import time; pill.ai does the same
but defers the license check to first use to avoid a network call
on every `import interpreter`.
"""
from .core.core import Interpreter

# Convenience singleton — matches `from interpreter import interpreter` in OI.
# Lazy: __getattr__ defers construction until first attribute access.
_singleton: Interpreter | None = None


def _get_singleton() -> Interpreter:
    global _singleton
    if _singleton is None:
        _singleton = Interpreter()
    return _singleton


class _LazyInterpreter:
    """Proxy that creates the real Interpreter on first attribute access."""

    def __getattr__(self, name: str):
        return getattr(_get_singleton(), name)

    def __call__(self, *args, **kwargs):
        return _get_singleton().chat(*args, **kwargs)

    def __repr__(self):
        return repr(_get_singleton())


interpreter = _LazyInterpreter()

__all__ = ["Interpreter", "interpreter"]
