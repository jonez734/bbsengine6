# test_inputchoice_key_f2.py
# Tests for KEY_F2 handler in inputchoice.py

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


class TestInputChoiceKeyF2:
    """Tests for KEY_F2 handler in inputchoice.py."""

    def test_inputchoice_key_f2_shows_string_handler(self):
        """Test pressing KEY_F2 echoes the string handler and reprompts."""
        from bbsengine6.io.inputchoice import inputchoice

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo") as mock_echo:
                mock_getch.side_effect = ["KEY_F2", "Q"]

                result = inputchoice(
                    "Choice: ",
                    "AQ",
                    default="Q",
                    f2_handler="Showing notifications list...",
                )

                echo_calls = [str(c) for c in mock_echo.call_args_list]
                f2_shown = any("notifications" in str(c) for c in echo_calls)
                assert f2_shown, (
                    f"F2 string handler not echoed. Echo calls: {echo_calls}"
                )
                assert result == "Q"

    def test_inputchoice_key_f2_calls_callable(self):
        """Test KEY_F2 calls the callable handler and reprompts."""
        from bbsengine6.io.inputchoice import inputchoice

        handler_called = False

        def my_f2_handler(**kwargs):
            nonlocal handler_called
            handler_called = True

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo"):
                mock_getch.side_effect = ["KEY_F2", "Q"]

                result = inputchoice(
                    "Choice: ",
                    "AQ",
                    default="Q",
                    f2_handler=my_f2_handler,
                )

                assert handler_called, "F2 callable not called on KEY_F2"
                assert result == "Q"

    def test_inputchoice_key_f2_with_none(self):
        """Test KEY_F2 with None handler just reprompts (no-op)."""
        from bbsengine6.io.inputchoice import inputchoice

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo") as mock_echo:
                mock_getch.side_effect = ["KEY_F2", "Q"]

                result = inputchoice(
                    "Choice: ",
                    "AQ",
                    default="Q",
                    f2_handler=None,
                )

                assert result == "Q"

    def test_key_f2_not_matched_by_options(self):
        """Test KEY_F2 does not match options string, so loop continues."""
        from bbsengine6.io.inputchoice import inputchoice

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo"):
                mock_getch.side_effect = ["KEY_F2", "A"]

                result = inputchoice(
                    "Choice: ",
                    "ABQ",
                    default="Q",
                    f2_handler="notifications",
                )

                assert result == "A"

    def test_key_f2_reprints_prompt_after_handler(self):
        """Test F2 handler causes prompt to be reprinted after handler runs."""
        from bbsengine6.io.inputchoice import inputchoice

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo") as mock_echo:
                mock_getch.side_effect = ["KEY_F2", "Q"]

                inputchoice(
                    "Choose: ",
                    "AQ",
                    default="Q",
                    f2_handler="F2 handler called",
                )

                prompt_reprinted = any(
                    "Choose:" in str(c) for c in mock_echo.call_args_list
                )
                assert prompt_reprinted, "Prompt not reprinted after F2 handler"

    def test_inputchoice_key_f2_with_kwargs(self):
        """Test F2 callable receives kwargs (args, etc.)."""
        from bbsengine6.io.inputchoice import inputchoice

        received_kwargs = {}

        def capture_kwargs(**kwargs):
            received_kwargs.update(kwargs)

        with patch("bbsengine6.io.inputchoice.getch") as mock_getch:
            with patch("bbsengine6.io.inputchoice.echo"):
                mock_getch.side_effect = ["KEY_F2", "Q"]

                class MockArgs:
                    loginid = "testuser"
                    debug = True

                inputchoice(
                    "Choice: ",
                    "AQ",
                    default="Q",
                    f2_handler=capture_kwargs,
                    args=MockArgs(),
                )

                assert "args" in received_kwargs
                assert received_kwargs["args"].loginid == "testuser"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
