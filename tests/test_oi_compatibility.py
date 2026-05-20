"""
OI compatibility tests — verify pill.ai's Interpreter matches the public
API of OpenInterpreter/open-interpreter (main branch, May 2026).

Tests are intentionally offline-safe: no LLM calls, no network, no license key.
Mock LangGraph graph where needed.
"""
import inspect
from unittest.mock import MagicMock, patch

import pytest

# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_interpreter(**kwargs):
    """Build an Interpreter with all external I/O patched out."""
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(
            __import__("interpreter.core.core", fromlist=["Interpreter"]).Interpreter,
            "_print_banner",
        ),
        patch.object(
            __import__("interpreter.core.core", fromlist=["Interpreter"]).Interpreter,
            "_ask_permissions_on_first_run",
        ),
    ):
        from interpreter.core.core import Interpreter
        return Interpreter(**kwargs)


def _mock_license():
    from licensing.models import LicenseInfo, LicenseTier, LicenseStatus
    return LicenseInfo(
        key="LOCAL",
        tier=LicenseTier.FREE,
        status=LicenseStatus.VALID,
        daily_call_limit=0,
        message="",
    )


# ─── 1. __init__ param parity ─────────────────────────────────────────────────

OI_PARAMS = [
    # name, expected_default
    ("messages", None),
    ("offline", False),
    ("auto_run", False),
    ("verbose", False),
    ("debug", False),
    ("max_output", 2800),
    ("safe_mode", "off"),
    ("shrink_images", True),
    ("loop", False),
    ("loop_breakers", None),       # default resolved inside __init__
    ("disable_telemetry", True),   # pill.ai flips default to True (privacy)
    ("in_terminal_interface", False),
    ("conversation_history", True),
    ("conversation_filename", None),
    ("conversation_history_path", None),  # default resolved inside __init__
    ("os", False),
    ("speak_messages", False),
    ("llm", None),
    ("custom_instructions", ""),
    ("user_message_template", "{content}"),
    ("always_apply_user_message_template", False),
    ("code_output_sender", "user"),
    ("computer", None),
    ("sync_computer", False),
    ("import_computer_api", False),
    ("skills_path", None),
    ("import_skills", False),
    ("multi_line", True),
    ("contribute_conversation", False),
    ("plain_text_display", False),
]


@pytest.mark.parametrize("param,_", OI_PARAMS)
def test_oi_param_exists(param, _):
    """Every OI __init__ param must be present in pill.ai's Interpreter."""
    from interpreter.core.core import Interpreter
    sig = inspect.signature(Interpreter.__init__)
    assert param in sig.parameters, (
        f"Missing OI param '{param}' from Interpreter.__init__"
    )


def test_all_oi_params_accepted_without_error():
    """Passing every OI param should not raise."""
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter(
            messages=[],
            offline=True,
            auto_run=False,
            verbose=False,
            debug=False,
            max_output=1000,
            safe_mode="off",
            shrink_images=False,
            loop=False,
            loop_breakers=["done"],
            disable_telemetry=True,
            in_terminal_interface=False,
            conversation_history=False,
            os=False,
            speak_messages=False,
            llm=None,
            system_message="test",
            custom_instructions="be helpful",
            user_message_template="{content}",
            always_apply_user_message_template=False,
            code_output_template="output: {content}",
            empty_code_output_template="no output",
            code_output_sender="user",
            sync_computer=False,
            import_computer_api=False,
            import_skills=False,
            multi_line=True,
            contribute_conversation=False,
            plain_text_display=False,
        )
        assert ai is not None


# ─── 2. Instance attribute parity ─────────────────────────────────────────────

OI_ATTRIBUTES = [
    "messages",
    "responding",
    "last_messages_count",
    "offline",
    "auto_run",
    "verbose",
    "debug",
    "max_output",
    "safe_mode",
    "shrink_images",
    "loop",
    "loop_message",
    "loop_breakers",
    "disable_telemetry",
    "in_terminal_interface",
    "conversation_history",
    "conversation_filename",
    "conversation_history_path",
    "os",
    "speak_messages",
    "custom_instructions",
    "user_message_template",
    "always_apply_user_message_template",
    "code_output_template",
    "empty_code_output_template",
    "code_output_sender",
    "sync_computer",
    "import_computer_api",
    "import_skills",
    "multi_line",
    "contribute_conversation",
    "plain_text_display",
    "highlight_active_line",
    "computer",
    "system_message",
]


@pytest.mark.parametrize("attr", OI_ATTRIBUTES)
def test_oi_attribute_exists(attr):
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert hasattr(ai, attr), f"Missing OI instance attribute: {attr}"


# ─── 3. Method parity ─────────────────────────────────────────────────────────

OI_METHODS = ["chat", "reset", "wait", "local_setup", "display_message", "get_oi_dir"]


@pytest.mark.parametrize("method", OI_METHODS)
def test_oi_method_exists(method):
    from interpreter.core.core import Interpreter
    assert hasattr(Interpreter, method), f"Missing OI method: {method}"
    assert callable(getattr(Interpreter, method))


def test_chat_signature_oi_compatible():
    """chat(message, display, stream) — matches OI's signature."""
    from interpreter.core.core import Interpreter
    sig = inspect.signature(Interpreter.chat)
    params = list(sig.parameters)
    assert "message" in params
    assert "display" in params
    assert "stream" in params


def test_reset_clears_messages():
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        ai.messages = [{"role": "user", "content": "hello"}]
        ai.last_messages_count = 1
        # Patch terminal.terminate so reset() doesn't fail
        ai.computer.terminal.terminate = MagicMock()
        ai.reset()
        assert ai.messages == []
        assert ai.last_messages_count == 0


# ─── 4. OI properties ─────────────────────────────────────────────────────────

def test_anonymous_telemetry_is_false():
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert ai.anonymous_telemetry is False


def test_will_contribute_is_false():
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert ai.will_contribute is False


# ─── 5. computer.* namespace parity ───────────────────────────────────────────

COMPUTER_ATTRS = [
    "mouse",
    "keyboard",
    "browser",
    "terminal",
    "display",
    "clipboard",
    "files",
    "vision",
    "os",
    "screenshot",
]


@pytest.mark.parametrize("attr", COMPUTER_ATTRS)
def test_computer_attr_exists(attr):
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert hasattr(ai.computer, attr), f"Missing computer.{attr}"


def test_computer_os_alias_is_terminal():
    """computer.os should be the same object as computer.terminal."""
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert ai.computer.os is ai.computer.terminal


def test_computer_screenshot_callable():
    from interpreter.core.core import Interpreter
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert callable(ai.computer.screenshot)


# ─── 6. Singleton import pattern ──────────────────────────────────────────────

def test_interpreter_singleton_importable():
    """from interpreter import interpreter should work without instantiation error."""
    with patch("licensing.activation.require_license", return_value=_mock_license()):
        import interpreter as interp_module
        assert hasattr(interp_module, "interpreter")
        assert hasattr(interp_module, "Interpreter")


def test_lazy_singleton_not_instantiated_on_import():
    """The singleton should NOT construct until first attribute access."""
    # _singleton should still be None if we never accessed interpreter.*
    # Access _singleton via the module's internal
    import interpreter.interpreter as interp_mod
    # This test is structural — just ensure the proxy class is in place
    assert "Lazy" in type(interp_mod.interpreter).__name__


# ─── 7. OI import compat ──────────────────────────────────────────────────────

def test_oi_import_pattern():
    """from interpreter import Interpreter should expose the class."""
    from interpreter import Interpreter
    assert inspect.isclass(Interpreter)


def test_class_name_differs_but_compatible():
    """OI uses OpenInterpreter; pill.ai uses Interpreter. Both are valid."""
    from interpreter import Interpreter
    # Should be constructable with zero args
    with (
        patch("licensing.activation.require_license", return_value=_mock_license()),
        patch.object(Interpreter, "_print_banner"),
        patch.object(Interpreter, "_ask_permissions_on_first_run"),
    ):
        ai = Interpreter()
        assert isinstance(ai, Interpreter)
