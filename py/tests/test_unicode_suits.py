"""
Tests for the {u:NAME[:repeat]} unicode namespace and direct {NAME} unicode
commands in bbsengine6.io.echo.

Covers:
- The four card-suit glyphs: {u:spade}, {u:heart}, {u:diamond}, {u:club}.
- Block-element glyphs: {u:solidblock}, {u:lightblock}, {u:mediumblock}.
- Repeat-count support for the namespace: {u:solidblock:2}, {u:solidblock:3}.
- Regression: existing direct-name entries ({dblhline}, {arrow}, ...)
  actually render — historically broken because _handle_unicode checked
  token.kind in _unicode instead of token.value in _unicode.
- Regression: {diamond} still resolves to the ACS ◆ glyph (not the card
  suit ♦) so the two namespaces don't collide.
- Negative: unknown {u:NAME} does not crash.
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

    written["stream"] = buf
    return written


def _strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences so tests can compare rendered glyphs only.

    Strips both CSI sequences (ESC [ ... final-byte) and SCS sequences
    (ESC ( X) — the latter is what `_acs_off()` emits to leave the
    alternate character set.
    """
    import re

    csi = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", s)
    scs = re.sub(r"\x1b\([\x20-\x7e]", "", csi)
    return scs


class TestSuitsTableContents:
    """The _suits dict must contain the four card-suit glyphs.

    Suits live in their own small table (separate from _unicode) so the
    diamond/ACS-collision story stays clean.
    """

    @pytest.mark.parametrize(
        "name, codepoint",
        [
            ("spade", "\u2660"),
            ("heart", "\u2665"),
            ("diamond", "\u2666"),
            ("club", "\u2663"),
        ],
    )
    def test_suits_entry_present(self, name, codepoint):
        assert name in echo_module._suits, (
            f"{name!r} is missing from bbsengine6.io.echo._suits"
        )
        assert echo_module._suits[name] == codepoint


class TestUnicodeTableContents:
    """The _unicode dict must contain the block glyphs (suits live in _suits)."""

    @pytest.mark.parametrize(
        "name, codepoint",
        [
            ("solidblock", "\u2588"),
            ("lightblock", "\u2591"),
            ("mediumblock", "\u2592"),
        ],
    )
    def test_unicode_entry_present(self, name, codepoint):
        assert name in echo_module._unicode, (
            f"{name!r} is missing from bbsengine6.io.echo._unicode"
        )
        assert echo_module._unicode[name] == codepoint


class TestCardSuitRendering:
    """{u:NAME} for the four suits must render the matching glyph."""

    @pytest.mark.parametrize(
        "cmd, glyph",
        [
            ("{u:spade}", "\u2660"),
            ("{u:heart}", "\u2665"),
            ("{u:diamond}", "\u2666"),
            ("{u:club}", "\u2663"),
        ],
    )
    def test_suit_renders_correct_glyph(self, captured_stdout, cmd, glyph):
        echo_module.echo(cmd, end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == glyph, (
            f"expected {cmd} to render as {glyph!r}, got {out!r}"
        )


class TestBlockRendering:
    """{u:NAME} for the block glyphs must render the matching character."""

    @pytest.mark.parametrize(
        "cmd, glyph",
        [
            ("{u:solidblock}", "\u2588"),
            ("{u:lightblock}", "\u2591"),
            ("{u:mediumblock}", "\u2592"),
        ],
    )
    def test_block_renders_correct_glyph(self, captured_stdout, cmd, glyph):
        echo_module.echo(cmd, end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == glyph, (
            f"expected {cmd} to render as {glyph!r}, got {out!r}"
        )


class TestUnicodeRepeat:
    """{u:NAME:N} must repeat the glyph N times."""

    def test_solidblock_repeat_two(self, captured_stdout):
        echo_module.echo("{u:solidblock:2}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2588" * 2, (
            f"expected '██' from {{u:solidblock:2}}, got {out!r}"
        )

    def test_solidblock_repeat_three(self, captured_stdout):
        echo_module.echo("{u:solidblock:3}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2588" * 3, (
            f"expected '███' from {{u:solidblock:3}}, got {out!r}"
        )

    def test_repeat_does_not_affect_surrounding_text(self, captured_stdout):
        echo_module.echo("A{u:solidblock:2}K", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "A" + "\u2588" * 2 + "K", (
            f"expected 'A██K', got {out!r}"
        )

    def test_invalid_repeat_falls_back_to_single(self, captured_stdout):
        """A non-integer repeat arg must not crash and must default to repeat=1."""
        echo_module.echo("{u:solidblock:abc}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2588", (
            f"expected a single '█' from {{u:solidblock:abc}}, got {out!r}"
        )


class TestDirectUnicodeRegression:
    """Existing {dblhline}, {arrow}, etc. must actually render now that
    _handle_unicode looks at token.value (not token.kind)."""

    @pytest.mark.parametrize(
        "cmd, glyph",
        [
            ("{dblhline}", "\u2550"),
            ("{dblvline}", "\u2551"),
            ("{dblul}", "\u2554"),
            ("{dblur}", "\u2557"),
            ("{dblll}", "\u255a"),
            ("{dbllr}", "\u255d"),
            ("{arrow}", "\u2192"),
            ("{arrow_left}", "\u2190"),
            ("{arrow_up}", "\u2191"),
            ("{arrow_down}", "\u2193"),
        ],
    )
    def test_direct_unicode_renders(self, captured_stdout, cmd, glyph):
        echo_module.echo(cmd, end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == glyph, (
            f"expected {cmd} to render as {glyph!r}, got {out!r}"
        )


class TestDiamondCollision:
    """The card-suit and ACS namespaces must not collide.

    `{diamond}` is the ACS glyph ◆ (U+25C6).
    `{u:diamond}` is the card suit ♦ (U+2666).
    """

    def test_bare_diamond_is_acs(self, captured_stdout):
        """{diamond} must resolve to the ACS diamond ◆, not the card suit."""
        echo_module.echo("{diamond}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        # The ACS glyph is rendered by emitting ESC(0 + "`" + ESC(B which
        # a terminal would render as ◆. In a non-ACS context, the literal
        # "`" (U+0060) is written, but the dispatcher should still take
        # the ACS branch — not the unicode {u:diamond} branch.
        assert "\u2666" not in out, (
            f"{{diamond}} must not render as the card-suit ♦, got {out!r}"
        )

    def test_namespaced_diamond_is_card_suit(self, captured_stdout):
        """{u:diamond} must resolve to the card-suit ♦, not the ACS glyph."""
        echo_module.echo("{u:diamond}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2666", (
            f"expected {{u:diamond}} to render as ♦ (U+2666), got {out!r}"
        )


class TestUnknownUnicode:
    """Unknown {u:NAME} must not crash."""

    def test_unknown_unicode_name_does_not_raise(self, captured_stdout):
        """A bogus name in the {u:...} namespace must fall through cleanly."""
        # echo() should not raise; it should just not produce the glyph.
        echo_module.echo("{u:notarealthing}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        # We don't pin the exact fallback text — we only pin "no crash,
        # no suit glyph was synthesized". The token falls through
        # handler_dispatch and is yielded as a raw WORD.
        assert "\u2660" not in out
        assert "\u2665" not in out
        assert "\u2666" not in out
        assert "\u2663" not in out


class TestUserReproFromBugReport:
    """Pin the exact invocations from the original bug report."""

    def test_double_brace_literal_u_spade(self, captured_stdout):
        # The user's literal-text invocations:
        #   echo(f"{{u:spade}}")  -> the f-string becomes "{u:spade}"
        # In the bug, this was rendered literally. After the fix the
        # *content* is what gets interpreted by echo (the {{ was the
        # test's way of writing a literal `{`); we test the interpreted
        # form so we exercise the actual code path.
        echo_module.echo("{u:spade}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2660"

    def test_double_brace_literal_spade(self, captured_stdout):
        # echo(f"{{spade}}") -> "{spade}". "spade" is registered in the
        # _suits table, so the bare form resolves to ♠ (same answer as
        # {u:spade}).
        echo_module.echo("{spade}", end="", width=80, flush=False)
        out = _strip_ansi("".join(captured_stdout["chunks"]))
        assert out == "\u2660", (
            f"expected {{spade}} to render as ♠, got {out!r}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
