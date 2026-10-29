"""getch_str and getch_utf8 return the same keys for the same input; the runtime default works.

Each test writes bytes to a real pty in raw mode (as an inputstring prompt has it) and reads
them through a reader. Raw mode matters: in cooked mode a key without Enter is held by the
line discipline and the reader returns None.
"""

import importlib
import os
import pty
import time
import tty

import pytest

common = importlib.import_module("bbsengine6.io.common")
g = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture
def raw_pty():
    master, slave = pty.openpty()
    tty.setraw(slave)
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved = common._current_input_stream
    common.set_input_stream(stream)
    yield master
    common.set_input_stream(saved)
    stream.close()
    os.close(master)


def _read_all(master, reader, data, *, impl=None, count=None):
    """Write ``data``, then read keys until the reader returns None (or ``count`` keys)."""
    os.write(master, data)
    time.sleep(0.1)
    keys = []
    limit = count if count is not None else len(data) + 2
    for _ in range(limit):
        key = reader(timeout=0.3) if impl is None else reader(timeout=0.3, impl=impl)
        if key is None:
            break
        keys.append(key)
    return keys


def _keys_from_fresh_pty(reader, data, impl=None):
    """Run ``reader`` on its own raw pty with ``data`` written first. Each reader gets its own
    stream, so both see identical input."""
    master, slave = pty.openpty()
    tty.setraw(slave)
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved = common._current_input_stream
    common.set_input_stream(stream)
    try:
        return _read_all(master, reader, data, impl=impl)
    finally:
        common.set_input_stream(saved)
        stream.close()
        os.close(master)


@pytest.mark.unit
@pytest.mark.parametrize(
    "data, expected",
    [
        (b"ab", ["a", "b"]),
        (b"hi\x7f", ["h", "i", "KEY_BACKSPACE"]),
        (b"x\x17", ["x", "KEY_CTRL_W"]),
    ],
    ids=["plain", "backspace", "ctrl-w"],
)
def test_str_and_utf8_readers_return_identical_keys(data, expected):
    keys_str = _keys_from_fresh_pty(g.getch_str, data)
    keys_utf8 = _keys_from_fresh_pty(g.getch_utf8, data)
    assert keys_str == expected, keys_str
    assert keys_utf8 == keys_str


@pytest.mark.unit
def test_impl_keyword_routes_to_the_chosen_reader(raw_pty):
    keys = _read_all(raw_pty, g.getch_str, b"q", impl="utf8")
    assert keys == ["q"]


@pytest.mark.unit
def test_runtime_default_follows_set_getch_impl_and_restores():
    original = g.get_getch_impl()
    try:
        g.set_getch_impl("utf8")
        assert g.get_getch_impl() == "utf8"
        g.set_getch_impl("str")
        assert g.get_getch_impl() == "str"
    finally:
        g.set_getch_impl(original)
    assert g.get_getch_impl() == original


@pytest.mark.unit
def test_unknown_impl_is_refused():
    with pytest.raises(ValueError):
        g.set_getch_impl("bogus")
