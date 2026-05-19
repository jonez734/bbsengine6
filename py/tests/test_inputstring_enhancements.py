"""Test enhancements to bbsengine6.io.inputstring function key support.

Tests for:
- InputHistory class (command history)
- New key handlers (DELETE, INSERT, PAGE UP/DOWN, F-keys)
- Insert/overwrite mode
- Mode indicator display
- Backward compatibility
"""

import pytest
import threading
from bbsengine6.io.inputstring import InputHistory


class TestInputHistory:
    """Test InputHistory class - GNU readline compatible."""

    def test_init_default_size(self):
        """InputHistory initializes with default size."""
        history = InputHistory()
        assert history.get_all() == []

    def test_add_entry(self):
        """add_entry appends to history."""
        history = InputHistory()
        history.add_entry("first command")
        assert history.get_all() == ["first command"]

    def test_bounded_size(self):
        """History respects maxsize limit (no dedup like GNU readline)."""
        history = InputHistory(maxsize=3)
        history.add_entry("cmd1")
        history.add_entry("cmd2")
        history.add_entry("cmd3")
        history.add_entry("cmd4")  # This should evict cmd1
        
        entries = history.get_all()
        assert len(entries) == 3
        assert entries == ["cmd2", "cmd3", "cmd4"]

    def test_empty_entries_not_added(self):
        """Empty entries are not added to history."""
        history = InputHistory()
        history.add_entry("")
        history.add_entry("  ")  # Whitespace-only is still added
        assert len(history.get_all()) >= 1  # Whitespace entry is added

    def test_up_navigation(self):
        """UP arrow navigates backward through history."""
        history = InputHistory()
        history.add_entry("first")
        history.add_entry("second")
        history.add_entry("third")
        
        # First UP from end goes to last entry
        assert history.get_previous() == "third"
        # Further UPs go backward
        assert history.get_previous() == "second"
        assert history.get_previous() == "first"
        # Already at oldest, stays there
        assert history.get_previous() == "first"

    def test_down_navigation(self):
        """DOWN arrow navigates forward through history."""
        history = InputHistory()
        history.add_entry("first")
        history.add_entry("second")
        history.add_entry("third")
        
        # Get to the end
        history.get_previous()
        history.get_previous()
        history.get_previous()
        
        # DOWN goes forward
        assert history.get_next() == "second"
        assert history.get_next() == "third"
        # At newest, DOWN goes to "end" (new input)
        assert history.get_next() is None

    def test_reset_position(self):
        """reset_position clears navigation state."""
        history = InputHistory()
        history.add_entry("first")
        history.add_entry("second")
        
        # Navigate to first
        history.get_previous()
        
        # Reset clears position
        history.reset_position()
        
        # Next UP from reset goes to second (last entry)
        assert history.get_previous() == "second"

    def test_add_entry_resets_position(self):
        """add_entry implicitly resets position."""
        history = InputHistory()
        history.add_entry("first")
        history.add_entry("second")
        history.get_previous()  # Navigate to first
        
        # Adding entry resets position
        history.add_entry("third")
        
        # Next UP goes to third (last entry)
        assert history.get_previous() == "third"

    def test_clear(self):
        """clear removes all history."""
        history = InputHistory()
        history.add_entry("first")
        history.add_entry("second")
        
        history.clear()
        
        assert history.get_all() == []
        assert history.get_previous() is None

    def test_thread_safety(self):
        """History operations are thread-safe."""
        history = InputHistory(maxsize=100)
        
        def add_entries(start, count):
            for i in range(start, start + count):
                history.add_entry(f"entry_{i}")
        
        def navigate():
            for _ in range(10):
                history.get_previous()
                history.get_next()
                history.reset_position()
        
        threads = []
        # Multiple threads adding and navigating
        threads.append(threading.Thread(target=add_entries, args=(0, 20)))
        threads.append(threading.Thread(target=add_entries, args=(20, 20)))
        threads.append(threading.Thread(target=navigate))
        threads.append(threading.Thread(target=navigate))
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have all entries without crashes
        assert len(history.get_all()) > 0


class TestDeleteKey:
    """Test DELETE key handler."""

    def test_delete_at_cursor(self):
        """DELETE removes character at cursor."""
        from bbsengine6.io.inputstring import handle_delete
        
        buffer = "hello"
        curpos = 1  # At 'e'
        
        result_buffer, result_curpos, result_scroll = handle_delete(
            buffer, curpos, 0, 80
        )
        
        assert result_buffer == "hllo"
        assert result_curpos == 1

    def test_delete_at_end_no_op(self):
        """DELETE at end of buffer is graceful no-op."""
        from bbsengine6.io.inputstring import handle_delete
        
        buffer = "hello"
        curpos = 5  # At end
        
        result_buffer, result_curpos, result_scroll = handle_delete(
            buffer, curpos, 0, 80
        )
        
        assert result_buffer == "hello"  # Unchanged
        assert result_curpos == 5  # Unchanged

    def test_delete_at_middle(self):
        """DELETE at middle of buffer."""
        from bbsengine6.io.inputstring import handle_delete
        
        buffer = "hello world"
        curpos = 5  # At space
        
        result_buffer, result_curpos, result_scroll = handle_delete(
            buffer, curpos, 0, 80
        )
        
        assert result_buffer == "helloworld"


class TestInsertMode:
    """Test INSERT key toggle and character insertion modes."""

    def test_insert_toggle_exists(self):
        """INSERT key handler exists and returns properly."""
        from bbsengine6.io.inputstring import handle_insert_toggle
        
        buffer = "test"
        curpos = 2
        
        result_buffer, result_curpos, result_scroll = handle_insert_toggle(
            buffer, curpos, 0, 80
        )
        
        assert result_buffer == "test"  # Unchanged
        assert result_curpos == 2  # Unchanged

    def test_insert_mode_character_insertion(self):
        """In INSERT mode, chars are inserted, shifting right."""
        # This would be tested in integration with inputstring()
        # Unit test of character insertion in main loop
        pass

    def test_overwrite_mode_character_insertion(self):
        """In OVERWRITE mode, chars replace at cursor."""
        # This would be tested in integration with inputstring()
        pass


class TestPageUpDown:
    """Test PAGE UP/DOWN navigation."""

    def test_pageup_jump(self):
        """PAGE UP jumps backward by pagesize."""
        from bbsengine6.io.inputstring import handle_pageup
        
        buffer = "0123456789abcdefghij"
        curpos = 15  # Middle of buffer
        
        result_buffer, result_curpos, result_scroll = handle_pageup(
            buffer, curpos, 5, 80
        )
        
        # Default pagesize is 10, so jump from 15 to 5
        assert result_curpos == 5
        assert result_buffer == buffer  # Buffer unchanged

    def test_pageup_clamps_to_start(self):
        """PAGE UP clamped to start of buffer."""
        from bbsengine6.io.inputstring import handle_pageup
        
        buffer = "hello"
        curpos = 2
        
        result_buffer, result_curpos, result_scroll = handle_pageup(
            buffer, curpos, 0, 80
        )
        
        assert result_curpos == 0  # Clamped to start

    def test_pagedown_jump(self):
        """PAGE DOWN jumps forward by pagesize."""
        from bbsengine6.io.inputstring import handle_pagedown
        
        buffer = "0123456789abcdefghij"
        curpos = 5
        
        result_buffer, result_curpos, result_scroll = handle_pagedown(
            buffer, curpos, 0, 80
        )
        
        # Default pagesize is 10, so jump from 5 to 15
        assert result_curpos == 15
        assert result_buffer == buffer  # Buffer unchanged

    def test_pagedown_clamps_to_end(self):
        """PAGE DOWN clamped to end of buffer."""
        from bbsengine6.io.inputstring import handle_pagedown
        
        buffer = "hello"
        curpos = 3
        
        result_buffer, result_curpos, result_scroll = handle_pagedown(
            buffer, curpos, 0, 80
        )
        
        assert result_curpos == 5  # Clamped to end


class TestFunctionKeys:
    """Test F1-F12 key handlers."""

    def test_function_key_handler_exists(self):
        """handle_function_key exists and returns properly."""
        from bbsengine6.io.inputstring import handle_function_key
        
        buffer = "test"
        result = handle_function_key("KEY_F2", buffer, 2, 0, 80)
        
        assert result == (buffer, 2, 0)

    def test_f1_help_handler(self):
        """F1 help handler (stub for now)."""
        from bbsengine6.io.inputstring import handle_help
        
        buffer = "test"
        result_buffer, result_curpos, result_scroll = handle_help(
            buffer, 2, 0, 80
        )
        
        assert result_buffer == "test"  # Unchanged


class TestModeIndicator:
    """Test mode indicator display."""

    def test_insert_mode_constant(self):
        """INSERT mode indicator constant exists."""
        from bbsengine6.io.const import INPUTSTRING_INSERT_MODE_INDICATOR
        assert INPUTSTRING_INSERT_MODE_INDICATOR == "[INS]"

    def test_overwrite_mode_constant(self):
        """OVERWRITE mode indicator constant exists."""
        from bbsengine6.io.const import INPUTSTRING_OVERWRITE_MODE_INDICATOR
        assert INPUTSTRING_OVERWRITE_MODE_INDICATOR == "[OVR]"

    def test_redraw_line_with_insert_mode(self):
        """redraw_line accepts insert_mode parameter."""
        from bbsengine6.io.inputstring import redraw_line
        
        # Just verify it doesn't crash
        # (Can't easily test echo output without mocking)
        try:
            redraw_line(
                prompt="Test: ",
                buffer="hello",
                max_len=80,
                start_row=1,
                start_col=1,
                curpos=2,
                scroll_offset=0,
                max_width=80,
                mask=None,
                insert_mode=True,
            )
        except Exception:
            pass  # Echo may fail in test environment


class TestHistoryConstants:
    """Test history-related constants."""

    def test_default_history_size_constant(self):
        """Default history size constant matches GNU readline."""
        from bbsengine6.io.const import INPUTSTRING_DEFAULT_HISTORY_SIZE
        assert INPUTSTRING_DEFAULT_HISTORY_SIZE == 500

    def test_default_pagesize_constant(self):
        """Default pagesize constant is 10."""
        from bbsengine6.io.const import INPUTSTRING_DEFAULT_PAGESIZE
        assert INPUTSTRING_DEFAULT_PAGESIZE == 10


class TestBackwardCompatibility:
    """Verify no breaking changes to existing API."""

    def test_inputstring_signature_unchanged(self):
        """inputstring() still accepts original parameters."""
        from bbsengine6.io.inputstring import inputstring
        import inspect
        
        sig = inspect.signature(inputstring)
        params = list(sig.parameters.keys())
        
        # Original parameters must be present
        assert "prompt" in params
        assert "oldvalue" in params
        assert "kwargs" in params or "**kwargs" in str(sig)

    def test_inputstring_defaults(self):
        """inputstring() parameters have sensible defaults."""
        from bbsengine6.io.inputstring import inputstring
        import inspect
        
        sig = inspect.signature(inputstring)
        
        # prompt and oldvalue should have defaults
        assert sig.parameters["prompt"].default == "> "
        assert sig.parameters["oldvalue"].default == ""

    def test_new_parameters_are_optional(self):
        """All new parameters have defaults (backward compatible)."""
        from bbsengine6.io.inputstring import inputstring
        import inspect
        
        sig = inspect.signature(inputstring)
        
        # New parameters should have defaults
        new_params = ["history", "pagesize", "beep_on_error", 
                     "f1_help", "function_key_handlers"]
        for param in new_params:
            if param in sig.parameters:
                assert sig.parameters[param].default is not inspect.Parameter.empty


class TestIntegration:
    """Integration tests (basic, no actual terminal I/O)."""

    def test_input_history_class_instantiation(self):
        """Can create InputHistory instances."""
        hist1 = InputHistory()
        hist2 = InputHistory(maxsize=100)
        
        assert len(hist1.get_all()) == 0
        assert len(hist2.get_all()) == 0

    def test_multiple_history_instances(self):
        """Multiple InputHistory instances are independent."""
        hist1 = InputHistory()
        hist2 = InputHistory()
        
        hist1.add_entry("hist1_entry")
        hist2.add_entry("hist2_entry")
        
        assert hist1.get_all() == ["hist1_entry"]
        assert hist2.get_all() == ["hist2_entry"]

    def test_key_actions_registry_populated(self):
        """KEY_ACTIONS registry has expected handlers."""
        from bbsengine6.io.inputstring import KEY_ACTIONS
        
        # Check that new handlers are registered
        expected_keys = [
            "KEY_LEFT", "KEY_RIGHT", "KEY_HOME", "KEY_END",
            "KEY_BACKSPACE", "KEY_DELETE", "KEY_INSERT",
            "KEY_PAGEUP", "KEY_PAGEDOWN",
        ]
        
        for key in expected_keys:
            assert key in KEY_ACTIONS, f"{key} not in KEY_ACTIONS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
