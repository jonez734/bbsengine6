# test_notify_message_demo.py
# Comprehensive tests for notify message demo system

import subprocess
import sys
import threading
from unittest.mock import patch

import pytest

# Add examples path to import the demo
sys.path.insert(0, "/home/opencode/data/work/bbsengine6/py/src/bbsengine6/examples")

from notify_message_demo import (
    AsciiValidator,
    DemoConfig,
    EchoProcessor,
    MessageHandler,
    NotifyMessageDemo,
    TemplateEngine,
)


# ============================================================================
# ASCII VALIDATOR TESTS
# ============================================================================


class TestAsciiValidator:
    """Tests for ASCII character validation."""

    def test_valid_printable_ascii(self):
        """Test valid printable ASCII characters."""
        valid_strings = [
            "Hello World",
            "test@example.com",
            "123-456-7890",
            "!@#$%^&*()",
            "Special chars: ~`|\\",
            "Numbers: 0123456789",
        ]
        for s in valid_strings:
            assert AsciiValidator.is_valid_string(s), f"Should be valid: {s}"

    def test_invalid_control_characters(self):
        """Test that control characters are rejected."""
        invalid_strings = [
            "Hello\x00World",  # Null
            "Test\x01Control",  # SOH
            "Tab\tChar",  # Tab
            "New\nLine",  # Newline
            "Carriage\rReturn",  # CR
            "Bell\x07Sound",  # Bell
        ]
        for s in invalid_strings:
            assert not AsciiValidator.is_valid_string(s), (
                f"Should be invalid: {repr(s)}"
            )

    def test_invalid_non_ascii(self):
        """Test that non-ASCII characters are rejected."""
        invalid_strings = [
            "Hello café",  # Unicode
            "Test™",  # Trademark
            "Emoji 😀",  # Emoji
            "中文",  # Chinese
            "Русский",  # Russian
        ]
        for s in invalid_strings:
            assert not AsciiValidator.is_valid_string(s), (
                f"Should be invalid: {repr(s)}"
            )

    def test_empty_string(self):
        """Test empty string is valid."""
        assert AsciiValidator.is_valid_string("")

    def test_boundary_characters(self):
        """Test boundary ASCII characters."""
        # Space (0x20) is minimum valid
        assert AsciiValidator.is_valid_char(" ")

        # Tilde (0x7E) is maximum valid
        assert AsciiValidator.is_valid_char("~")

        # Just before space (0x1F) is invalid
        assert not AsciiValidator.is_valid_char("\x1f")

        # Just after tilde (0x7F) is invalid (DEL)
        assert not AsciiValidator.is_valid_char("\x7f")

    def test_validate_or_raise_valid(self):
        """Test validate_or_raise with valid input."""
        # Should not raise
        AsciiValidator.validate_or_raise("Hello World")
        AsciiValidator.validate_or_raise("Test@123")

    def test_validate_or_raise_invalid(self):
        """Test validate_or_raise with invalid input."""
        with pytest.raises(ValueError, match="Invalid characters"):
            AsciiValidator.validate_or_raise("Hello\nWorld")

        with pytest.raises(ValueError, match="Invalid characters"):
            AsciiValidator.validate_or_raise("Test™")

        with pytest.raises(ValueError, match="Invalid characters"):
            AsciiValidator.validate_or_raise("Café")


# ============================================================================
# TEMPLATE ENGINE TESTS
# ============================================================================


class TestTemplateEngine:
    """Tests for message template system."""

    def test_default_template(self):
        """Test default template format."""
        assert TemplateEngine.DEFAULT_TEMPLATE == "{sender}: {message}"

    def test_template_validation_valid(self):
        """Test validation of valid templates."""
        valid_templates = [
            "{sender}: {message}",
            ">> {message}",
            "{timestamp} - {sender}: {message}",
            "[{sender}] {message}",
            "{message}",
        ]
        for template in valid_templates:
            # Should not raise
            TemplateEngine.validate_template(template)

    def test_template_validation_missing_message(self):
        """Test that templates must contain {message}."""
        with pytest.raises(ValueError, match="must contain {message}"):
            TemplateEngine.validate_template("{sender}: {content}")

    def test_template_validation_max_length(self):
        """Test template length limit."""
        long_template = "{message}" + "x" * 500
        with pytest.raises(ValueError, match="too long"):
            TemplateEngine.validate_template(long_template)

    def test_template_render_simple(self):
        """Test simple template rendering."""
        template = "{sender}: {message}"
        variables = {
            "sender": "alice",
            "message": "Hello Bob",
        }
        result = TemplateEngine.render(template, variables)
        assert result == "alice: Hello Bob"

    def test_template_render_complex(self):
        """Test complex template rendering."""
        template = "[{sender}] {timestamp} -> {message}"
        variables = {
            "sender": "bob",
            "timestamp": "2024-01-01T12:00:00",
            "message": "Test message",
        }
        result = TemplateEngine.render(template, variables)
        assert "[bob]" in result
        assert "2024-01-01T12:00:00" in result
        assert "Test message" in result

    def test_template_render_missing_variable(self):
        """Test rendering with missing variable."""
        template = "{sender}: {message}"
        variables = {"sender": "alice"}  # missing message

        with pytest.raises(ValueError, match="not provided"):
            TemplateEngine.render(template, variables)

    def test_template_render_extra_variables(self):
        """Test rendering with extra variables is OK."""
        template = "{sender}: {message}"
        variables = {
            "sender": "alice",
            "message": "Hello",
            "extra": "value",  # Extra variable
        }
        result = TemplateEngine.render(template, variables)
        assert result == "alice: Hello"

    def test_get_required_variables(self):
        """Test extraction of required variables."""
        template = "[{sender}] {timestamp} - {message}"
        variables = TemplateEngine.get_required_variables(template)
        assert variables == {"sender", "timestamp", "message"}

    def test_get_required_variables_none(self):
        """Test template with no variables."""
        template = "Static message"
        variables = TemplateEngine.get_required_variables(template)
        assert variables == set()


# ============================================================================
# ECHO PROCESSOR TESTS
# ============================================================================


class TestEchoProcessor:
    """Tests for echo command processing."""

    def test_is_echo_command_standard(self):
        """Test detection of standard echo commands."""
        assert EchoProcessor.is_echo_command("echo hello")
        assert EchoProcessor.is_echo_command("echo 'test'")
        assert EchoProcessor.is_echo_command('echo "test message"')
        assert EchoProcessor.is_echo_command("ECHO test")

    def test_is_echo_command_bang_syntax(self):
        """Test detection of !echo syntax."""
        assert EchoProcessor.is_echo_command("!echo hello")
        assert EchoProcessor.is_echo_command("!ECHO test")

    def test_is_not_echo_command(self):
        """Test non-echo commands."""
        assert not EchoProcessor.is_echo_command("cat file")
        assert not EchoProcessor.is_echo_command("ls")
        assert not EchoProcessor.is_echo_command("echo")  # No args
        assert not EchoProcessor.is_echo_command("hello world")

    def test_process_echo_simple(self):
        """Test simple echo command execution."""
        result = EchoProcessor.process_echo("echo hello")
        assert result == "hello"

    def test_process_echo_with_spaces(self):
        """Test echo with spaces."""
        result = EchoProcessor.process_echo("echo 'hello world'")
        # Output includes the quotes
        assert "hello" in result

    def test_process_echo_bang_syntax(self):
        """Test !echo syntax."""
        result = EchoProcessor.process_echo("!echo test")
        assert result == "test"

    def test_process_echo_numbers(self):
        """Test echo with numbers."""
        result = EchoProcessor.process_echo("echo 123456")
        assert "123456" in result

    def test_process_echo_special_chars(self):
        """Test echo with special ASCII chars."""
        result = EchoProcessor.process_echo("echo '!@#$%^&*()'")
        # Should contain at least some of the special chars
        assert any(c in result for c in "!@#$%^&*()")

    def test_process_echo_validation_error(self):
        """Test that invalid ASCII in args raises error."""
        with pytest.raises(ValueError, match="Invalid characters"):
            EchoProcessor.process_echo("echo 'hello™'")

    def test_process_echo_timeout(self):
        """Test echo command timeout handling."""
        # This is a bit tricky - we can't easily timeout echo
        # Just verify the timeout mechanism exists
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("echo", 2)
            with pytest.raises(ValueError, match="timed out"):
                EchoProcessor.process_echo("echo test")


# ============================================================================
# DEMO CONFIG TESTS
# ============================================================================


class TestDemoConfig:
    """Tests for demo configuration."""

    def test_config_valid(self):
        """Test valid configuration."""
        config = DemoConfig(moniker="alice")
        config.validate()  # Should not raise

    def test_config_custom_template(self):
        """Test config with custom template."""
        config = DemoConfig(
            moniker="bob",
            template=">> {message}",
        )
        config.validate()
        assert config.template == ">> {message}"

    def test_config_invalid_moniker_empty(self):
        """Test that empty moniker is invalid."""
        config = DemoConfig(moniker="")
        with pytest.raises(ValueError, match="Invalid moniker"):
            config.validate()

    def test_config_invalid_moniker_too_long(self):
        """Test that very long moniker is invalid."""
        config = DemoConfig(moniker="a" * 100)
        with pytest.raises(ValueError, match="Invalid moniker"):
            config.validate()

    def test_config_invalid_moniker_non_ascii(self):
        """Test that non-ASCII moniker is invalid."""
        config = DemoConfig(moniker="café")
        with pytest.raises(ValueError, match="Invalid characters"):
            config.validate()

    def test_config_invalid_template(self):
        """Test that invalid template is caught."""
        config = DemoConfig(
            moniker="alice",
            template="No message variable here",
        )
        with pytest.raises(ValueError, match="must contain"):
            config.validate()

    def test_config_invalid_max_messages(self):
        """Test that invalid max_messages is caught."""
        config = DemoConfig(moniker="alice", max_messages=0)
        with pytest.raises(ValueError, match="max_messages must be >= 1"):
            config.validate()

    def test_config_invalid_timeout(self):
        """Test that invalid timeout is caught."""
        config = DemoConfig(moniker="alice", check_timeout=-1)
        with pytest.raises(ValueError, match="check_timeout must be > 0"):
            config.validate()


# ============================================================================
# MESSAGE HANDLER TESTS
# ============================================================================


class TestMessageHandler:
    """Tests for message handling and statistics."""

    @pytest.fixture
    def handler(self):
        """Create a message handler instance."""
        config = DemoConfig(moniker="alice")
        handler = MessageHandler(config)
        return handler

    def test_handler_initialization(self, handler):
        """Test handler initialization."""
        assert handler.config.moniker == "alice"
        assert handler.stats["sent"] == 0
        assert handler.stats["received"] == 0
        assert handler.stats["errors"] == 0

    def test_send_message_valid(self, handler):
        """Test sending a valid message."""
        handler.send_message("Hello Bob", "bob")
        assert handler.stats["sent"] == 1
        assert len(handler.message_history) == 1

    def test_send_message_invalid_ascii(self, handler):
        """Test that non-ASCII message is rejected."""
        with pytest.raises(ValueError, match="Invalid characters"):
            handler.send_message("Hello™", "bob")
        assert handler.stats["errors"] == 1

    def test_send_message_too_long(self, handler):
        """Test that very long message is rejected."""
        with pytest.raises(ValueError, match="too long"):
            handler.send_message("a" * 600, "bob")
        assert handler.stats["errors"] == 1

    def test_send_message_with_echo(self, handler):
        """Test sending message with echo command."""
        handler.send_message("echo test", "bob")
        assert handler.stats["sent"] == 1

    def test_get_stats(self, handler):
        """Test getting statistics."""
        handler.send_message("Test 1", "bob")
        handler.send_message("Test 2", "bob")

        stats = handler.get_stats()
        assert stats["sent"] == 2
        assert stats["received"] == 0

    def test_get_history(self, handler):
        """Test getting message history."""
        handler.send_message("Message 1", "bob")
        handler.send_message("Message 2", "bob")

        history = handler.get_history()
        assert len(history) == 2
        assert all(msg["direction"] == "out" for msg in history)

    def test_history_respects_max_length(self):
        """Test that history respects max_messages limit."""
        config = DemoConfig(moniker="alice", max_messages=5)
        handler = MessageHandler(config)

        # Send 10 messages
        for i in range(10):
            handler.send_message(f"Message {i}", "bob")

        # History should only have last 5
        history = handler.get_history()
        assert len(history) == 5

    def test_thread_safety(self, handler):
        """Test that handler is thread-safe."""
        errors = []

        def send_messages(count):
            try:
                for i in range(count):
                    handler.send_message(f"Message {i}", "bob")
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=send_messages, args=(10,)) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert handler.stats["sent"] == 30


# ============================================================================
# NOTIFY MESSAGE DEMO TESTS
# ============================================================================


class TestNotifyMessageDemo:
    """Tests for the main demo runner."""

    @pytest.fixture
    def demo(self):
        """Create a demo instance."""
        config = DemoConfig(moniker="alice")
        demo = NotifyMessageDemo(config)
        return demo

    def test_demo_initialization(self, demo):
        """Test demo initialization."""
        assert demo.config.moniker == "alice"
        assert demo.handler is not None

    def test_demo_config_validation_required(self):
        """Test that demo validates config."""
        config = DemoConfig(moniker="")
        with pytest.raises(ValueError, match="Invalid moniker"):
            NotifyMessageDemo(config)

    def test_show_stats(self, demo):
        """Test that stats can be displayed."""
        demo.handler.send_message("Test", "bob")
        # Should not raise
        demo._show_stats()

    def test_process_input_send_message(self, demo):
        """Test processing @user message input."""
        demo._process_input("@bob Hello there")
        assert demo.handler.stats["sent"] == 1

    def test_process_input_send_message_invalid(self, demo):
        """Test that invalid message format is rejected."""
        with pytest.raises(ValueError, match="Usage"):
            demo._process_input("@bob")  # No message

    def test_process_input_stats_command(self, demo):
        """Test stats command."""
        # Should not raise
        demo._process_input("stats")

    def test_process_input_unknown_command(self, demo):
        """Test unknown command rejection."""
        with pytest.raises(ValueError, match="Unknown command"):
            demo._process_input("invalid_command")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestIntegration:
    """Integration tests for message exchange."""

    def test_two_way_messaging(self):
        """Test messages can flow both ways."""
        alice_config = DemoConfig(moniker="alice")
        alice = NotifyMessageDemo(alice_config, None)

        bob_config = DemoConfig(moniker="bob")
        bob = NotifyMessageDemo(bob_config, None)

        # Alice sends to Bob
        alice.handler.send_message("Hello Bob", "bob")
        assert alice.handler.stats["sent"] == 1

        # Bob sends to Alice
        bob.handler.send_message("Hi Alice", "alice")
        assert bob.handler.stats["sent"] == 1

    def test_custom_templates(self):
        """Test different templates for each user."""
        alice_config = DemoConfig(
            moniker="alice",
            template="Alice: {message}",
        )
        alice = NotifyMessageDemo(alice_config)

        bob_config = DemoConfig(
            moniker="bob",
            template="[BOB] {message}",
        )
        bob = NotifyMessageDemo(bob_config)

        assert alice.config.template == "Alice: {message}"
        assert bob.config.template == "[BOB] {message}"

    def test_message_history(self):
        """Test message history tracking."""
        config = DemoConfig(moniker="alice")
        demo = NotifyMessageDemo(config)

        demo.handler.send_message("Message 1", "bob")
        demo.handler.send_message("Message 2", "bob")

        history = demo.handler.get_history()
        assert len(history) == 2
        assert all(msg["direction"] == "out" for msg in history)

    def test_echo_in_message(self):
        """Test echo command in message."""
        config = DemoConfig(moniker="alice", enable_echo_commands=True)
        demo = NotifyMessageDemo(config)

        demo.handler.send_message("echo 'test output'", "bob")
        assert demo.handler.stats["sent"] == 1

    def test_echo_disabled(self):
        """Test behavior when echo is disabled."""
        config = DemoConfig(moniker="alice", enable_echo_commands=False)
        demo = NotifyMessageDemo(config)

        # Message containing echo should be sent as-is
        demo.handler.send_message("echo test", "bob")
        assert demo.handler.stats["sent"] == 1


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_message(self):
        """Test behavior with empty message."""
        config = DemoConfig(moniker="alice")
        demo = NotifyMessageDemo(config)

        # Empty string should be valid ASCII
        demo.handler.send_message("", "bob")
        assert demo.handler.stats["sent"] == 1

    def test_max_length_message(self):
        """Test message exactly at max length."""
        config = DemoConfig(moniker="alice")
        demo = NotifyMessageDemo(config)

        # 500 chars is the limit
        message = "a" * 500
        demo.handler.send_message(message, "bob")
        assert demo.handler.stats["sent"] == 1

    def test_all_printable_ascii_range(self):
        """Test all printable ASCII characters."""
        config = DemoConfig(moniker="alice")
        demo = NotifyMessageDemo(config)

        # Create message with all printable ASCII (0x20-0x7E)
        all_ascii = "".join(chr(i) for i in range(0x20, 0x7F))
        demo.handler.send_message(all_ascii, "bob")
        assert demo.handler.stats["sent"] == 1

    def test_special_chars_in_template(self):
        """Test templates with special characters."""
        config = DemoConfig(
            moniker="alice",
            template=">> {sender} says: {message} <<",
        )
        config.validate()  # Should not raise

    def test_template_with_duplicated_variables(self):
        """Test template with repeated variable usage."""
        config = DemoConfig(
            moniker="alice",
            template="{message} - ECHO: {message}",
        )
        config.validate()

        variables = {"message": "Hello", "sender": "alice"}
        result = TemplateEngine.render(config.template, variables)
        assert "Hello - ECHO: Hello" == result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
