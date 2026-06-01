"""
Comprehensive tests for bbsengine6.io.screen module.

Tests cover:
- screen._bottombar_fragments list operations (append, remove, clear, iteration)
- register_bottombar_fragment / unregister_bottombar_fragment functions
- _render_bottombar_fragments internal function
- setbottombar with various left/right/stack combinations
- Backwards compatibility with explicit right parameter
- Edge cases: empty stack, None items, single item, multiple items
- Callables vs strings in the stack
"""

import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, "py/src")

from bbsengine6.io import screen
from bbsengine6.io.screen import (
    register_bottombar_fragment,
    unregister_bottombar_fragment,
    _render_bottombar_fragments,
    setbottombar,
    bottombarstack,
)


@pytest.fixture(autouse=True)
def clean_fragments():
    """Clean _bottombar_fragments before and after each test."""
    screen._bottombar_fragments.clear()
    yield
    screen._bottombar_fragments.clear()


class TestBottombarFragmentsListOperations:
    """Test _bottombar_fragments as a plain list with standard operations."""

    def test_is_list(self):
        """Verify _bottombar_fragments is a standard Python list."""
        assert isinstance(screen._bottombar_fragments, list)

    def test_append_string(self):
        """Test appending a string to _bottombar_fragments."""
        screen._bottombar_fragments.append("test item")
        assert "test item" in screen._bottombar_fragments

    def test_append_callable(self):
        """Test appending a callable to _bottombar_fragments."""

        def func(**kw):
            return "dynamic"

        screen._bottombar_fragments.append(func)
        assert func in screen._bottombar_fragments

    def test_remove_item(self):
        """Test removing an item from _bottombar_fragments."""
        screen._bottombar_fragments.append("item1")
        screen._bottombar_fragments.append("item2")
        screen._bottombar_fragments.remove("item1")
        assert "item1" not in screen._bottombar_fragments
        assert "item2" in screen._bottombar_fragments

    def test_clear_fragments(self):
        """Test clearing the entire list."""
        screen._bottombar_fragments.append("item1")
        screen._bottombar_fragments.append("item2")
        screen._bottombar_fragments.append(lambda **kw: "x")
        screen._bottombar_fragments.clear()
        assert len(screen._bottombar_fragments) == 0

    def test_iteration_order(self):
        """Test that iteration follows insertion order."""
        items = ["first", "second", "third"]
        for item in items:
            screen._bottombar_fragments.append(item)
        assert list(screen._bottombar_fragments) == items

    def test_duplicate_prevention(self):
        """Test that same item can be added multiple times (list behavior)."""
        screen._bottombar_fragments.append("item")
        screen._bottombar_fragments.append("item")
        assert screen._bottombar_fragments.count("item") == 2

    def test_len_after_operations(self):
        """Test len() reflects correct count."""
        assert len(screen._bottombar_fragments) == 0
        screen._bottombar_fragments.append("a")
        screen._bottombar_fragments.append("b")
        assert len(screen._bottombar_fragments) == 2
        screen._bottombar_fragments.remove("a")
        assert len(screen._bottombar_fragments) == 1

    def test_contains_check(self):
        """Test 'in' operator for membership check."""
        screen._bottombar_fragments.append("present")
        assert "present" in screen._bottombar_fragments
        assert "absent" not in screen._bottombar_fragments

    def test_pop_last_item(self):
        """Test popping the last item."""
        screen._bottombar_fragments.append("first")
        screen._bottombar_fragments.append("second")
        popped = screen._bottombar_fragments.pop()
        assert popped == "second"
        assert len(screen._bottombar_fragments) == 1


class TestRegisterUnregisterBottombar:
    """Test register_bottombar_fragment and unregister_bottombar_fragment functions."""

    def test_register_adds_to_stack(self):
        """Test that register_bottombar_fragment adds item to stack."""
        register_bottombar_fragment("test")
        assert "test" in screen._bottombar_fragments

    def test_register_returns_item(self):
        """Test that register_bottombar_fragment returns the registered item."""
        result = register_bottombar_fragment("test")
        assert result == "test"

    def test_register_callable(self):
        """Test registering a callable."""

        def func(**kw):
            return "result"

        result = register_bottombar_fragment(func)
        assert result is func
        assert func in screen._bottombar_fragments

    def test_register_no_duplicates(self):
        """Test that register_bottombar_fragment prevents duplicates."""
        register_bottombar_fragment("unique")
        register_bottombar_fragment("unique")  # Should not add again
        assert screen._bottombar_fragments.count("unique") == 1

    def test_register_lambda(self):
        """Test registering a lambda function."""

        def lam(**kw):
            return "lambda result"

        register_bottombar_fragment(lam)
        assert lam in screen._bottombar_fragments

    def test_unregister_removes_from_stack(self):
        """Test that unregister_bottombar_fragment removes item."""
        register_bottombar_fragment("to_remove")
        result = unregister_bottombar_fragment("to_remove")
        assert result is True
        assert "to_remove" not in screen._bottombar_fragments

    def test_unregister_returns_true_on_success(self):
        """Test unregister returns True when item found."""
        register_bottombar_fragment("exists")
        result = unregister_bottombar_fragment("exists")
        assert result is True

    def test_unregister_returns_false_when_not_found(self):
        """Test unregister returns False when item not in stack."""
        result = unregister_bottombar_fragment("nonexistent")
        assert result is False

    def test_unregister_callable(self):
        """Test unregistering a callable."""

        def func(**kw):
            return "x"

        register_bottombar_fragment(func)
        result = unregister_bottombar_fragment(func)
        assert result is True
        assert func not in screen._bottombar_fragments

    def test_register_unregister_roundtrip(self):
        """Test adding and removing same item multiple times."""
        item = "roundtrip"
        register_bottombar_fragment(item)
        assert item in screen._bottombar_fragments
        unregister_bottombar_fragment(item)
        assert item not in screen._bottombar_fragments
        register_bottombar_fragment(item)
        assert item in screen._bottombar_fragments


class TestRenderRightstack:
    """Test _render_bottombar_fragments internal function."""

    def test_empty_stack_returns_empty_string(self):
        """Test that empty stack returns empty string."""
        result = _render_bottombar_fragments()
        assert result == ""

    def test_single_string(self):
        """Test rendering single string item."""
        screen._bottombar_fragments.append("single")
        result = _render_bottombar_fragments()
        assert result == "single"

    def test_single_string_no_pipe(self):
        """Test single item does NOT get pipe separator."""
        screen._bottombar_fragments.append("alone")
        result = _render_bottombar_fragments()
        assert result == "alone"
        assert "|" not in result

    def test_multiple_strings_joined_with_pipe(self):
        """Test multiple strings are joined with ' | '."""
        screen._bottombar_fragments.append("item1")
        screen._bottombar_fragments.append("item2")
        screen._bottombar_fragments.append("item3")
        result = _render_bottombar_fragments()
        assert result == "item1 | item2 | item3"

    def test_callable_invoked_with_kwargs(self):
        """Test that callables receive **kwargs."""
        received_kwargs = {}

        def capture_kwargs(**kwargs):
            received_kwargs.update(kwargs)
            return "captured"

        screen._bottombar_fragments.append(capture_kwargs)
        _render_bottombar_fragments(foo="bar", baz=123)
        assert received_kwargs == {"foo": "bar", "baz": 123}

    def test_callable_returns_string(self):
        """Test callable returning a string."""
        screen._bottombar_fragments.append(lambda **kw: "from callable")
        result = _render_bottombar_fragments()
        assert result == "from callable"

    def test_mixed_strings_and_callables(self):
        """Test mixing strings and callables."""
        screen._bottombar_fragments.append("static")
        screen._bottombar_fragments.append(lambda **kw: "dynamic")
        screen._bottombar_fragments.append("another")
        result = _render_bottombar_fragments()
        assert result == "static | dynamic | another"

    def test_none_callable_result_filtered(self):
        """Test that None returned from callable is not added."""

        def returns_none(**kw):
            return None

        screen._bottombar_fragments.append("valid")
        screen._bottombar_fragments.append(returns_none)
        result = _render_bottombar_fragments()
        assert result == "valid"

    def test_empty_string_callable_result_filtered(self):
        """Test that empty string from callable is not added."""

        def returns_empty(**kw):
            return ""

        screen._bottombar_fragments.append("valid")
        screen._bottombar_fragments.append(returns_empty)
        screen._bottombar_fragments.append("after")
        result = _render_bottombar_fragments()
        assert result == "valid | after"

    def test_none_in_stack_filtered(self):
        """Test that None in stack is filtered out."""
        screen._bottombar_fragments.append("before")
        screen._bottombar_fragments.append(None)
        screen._bottombar_fragments.append("after")
        result = _render_bottombar_fragments()
        assert result == "before | after"

    def test_empty_string_in_stack_filtered(self):
        """Test that empty string in stack is filtered out."""
        screen._bottombar_fragments.append("first")
        screen._bottombar_fragments.append("")
        screen._bottombar_fragments.append("last")
        result = _render_bottombar_fragments()
        assert result == "first | last"

    def test_notification_status_prepended(self):
        """Test that notification status is prepended when present."""
        screen._bottombar_fragments.append("module status")

        with patch("bbsengine6.io.screen.get_notification_status") as mock_notif:
            mock_notif.return_value = "F2: notify (5)"
            result = _render_bottombar_fragments()

        assert result == "F2: notify (5) | module status"

    def test_notification_empty_not_added(self):
        """Test that empty notification status doesn't add prefix."""
        screen._bottombar_fragments.append("module status")

        with patch("bbsengine6.io.screen.get_notification_status") as mock_notif:
            mock_notif.return_value = ""
            result = _render_bottombar_fragments()

        assert result == "module status"
        assert "|" not in result

    def test_notification_before_all_items(self):
        """Test notification is always first in output."""
        screen._bottombar_fragments.append("item1")
        screen._bottombar_fragments.append("item2")

        with patch("bbsengine6.io.screen.get_notification_status") as mock_notif:
            mock_notif.return_value = "F2: notify (1)"
            result = _render_bottombar_fragments()

        assert result.startswith("F2: notify (1)")
        assert result == "F2: notify (1) | item1 | item2"

    def test_exception_in_callable_caught(self):
        """Test that exceptions in callables are caught gracefully."""

        def bad_callable(**kw):
            raise RuntimeError("test error")

        screen._bottombar_fragments.append(bad_callable)
        screen._bottombar_fragments.append("after error")

        # Should not raise, should continue with other items
        result = _render_bottombar_fragments()
        assert result == "after error"

    def test_callable_returning_non_string(self):
        """Test callable returning non-string is converted."""

        def returns_int(**kw):
            return 42

        screen._bottombar_fragments.append(returns_int)
        result = _render_bottombar_fragments()
        assert result == "42"


class TestSetbottombarWithStack:
    """Test setbottombar behavior with screen._bottombar_fragments."""

    def test_empty_stack_no_right(self):
        """Test setbottombar with empty stack and no right param."""
        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("left side")
            # Should not crash even with empty stack

    def test_stack_populates_right_when_none(self):
        """Test that stack items appear when right is None."""
        screen._bottombar_fragments.append("stack item 1")
        screen._bottombar_fragments.append("stack item 2")

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left")
            call_args = mock_update.call_args[0][0]
            assert "stack item 1 | stack item 2" in call_args

    def test_explicit_right_overrides_stack(self):
        """Test that explicit right parameter overrides stack."""
        screen._bottombar_fragments.append("from stack")
        screen._bottombar_fragments.append("also from stack")

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left", "explicit right")
            call_args = mock_update.call_args[0][0]
            assert "explicit right" in call_args
            assert "from stack" not in call_args

    def test_explicit_callable_right_overrides_stack(self):
        """Test that explicit callable right overrides stack."""
        screen._bottombar_fragments.append("from stack")

        def explicit_callable(**kw):
            return "explicit callable result"

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left", explicit_callable)
            call_args = mock_update.call_args[0][0]
            assert "explicit callable result" in call_args
            assert "from stack" not in call_args

    def test_stack_with_callable(self):
        """Test stack items that are callables are invoked."""

        def dynamic_item(**kw):
            return "generated at " + kw.get("time", "runtime")

        screen._bottombar_fragments.append(dynamic_item)

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left", time="noon")
            call_args = mock_update.call_args[0][0]
            assert "generated at noon" in call_args

    def test_stack_left_still_works(self):
        """Test that left side works independently of stack."""
        screen._bottombar_fragments.append("right item")

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left side")
            call_args = mock_update.call_args[0][0]
            assert "left side" in call_args
            assert "right item" in call_args

    def test_callable_left_still_works(self):
        """Test that callable left side works with stack."""

        def left_func(**kw):
            return "left from callable"

        screen._bottombar_fragments.append("right item")

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar(left_func)
            call_args = mock_update.call_args[0][0]
            assert "left from callable" in call_args

    def test_both_left_and_right_callable(self):
        """Test callable on both left and right (via stack)."""

        def left_func(**kw):
            return "left result"

        def right_func(**kw):
            return "right result"

        screen._bottombar_fragments.append(right_func)

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar(left_func, time="test")
            call_args = mock_update.call_args[0][0]
            assert "left result" in call_args
            assert "right result" in call_args


class TestSetbottombarBackwardsCompat:
    """Test backwards compatibility with old setbottombar usage."""

    def test_left_string_right_none(self):
        """Traditional usage: left string, no right."""
        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("menu")
            call_args = mock_update.call_args[0][0]
            assert "menu" in call_args

    def test_left_string_right_string(self):
        """Traditional usage: both strings."""
        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left", "right")
            call_args = mock_update.call_args[0][0]
            assert "left" in call_args
            assert "right" in call_args

    def test_left_string_right_callable(self):
        """Traditional usage: left string, right callable."""

        def right_func(**kw):
            return "dynamic right"

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("left", right_func)
            call_args = mock_update.call_args[0][0]
            assert "left" in call_args
            assert "dynamic right" in call_args

    def test_kwargs_passed_to_left_callable(self):
        """Test kwargs are passed to left callable."""
        received = {}

        def left_func(**kw):
            received.update(kw)
            return "left"

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar(left_func, player="TestPlayer")

        assert received.get("player") == "TestPlayer"

    def test_kwargs_passed_to_right_callable(self):
        """Test kwargs are passed to right callable."""
        received = {}

        def right_func(**kw):
            received.update(kw)
            return "right"

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("left", right_func, game_id=42)

        assert received.get("game_id") == 42

    def test_kwargs_passed_to_stack_callables(self):
        """Test kwargs are passed to stack callables."""
        received_kwargs = []

        def capture1(**kw):
            received_kwargs.append(("func1", kw))
            return "f1"

        def capture2(**kw):
            received_kwargs.append(("func2", kw))
            return "f2"

        screen._bottombar_fragments.append(capture1)
        screen._bottombar_fragments.append(capture2)

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("left", foo="bar", count=5)

        assert ("func1", {"foo": "bar", "count": 5}) in received_kwargs
        assert ("func2", {"foo": "bar", "count": 5}) in received_kwargs


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_string_in_stack(self):
        """Test handling of very long string in stack."""
        long_string = "x" * 1000
        screen._bottombar_fragments.append(long_string)

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("short left")
            # Should not crash

    def test_special_characters_in_strings(self):
        """Test special characters are preserved."""
        screen._bottombar_fragments.append("pipe: | and backslash: \\")
        result = _render_bottombar_fragments()
        assert "pipe: | and backslash: \\" in result

    def test_unicode_in_strings(self):
        """Test unicode characters are preserved."""
        screen._bottombar_fragments.append("Unicode: \u2764 \u2603 \U0001f600")
        result = _render_bottombar_fragments()
        assert "\u2764" in result

    def test_empty_stack_with_explicit_right_none(self):
        """Test empty stack with explicit right=None (should use None, not empty)."""
        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("left", None)
            # Should work, right_buf becomes None

    def test_stack_cleared_between_calls(self):
        """Test that clearing stack between calls works."""
        screen._bottombar_fragments.append("item")

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("first")

        screen._bottombar_fragments.clear()

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            setbottombar("second")
            mock_update.call_args[0][0]
            # Stack is empty, no right-side items

    def test_multiple_registrations_same_callable(self):
        """Test registering same callable multiple times via register_bottombar_fragment."""

        def func(**kw):
            return "test"

        register_bottombar_fragment(func)
        register_bottombar_fragment(func)  # Should not add duplicate

        with patch("bbsengine6.io.screen.updatebottombar"):
            setbottombar("left")

        # Should only appear once
        assert screen._bottombar_fragments.count(func) == 1

    def test_register_in_loop(self):
        """Test registering multiple items in a loop."""
        items = [f"item_{i}" for i in range(5)]
        for item in items:
            register_bottombar_fragment(item)

        assert len(screen._bottombar_fragments) == 5
        assert list(screen._bottombar_fragments) == items


class TestThreadSafety:
    """Test thread safety of screen._bottombar_fragments operations."""

    def test_register_bottombar_fragment_thread_safe(self):
        """Test register is protected by lock."""
        import threading

        errors = []

        def register_items(start, count):
            try:
                for i in range(count):
                    register_bottombar_fragment(f"item_{start + i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_items, args=(i * 100, 50))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(screen._bottombar_fragments) == 200

    def test_unregister_bottombar_fragment_thread_safe(self):
        """Test unregister is protected by lock."""
        import threading

        for i in range(100):
            register_bottombar_fragment(f"item_{i}")

        errors = []

        def unregister_items(start, count):
            try:
                for i in range(count):
                    unregister_bottombar_fragment(f"item_{start + i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=unregister_items, args=(i * 25, 25))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(screen._bottombar_fragments) == 0

    def test_render_bottombar_fragments_thread_safe(self):
        """Test render creates snapshot before iteration."""
        import threading

        register_bottombar_fragment(lambda **kw: "from render")

        results = []
        errors = []

        def render_and_append():
            try:
                result = _render_bottombar_fragments()
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=render_and_append) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        for result in results:
            assert "from render" in result


class TestBottombarstackUnaffected:
    """Ensure existing bottombarstack is not broken."""

    def test_bottombarstack_still_works(self):
        """Test that popbottombar still works."""
        bottombarstack.append("old item")

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            screen.popbottombar()
            call_args = mock_update.call_args[0][0]
            assert "old item" in call_args

    def test_bottombarstack_pop(self):
        """Test pop from bottombarstack."""
        bottombarstack.append("first")
        bottombarstack.append("second")

        popped = bottombarstack.pop()
        assert popped == "second"
        assert len(bottombarstack) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
