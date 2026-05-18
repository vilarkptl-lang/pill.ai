"""
Fork of OpenInterpreter/open-interpreter — interpreter/interpreter.py
Top-level public API — keeps compatibility with Open Interpreter's interface.
"""
from .core.core import Interpreter

# Convenience singleton (mirrors Open Interpreter's `from interpreter import interpreter`)
interpreter = Interpreter()
