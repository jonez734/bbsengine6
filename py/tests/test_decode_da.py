"""decode_da: split a probe_da() reply into its kind, class, and features."""

import pytest

from bbsengine6.io import terminal


@pytest.mark.parametrize(
    "reply, cls, features",
    [
        ("\x1b[?6c", 6, []),  # VT102
        ("\x1b[?1;2c", 1, [2]),  # VT100 with AVO
        ("\x1b[?62;1;2;6;8;9;15;22c", 62, [1, 2, 6, 8, 9, 15, 22]),  # VT220
        ("\x1b[?64;1;2;6;9;15;18;21;22c", 64, [1, 2, 6, 9, 15, 18, 21, 22]),  # modern xterm
    ],
)
def test_da1_class_and_features(reply, cls, features):
    d = terminal.decode_da(reply)
    assert d["kind"] == "DA1"
    assert d["class"] == cls
    assert d["features"] == features
    assert d["params"] == [cls] + features


def test_da1_empty_parameters():
    d = terminal.decode_da("\x1b[?c")
    assert d == {"kind": "DA1", "params": [], "class": None, "features": []}


def test_da2_terminal_type_and_firmware():
    d = terminal.decode_da("\x1b[>41;0;0c")
    assert d["kind"] == "DA2"
    assert d["terminal_type"] == 41
    assert d["firmware"] == 0
    assert d["params"] == [41, 0, 0]


def test_da2_minimal_reply_has_no_firmware():
    d = terminal.decode_da("\x1b[>0c")
    assert d["terminal_type"] == 0
    assert d["firmware"] is None


@pytest.mark.parametrize(
    "reply",
    [None, "", "hello", "\x1b[6c", "\x1b[?6cX", "\x1b[?62;x;2c", "\x1b[5n", "\x1b[?6"],
)
def test_not_a_da_reply_returns_none(reply):
    assert terminal.decode_da(reply) is None


def test_decode_agrees_with_has_ansi_approval():
    """Any reply decode_da accepts is one has_ansi approves, and the reverse."""
    samples = ["\x1b[?6c", "\x1b[>0c", "\x1b[?62;x;2c", "\x1b[6c", "", "\x1b[?c"]
    for s in samples:
        approved = bool(terminal.DA1_REPLY_RE.fullmatch(s) or terminal.DA2_REPLY_RE.fullmatch(s))
        assert (terminal.decode_da(s) is not None) == approved, s
