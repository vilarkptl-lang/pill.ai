def __getattr__(name):
    if name == "Interpreter":
        from interpreter import Interpreter
        return Interpreter
    raise AttributeError(name)

__all__ = ["Interpreter"]
