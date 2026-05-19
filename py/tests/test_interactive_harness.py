# test_interactive_harness.py
# Automated testing harness for interactive demo with mocked input/output

import sys
from typing import List, Tuple

import pytest

# Add examples path to import the demo
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import DemoConfig, handle_character_input


# ============================================================================
# LOOP STATE SIMULATOR
# ============================================================================


class LoopStateSimulator:
    """
    Simulates the interactive loop state without running the actual loop.

    Tests the key logic: prompt caching, buffer management, and status updates.
    """

    def __init__(self, config: DemoConfig):
        self.config = config
        self.buffer = ""
        self.previous_prompt = ""
        self.prompts_shown: List[str] = []
        self.prompts_cleared: int = 0
        self.status_updates: List[Tuple[int, str]] = []

    def process_key(self, key: str) -> None:
        """Process a keystroke and update state."""
        # Update buffer
        self.buffer = handle_character_input(key, self.buffer)

        # Generate current prompt
        current_prompt = f"{self.config.moniker}> {self.buffer}"

        # Check if prompt needs redraw (caching logic)
        if current_prompt != self.previous_prompt:
            # Only clear and redraw if changed
            self.prompts_cleared += 1
            self.prompts_shown.append(current_prompt)
            self.previous_prompt = current_prompt

    def handle_enter(self) -> str:
        """Handle ENTER key - extract command and reset buffer."""
        command = self.buffer.strip()
        self.buffer = ""

        # Reset prompt cache
        self.previous_prompt = ""
        self.prompts_cleared += 1

        return command

    def handle_f2(self) -> None:
        """Handle F2 key - clear and reset."""
        # F2 displays messages and clears prompt
        self.prompts_cleared += 1
        self.previous_prompt = ""
        self.buffer = ""

    def handle_timeout(self, clear_on_timeout: bool = False) -> None:
        """Handle timeout - optionally clear prompt."""
        if clear_on_timeout:
            self.prompts_cleared += 1
            self.previous_prompt = ""
        # If not clearing, loop back with caching active - no redraw

    def update_status(self, unread_count: int) -> None:
        """Update status bar."""
        status = f"F2: Messages ({unread_count})" if unread_count > 0 else ""
        self.status_updates.append((unread_count, status))


# ============================================================================
# TESTS - INTERACTIVE LOOP BASICS
# ============================================================================


class TestInteractiveLoopBasics:
    """Test basic interactive loop behavior using state simulator."""

    def test_simple_character_input(self):
        """Test that character input is buffered correctly."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type "hello"
        for char in "hello":
            sim.process_key(char)

        # Should have prompts showing buffer growth
        prompts = sim.prompts_shown
        assert len(prompts) > 0
        assert "alice> h" in prompts
        assert "alice> hello" in prompts

    def test_backspace_handling(self):
        """Test that backspace removes characters from buffer."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type "hello", backspace twice, add "p"
        for char in "hello":
            sim.process_key(char)
        sim.process_key("KEY_BACKSPACE")
        sim.process_key("KEY_BACKSPACE")
        sim.process_key("p")

        # Should have "help" in one of the prompts
        prompts = sim.prompts_shown
        assert any("help" in p for p in prompts)

    def test_escape_clears_buffer(self):
        """Test that ESC key clears the buffer."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type "test", press ESC, type "new"
        for char in "test":
            sim.process_key(char)
        sim.process_key("KEY_ESC")
        for char in "new":
            sim.process_key(char)

        # After ESC, buffer should be "new"
        assert sim.buffer == "new"
        prompts = sim.prompts_shown
        # Should see both "test" and "new" prompts
        assert any("test" in p for p in prompts)
        assert any("new" in p for p in prompts)


# ============================================================================
# TESTS - PROMPT CACHING (NO FLICKER)
# ============================================================================


class TestPromptCaching:
    """Test prompt caching to prevent flickering on timeout."""

    def test_no_unnecessary_redraws_on_timeout(self):
        """Test that prompt is not redrawn if content hasn't changed."""
        config = DemoConfig(
            moniker="alice", check_timeout=1, clear_prompt_on_timeout=False
        )
        sim = LoopStateSimulator(config)

        # Simulate timeout (no input) with clear_prompt_on_timeout=False
        initial_clears = sim.prompts_cleared
        sim.handle_timeout(clear_on_timeout=False)

        # With clear_prompt_on_timeout=False, timeout should NOT cause clear
        assert sim.prompts_cleared == initial_clears

    def test_prompt_redraw_on_buffer_change(self):
        """Test that prompt IS redrawn when buffer changes."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type one character
        sim.process_key("a")

        # Should show initial empty prompt and "a" prompt
        prompts = sim.prompts_shown
        assert len(prompts) >= 1
        assert "a" in prompts[-1]

    def test_prompt_caching_prevents_duplicate_redraws(self):
        """Test that identical prompts aren't redrawn."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type one character
        sim.process_key("a")
        initial_clears = sim.prompts_cleared

        # Simulate timeout with clear_prompt_on_timeout=False
        # This should NOT cause a redraw since buffer hasn't changed
        sim.handle_timeout(clear_on_timeout=False)

        # Clears should be unchanged
        assert sim.prompts_cleared == initial_clears


# ============================================================================
# TESTS - OFFLINE MESSAGE DELIVERY
# ============================================================================


class TestOfflineMessageDelivery:
    """Test message delivery when user is offline."""

    def test_unread_count_displayed_in_status(self):
        """Test that unread count appears in status bar."""
        config = DemoConfig(moniker="bob")
        sim = LoopStateSimulator(config)

        # Simulate status update with 3 unread messages
        sim.update_status(3)

        # Status bar should show "F2: Messages (3)"
        status_updates = sim.status_updates
        assert len(status_updates) > 0
        assert status_updates[-1] == (3, "F2: Messages (3)")

    def test_f2_clears_and_resets_buffer(self):
        """Test that F2 key clears buffer and resets caching."""
        config = DemoConfig(moniker="bob")
        sim = LoopStateSimulator(config)

        # Type something then F2
        sim.process_key("t")
        sim.process_key("e")
        sim.process_key("s")
        initial_clears = sim.prompts_cleared

        # Press F2
        sim.handle_f2()

        # Buffer should be cleared
        assert sim.buffer == ""
        # Clears should have incremented
        assert sim.prompts_cleared > initial_clears

    def test_unread_count_zero_shows_no_status(self):
        """Test that zero unread messages don't show in status."""
        config = DemoConfig(moniker="bob")
        sim = LoopStateSimulator(config)

        # Update with 0 messages
        sim.update_status(0)

        # Status text should be empty
        status_updates = sim.status_updates
        assert status_updates[-1] == (0, "")


# ============================================================================
# TESTS - TIMEOUT BEHAVIOR
# ============================================================================


class TestTimeoutBehavior:
    """Test behavior when getch_str times out."""

    def test_timeout_with_clear_prompt_on_timeout_false(self):
        """Test that prompt stays visible when clear_prompt_on_timeout=False."""
        config = DemoConfig(
            moniker="alice",
            check_timeout=1,
            clear_prompt_on_timeout=False,
        )
        sim = LoopStateSimulator(config)

        # Type something
        sim.process_key("a")
        initial_clears = sim.prompts_cleared

        # Simulate timeout with clear_prompt_on_timeout=False
        sim.handle_timeout(clear_on_timeout=False)

        # Clears should NOT have increased
        assert sim.prompts_cleared == initial_clears

    def test_timeout_with_clear_prompt_on_timeout_true(self):
        """Test that prompt is cleared when clear_prompt_on_timeout=True."""
        config = DemoConfig(
            moniker="alice",
            check_timeout=1,
            clear_prompt_on_timeout=True,
        )
        sim = LoopStateSimulator(config)

        # Type something
        sim.process_key("a")
        initial_clears = sim.prompts_cleared

        # Simulate timeout with clear_prompt_on_timeout=True
        sim.handle_timeout(clear_on_timeout=True)

        # Clears SHOULD have increased
        assert sim.prompts_cleared > initial_clears


# ============================================================================
# TESTS - FUNCTIONAL HELPERS
# ============================================================================


class TestFunctionalHelpers:
    """Test the functional helper functions used in the loop."""

    def test_handle_character_input_regular_char(self):
        """Test handle_character_input with regular character."""
        buffer = "hel"
        new_buffer = handle_character_input("l", buffer)
        assert new_buffer == "hell"

    def test_handle_character_input_backspace(self):
        """Test handle_character_input with backspace."""
        buffer = "hello"
        new_buffer = handle_character_input("KEY_BACKSPACE", buffer)
        assert new_buffer == "hell"

    def test_handle_character_input_backspace_empty(self):
        """Test handle_character_input backspace on empty buffer."""
        buffer = ""
        new_buffer = handle_character_input("KEY_BACKSPACE", buffer)
        assert new_buffer == ""

    def test_handle_character_input_escape(self):
        """Test handle_character_input with ESC key."""
        buffer = "hello"
        new_buffer = handle_character_input("KEY_ESC", buffer)
        assert new_buffer == ""

    def test_handle_character_input_invalid_char(self):
        """Test handle_character_input rejects invalid characters."""
        buffer = "test"
        # Try to add a control character (should be ignored)
        new_buffer = handle_character_input("\x00", buffer)
        # Buffer should remain unchanged
        assert new_buffer == "test"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestInteractiveIntegration:
    """Integration tests combining multiple features."""

    def test_send_message_from_interactive_input(self):
        """Test building up a message from interactive input."""
        config = DemoConfig(moniker="bob")
        sim = LoopStateSimulator(config)

        # Type "@alice hello"
        for char in "@alice hello":
            sim.process_key(char)

        # Buffer should contain the full message
        assert sim.buffer == "@alice hello"
        # Should have multiple prompts showing progress
        assert len(sim.prompts_shown) > 0

    def test_multiple_messages_sequence(self):
        """Test sending multiple messages in sequence."""
        config = DemoConfig(moniker="charlie")
        sim = LoopStateSimulator(config)

        # Send first message
        for char in "@alice hi":
            sim.process_key(char)
        msg1 = sim.handle_enter()
        assert msg1 == "@alice hi"

        # Send second message
        for char in "@bob hello":
            sim.process_key(char)
        msg2 = sim.handle_enter()
        assert msg2 == "@bob hello"

        # Buffer should be empty after both messages
        assert sim.buffer == ""

    def test_mixed_operations_sequence(self):
        """Test mixed operations: type, backspace, F2, type again."""
        config = DemoConfig(moniker="alice")
        sim = LoopStateSimulator(config)

        # Type message
        for char in "hello world":
            sim.process_key(char)
        assert sim.buffer == "hello world"

        # Press F2 (displays messages and clears)
        sim.handle_f2()
        assert sim.buffer == ""

        # Type new message
        for char in "new message":
            sim.process_key(char)
        assert sim.buffer == "new message"

        # Process it
        cmd = sim.handle_enter()
        assert cmd == "new message"
        assert sim.buffer == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
