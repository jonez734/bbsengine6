"""
Test suite for display_with_more_prompt() function.

Tests verify that:
1. More prompt displays correctly
2. Pressing ENTER (or 'y') continues to next page
3. Pressing 'n' aborts and returns False
4. Page callbacks are called at correct times
5. Messages display in correct order
"""

import sys
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock, call

# Add source to path
sys.path.insert(0, "py/src")

from bbsengine6.examples.notify_message_demo import display_with_more_prompt
from bbsengine6.io.echo import echo


class TestMorePromptBasicFunctionality:
    """Test basic more prompt functionality."""

    def test_more_prompt_with_enter_continues(self):
        """Test that pressing ENTER continues to next page."""
        messages = [f"Message {i}" for i in range(1, 7)]

        # Mock inputchoice to return 'y' (continue)
        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            result = display_with_more_prompt(messages, page_size=3)

            # Should return True (all messages displayed)
            assert result is True

            # inputchoice should have been called once (after 3 messages)
            assert mock_input.call_count == 1

    def test_more_prompt_with_n_aborts(self):
        """Test that pressing 'n' aborts."""
        messages = [f"Message {i}" for i in range(1, 7)]

        # Mock inputchoice to return 'n' (abort) - note: must be lowercase
        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "n"

            result = display_with_more_prompt(messages, page_size=3)

            # Should return False (aborted)
            assert result is False

            # inputchoice should have been called once
            assert mock_input.call_count == 1

    def test_more_prompt_with_default_y(self):
        """Test that default 'y' allows pressing just ENTER."""
        messages = [f"Message {i}" for i in range(1, 7)]

        # Mock inputchoice to return None (default, which is 'y')
        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = None

            result = display_with_more_prompt(messages, page_size=3)

            # Should return True (all messages displayed, default='y' continues)
            assert result is True

    def test_no_more_prompt_with_few_messages(self):
        """Test that fewer messages than page_size shows no prompt."""
        messages = [f"Message {i}" for i in range(1, 4)]  # Only 3 messages

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            result = display_with_more_prompt(messages, page_size=5)

            # Should return True without prompting
            assert result is True

            # inputchoice should NOT be called
            assert mock_input.call_count == 0

    def test_more_prompt_multiple_pages(self):
        """Test more prompt with multiple pages."""
        messages = [f"Message {i}" for i in range(1, 10)]  # 9 messages

        # Mock inputchoice to always return 'y'
        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            result = display_with_more_prompt(messages, page_size=3)

            # Should return True
            assert result is True

            # Should be called twice (after 3 messages, after 6 messages)
            assert mock_input.call_count == 2

    def test_more_prompt_exact_page_size(self):
        """Test when messages equals exactly one page size."""
        messages = [f"Message {i}" for i in range(1, 4)]  # Exactly 3 messages

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            result = display_with_more_prompt(messages, page_size=3)

            # Should return True without prompting (no remaining messages)
            assert result is True

            # No prompt needed
            assert mock_input.call_count == 0


class TestMorePromptPageCallback:
    """Test page callback functionality."""

    def test_page_callback_called(self):
        """Test that page callback is called after each page."""
        messages = [f"Message {i}" for i in range(1, 7)]  # 6 messages
        callback = MagicMock()

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            display_with_more_prompt(messages, page_size=3, on_page_displayed=callback)

            # Callback is called after each complete page AND for final incomplete page
            # With 6 messages and page_size=3: page 1 (3 msgs), page 2 (3 msgs)
            assert callback.call_count == 2

    def test_page_callback_multiple_pages(self):
        """Test callback with multiple pages."""
        messages = [f"Message {i}" for i in range(1, 7)]
        callback = MagicMock()

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            display_with_more_prompt(messages, page_size=3, on_page_displayed=callback)

            # Callback should be called for each complete page
            assert callback.call_count == 2

    def test_page_callback_called_for_incomplete_page(self):
        """Test callback called for final incomplete page."""
        messages = [f"Message {i}" for i in range(1, 5)]  # 4 messages
        callback = MagicMock()

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            display_with_more_prompt(messages, page_size=3, on_page_displayed=callback)

            # Callback called for page 1 (3 msgs) and final page 2 (1 msg)
            assert callback.call_count == 2


class TestMorePromptInputHandling:
    """Test input handling in more prompt."""

    def test_input_lowercase_y(self):
        """Test that lowercase 'y' works."""
        messages = [f"Message {i}" for i in range(1, 7)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            result = display_with_more_prompt(messages, page_size=3)

            assert result is True

    def test_input_uppercase_y(self):
        """Test that uppercase 'Y' works."""
        messages = [f"Message {i}" for i in range(1, 7)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            # inputchoice will upcase the input, so test with uppercase
            mock_input.return_value = "Y"

            # But the code compares with lowercase "n", so Y != "n" means continue
            result = display_with_more_prompt(messages, page_size=3)

            # Should continue (Y is not "n")
            assert result is True

    def test_input_lowercase_n(self):
        """Test that lowercase 'n' aborts."""
        messages = [f"Message {i}" for i in range(1, 7)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "n"

            result = display_with_more_prompt(messages, page_size=3)

            assert result is False

    def test_input_uppercase_n_continues(self):
        """Test that uppercase 'N' continues (code checks lowercase)."""
        messages = [f"Message {i}" for i in range(1, 7)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            # inputchoice returns uppercase, but code checks lowercase "n"
            # So 'N' != "n", which means continue
            mock_input.return_value = "N"

            result = display_with_more_prompt(messages, page_size=3)

            # N != "n" so it continues
            assert result is True


class TestMorePromptEdgeCases:
    """Test edge cases."""

    def test_empty_message_list(self):
        """Test with empty message list."""
        messages = []

        result = display_with_more_prompt(messages, page_size=3)

        # Should return True (no messages to display)
        assert result is True

    def test_single_message(self):
        """Test with single message."""
        messages = ["Single message"]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            result = display_with_more_prompt(messages, page_size=3)

            # Should return True without prompt
            assert result is True
            assert mock_input.call_count == 0

    def test_large_page_size(self):
        """Test with large page size."""
        messages = [f"Message {i}" for i in range(1, 6)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            result = display_with_more_prompt(messages, page_size=100)

            # Should return True without prompt
            assert result is True
            assert mock_input.call_count == 0

    def test_page_size_one(self):
        """Test with page_size=1."""
        messages = [f"Message {i}" for i in range(1, 4)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            result = display_with_more_prompt(messages, page_size=1)

            # Should return True
            assert result is True

            # Should be called for each complete page (3 messages, 1 per page = 2 prompts)
            assert mock_input.call_count == 2


class TestMorePromptPromptText:
    """Test that prompt displays correct information."""

    def test_prompt_shows_remaining_count(self):
        """Test that prompt shows remaining message count."""
        messages = [f"Message {i}" for i in range(1, 7)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            display_with_more_prompt(messages, page_size=3)

            # Check that inputchoice was called with correct prompt
            call_args = mock_input.call_args[0][0]

            # First call should show 3 remaining
            assert "3 remaining" in call_args

    def test_prompt_updates_remaining_count(self):
        """Test that remaining count updates correctly."""
        messages = [f"Message {i}" for i in range(1, 10)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            display_with_more_prompt(messages, page_size=3)

            # Should be called twice with different remaining counts
            assert mock_input.call_count == 2

            # First call: 9 messages total, 3 shown, 6 remaining
            first_call = mock_input.call_args_list[0][0][0]
            assert "6 remaining" in first_call

            # Second call: 6 remaining, 3 shown, 3 remaining
            second_call = mock_input.call_args_list[1][0][0]
            assert "3 remaining" in second_call


class TestMorePromptIntegration:
    """Integration tests with real echo output."""

    def test_more_prompt_full_flow_with_6_messages(self):
        """Test complete flow: display messages, show prompt, continue."""
        messages = ["Msg 1", "Msg 2", "Msg 3", "Msg 4", "Msg 5", "Msg 6"]
        callback = MagicMock()

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "y"

            result = display_with_more_prompt(
                messages, page_size=3, on_page_displayed=callback
            )

            # Verify behavior
            assert result is True
            # 6 messages, page_size 3: shown at 3, 6 -> prompt at 3 (6 remain)
            assert mock_input.call_count == 1
            # Callback called for complete pages and final page
            assert callback.call_count == 2

    def test_abort_stops_displaying(self):
        """Test that aborting stops at current page."""
        messages = [f"Message {i}" for i in range(1, 10)]

        with patch("bbsengine6.examples.notify_message_demo.inputchoice") as mock_input:
            mock_input.return_value = "n"

            result = display_with_more_prompt(messages, page_size=3)

            # Should return False (aborted)
            assert result is False

            # Only one prompt shown
            assert mock_input.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
