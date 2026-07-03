"""
Tests for the level.fail echo variable and level dispatch.

These tests pin down two pieces of behavior for the `fail` level:

1. The `level.fail` color variable is registered in the active
   `bbsengine6.io.echo` runtime vars so `{level.fail}` resolves to the
   expected color tokens (matching the deprecated `echovars` module).

2. `echo(..., level="fail")` injects a prefix that uses `{level.fail}`,
   just like the other level dispatch branches do for debug/warning/
   error/ok/info.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import bbsengine6.io  # noqa: F401

echo_module = sys.modules["bbsengine6.io.echo"]


pytestmark = pytest.mark.unit


@pytest.fixture
def captured_stdout(monkeypatch):
    """Capture everything written via write_current_output_stream."""
    import bbsengine6.io.common as common

    buf = io.StringIO()
    written = {"chunks": []}

    def fake_write(s, flush=False):
        written["chunks"].append(s)
        buf.write(s)
        if flush:
            buf.flush()

    monkeypatch.setattr(common, "write_current_output_stream", fake_write)
    # echo.py imports the symbol into its own namespace; patch there too.
    monkeypatch.setattr(echo_module, "write_current_output_stream", fake_write)

    # Prevent the side-effect of writing a logentry to the real logger.
    monkeypatch.setattr(echo_module, "logentry", lambda *a, **kw: None)

    written["stream"] = buf
    return written


class TestLevelFailVariable:
    """The `level.fail` color variable should be registered in echo.py."""

    def test_level_fail_registered_in_runtime_vars(self):
        """echo.py's _runtime_vars must include level.fail alongside the others."""
        assert "level.fail" in echo_module._runtime_vars, (
            "level.fail is missing from bbsengine6.io.echo._runtime_vars; "
            "{level.fail} will not resolve at runtime"
        )

    def test_level_fail_value_is_color_tokens(self):
        """level.fail should expand to ANSI color tokens (mirrors echovars.py)."""
        value = echo_module._runtime_vars.get("level.fail")
        assert value is not None
        # Should look like "{bgred}{black}" - two color tokens concatenated.
        assert "{" in value and "}" in value
        assert value == "{bgred}{black}"

    def test_all_levels_consistent_with_deprecated_echovars(self):
        """The active module should expose every level.* var that echovars.py does."""
        from bbsengine6.io import echovars

        for name in echovars.variables:
            if name.startswith("level."):
                assert name in echo_module._runtime_vars, (
                    f"{name} is defined in echovars but missing from "
                    f"bbsengine6.io.echo._runtime_vars"
                )


class TestLevelFailDispatch:
    """echo(level="fail") should emit a {level.fail}-prefixed line."""

    def test_echo_with_level_fail_emits_prefix(self, captured_stdout):
        """echo(text, level='fail') must produce a non-empty prefix."""
        echo_module.echo("something failed", level="fail")
        out = "".join(captured_stdout["chunks"])
        # The prefix should introduce the F: marker from the level.fail branch.
        assert "F:" in out, (
            f"expected 'F:' prefix marker in output, got: {out!r}"
        )
        # And the message must come after the prefix, not be the only thing printed.
        assert "something failed" in out
        assert out.index("F:") < out.index("something failed")

    def test_echo_with_level_fail_uses_color_tokens(self, captured_stdout):
        """The {level.fail} variable must resolve to actual ANSI color codes."""
        # Resolve the same value the prefix references and turn it into the
        # bytes echo.py would emit, then check the captured output matches.
        from bbsengine6.io.echo import echo_iter, _write_token  # noqa: F401

        rendered_value = "".join(
            tok.text for tok in echo_iter("{level.fail}")
        )
        # Sanity: echo_iter should expand {level.fail} into ANSI codes,
        # not leave the source token behind.
        assert "{level.fail}" not in rendered_value
        assert "\x1b[" in rendered_value, (
            f"expected ANSI escape in resolved {{level.fail}}, got: "
            f"{rendered_value!r}"
        )

        echo_module.echo("kaboom", level="fail")
        out = "".join(captured_stdout["chunks"])
        assert "{level.fail}" not in out
        # The prefix's resolved color codes must appear before the message.
        assert rendered_value in out
        assert out.index(rendered_value) < out.index("kaboom")

    def test_echo_with_level_fail_includes_message(self, captured_stdout):
        """The user-supplied message must still appear after the prefix."""
        echo_module.echo("disk full", level="fail")
        out = "".join(captured_stdout["chunks"])
        assert "disk full" in out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
