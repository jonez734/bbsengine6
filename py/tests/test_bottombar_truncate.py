"""
Regression tests for Phase 4 bottombar.py hardening.

Covers:
- _render_bottombar does not produce a negative slice when left_buf is
  longer than the available terminal width.
- Truncate math respects max(0, ...) so truncation never crashes on
  narrow terminals.
- Padding length is clamped with max(0, ...) so terminalwidth - left_len
  - right_len can never be negative.
"""

from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


def _build_bottombar(width: int):
    """Build a bottombar module reference and stubs for bb.echo / bb.terminal.

    bottombar.py imports echo directly via `from .io.echo import echo`, so
    the live binding lives on the bottombar module itself. Patching
    bbsengine6.io.echo.echo would have no effect — we must patch
    bbsengine6.bottombar.echo.
    """
    from bbsengine6 import bottombar

    captured = {"calls": []}

    def fake_echo(s, **kwargs):
        captured["calls"].append(s)

    def fake_width():
        return width

    def fake_lines():
        return 24

    return bottombar, captured, fake_echo, fake_width, fake_lines


def test_render_bottombar_does_not_crash_on_narrow_terminal():
    """When left_buf exceeds the available terminal width, the truncate
    math must use max(0, ...) so the slice never goes negative."""
    bb, captured, fake_echo, fake_width, fake_lines = _build_bottombar(width=20)

    registry = bb.FragmentRegistry(name="narrow-test")
    long_left = "x" * 500
    with patch.object(bb, "echo", fake_echo), patch.object(
        bb.terminal, "width", fake_width
    ), patch.object(bb.terminal, "lines", fake_lines):
        # Should not raise even with a long left and a right that pushes
        # past the available width.
        bb._render_bottombar(registry, left=long_left, right="X" * 500)

    assert len(captured["calls"]) == 1, "exactly one echo call expected"


def test_render_bottombar_no_negative_truncate_index():
    """truncate_to must always be >= 0; left_buf[:truncate_to] must not
    raise on tiny terminal widths."""
    bb, captured, fake_echo, fake_width, fake_lines = _build_bottombar(width=5)

    registry = bb.FragmentRegistry(name="tiny")
    long_left = "abcdefghij"  # 10 chars
    with patch.object(bb, "echo", fake_echo), patch.object(
        bb.terminal, "width", fake_width
    ), patch.object(bb.terminal, "lines", fake_lines):
        # Must not raise
        bb._render_bottombar(registry, left=long_left, right="")
    assert len(captured["calls"]) == 1


def test_render_bottombar_padding_is_non_negative():
    """padding = ' ' * max(0, terminalwidth - left_len - right_len)
    so the multiplier can never be negative."""
    bb, captured, fake_echo, fake_width, fake_lines = _build_bottombar(width=10)

    registry = bb.FragmentRegistry(name="pad-test")
    # left + right together exceed terminalwidth → padding must clamp.
    with patch.object(bb, "echo", fake_echo), patch.object(
        bb.terminal, "width", fake_width
    ), patch.object(bb.terminal, "lines", fake_lines):
        bb._render_bottombar(registry, left="x" * 20, right="y" * 20)
    assert len(captured["calls"]) == 1


def test_render_bottombar_short_input_unmodified():
    """When left fits, no '...' truncation marker should be added."""
    bb, captured, fake_echo, fake_width, fake_lines = _build_bottombar(width=80)

    registry = bb.FragmentRegistry(name="short-test")
    with patch.object(bb, "echo", fake_echo), patch.object(
        bb.terminal, "width", fake_width
    ), patch.object(bb.terminal, "lines", fake_lines):
        bb._render_bottombar(registry, left="hi", right="")

    rendered = captured["calls"][0]
    assert "..." not in rendered
    assert "hi" in rendered
