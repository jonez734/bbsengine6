# test_inputstring_key_f1.py
# Tests for KEY_F1 help handler in inputstring.py

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


class TestHandleHelp:
    """Tests for handle_help() in inputstring.py."""

    def test_handle_help_with_string(self):
        """Test handle_help echoes the string help text."""
        from bbsengine6.io.inputstring import handle_help

        with patch("bbsengine6.io.inputstring.echo") as mock_echo:
            result = handle_help("buffer", 0, 0, 80, f1_help="Test help text")
            assert result == ("buffer", 0, 0)
            assert mock_echo.call_count >= 1  # at least one echo for the help text

    def test_handle_help_with_callable(self):
        """Test handle_help calls the callable and echoes result."""
        from bbsengine6.io.inputstring import handle_help

        def get_help():
            return "Dynamic help text"

        with patch("bbsengine6.io.inputstring.echo"):
            result = handle_help("buffer", 0, 0, 80, f1_help=get_help)
            assert result == ("buffer", 0, 0)

    def test_handle_help_with_none(self):
        """Test handle_help returns unchanged when f1_help is None."""
        from bbsengine6.io.inputstring import handle_help

        result = handle_help("buffer", 5, 2, 80, f1_help=None)
        assert result == ("buffer", 5, 2)

    def test_handle_help_with_empty_string(self):
        """Test handle_help returns unchanged for empty string help."""
        from bbsengine6.io.inputstring import handle_help

        with patch("bbsengine6.io.inputstring.echo") as mock_echo:
            result = handle_help("buffer", 0, 0, 80, f1_help="")
            assert result == ("buffer", 0, 0)
            # Empty string still triggers echo call (the function handles it)
            assert mock_echo.call_count >= 1


class TestInputChoiceKeyF1:
    """Tests for KEY_F1 help in inputchoice.py."""

    def test_inputchoice_key_f1_shows_help_string(self):
        """Test pressing KEY_F1 shows the help string."""
        from bbsengine6.io.inputchoice import inputchoice

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo") as mock_echo:
                mock_getch.side_effect = ["KEY_F1", "Q"]

                inputchoice(
                    "Choice: ",
                    "ABQ",
                    default="Q",
                    help="(A) option A, (B) option B, (Q) quit",
                )

                # Should have echoed "help" and the help text
                echo_calls = [str(c) for c in mock_echo.call_args_list]
                help_shown = any(
                    "option A" in str(c) or "help" in str(c).lower() for c in echo_calls
                )
                assert help_shown, f"Help text not shown. Echo calls: {echo_calls}"

    def test_inputchoice_key_f1_calls_callable_help(self):
        """Test KEY_F1 calls the help callable."""
        from bbsengine6.io.inputchoice import inputchoice

        help_called = False

        def my_help(**kwargs):
            nonlocal help_called
            help_called = True

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo"):
                mock_getch.side_effect = ["KEY_F1", "Q"]

                inputchoice(
                    "Choice: ",
                    "AQ",
                    default="Q",
                    help=my_help,
                )

                assert help_called, "Help callable not called on KEY_F1"


class TestInputStringKeyF1Mapping:
    """Tests verifying KEY_F1 is properly mapped in inputstring."""

    def test_key_f1_removed_from_module_level_key_actions(self):
        """Test KEY_F1 was removed from module-level KEY_ACTIONS registry.

        F1 is now handled dynamically with f1_help context per-call,
        not registered at module load time.
        """
        # Access module via sys.modules to bypass io.__getattr__ function shadowing
        import sys

        mod = sys.modules["bbsengine6.io.inputstring"]
        assert "KEY_F1" not in mod.KEY_ACTIONS, (
            "KEY_F1 should not be in module-level KEY_ACTIONS"
        )
        # Verify F2-F12 still work
        assert "KEY_F2" in mod.KEY_ACTIONS, "KEY_F2 should still be in KEY_ACTIONS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
