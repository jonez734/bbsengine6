"""inputstring(show_bottombar=...) controls only whether the bottom bar is painted.

The bar paints the bottombarcolor background (bggray, 152,152,152) at the bottom row. With the
default the prompt paints it; with show_bottombar=False it does not, and the typed text still returns.
"""

import importlib
from unittest.mock import patch

import pytest

inp = importlib.import_module("bbsengine6.io.inputstring")
BAR_GRAY = b"\x1b[48;2;152;152;152m"

# Reuse the pty fixture from the editing tests so these run on a real terminal.
from tests.test_inputstring_editing import term  # noqa: F401,E402


@pytest.mark.unit
def test_default_paints_the_bottombar(term):
    result, out = term([b"ok\r"], lambda: inp.inputstring("prompt: ", ""))
    assert result == "ok"
    assert BAR_GRAY in out, "the default should paint the bottom bar"


@pytest.mark.unit
def test_show_bottombar_false_does_not_paint_the_bar(term):
    result, out = term([b"ok\r"], lambda: inp.inputstring("prompt: ", "", show_bottombar=False))
    assert result == "ok"
    assert BAR_GRAY not in out, "show_bottombar=False must not paint the bottom bar"


@pytest.mark.unit
def test_show_bottombar_false_still_returns_typed_text(term):
    result, _ = term([b"hello\r"], lambda: inp.inputstring("name: ", "", show_bottombar=False))
    assert result == "hello"


@pytest.mark.unit
def test_show_bottombar_false_skips_the_setbottombar_call(term):
    bb = importlib.import_module("bbsengine6.bottombar")
    with patch.object(bb, "setbottombar") as sb:
        term([b"x\r"], lambda: inp.inputstring("p: ", "", show_bottombar=False))
    sb.assert_not_called()
