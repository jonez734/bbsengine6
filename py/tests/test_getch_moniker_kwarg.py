"""getch_str accepts a moniker keyword without colliding with the session moniker.

A caller may pass moniker= in getch_str's kwargs (test_getch_notify does). The notification check
must not pass that moniker twice, which raised TypeError and left the key unread for the next test.
"""

import importlib
import os
import pty
from unittest.mock import patch

import pytest

common = importlib.import_module("bbsengine6.io.common")
g = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture
def pty_stream():
    master, slave = pty.openpty()
    stream = os.fdopen(slave, "r", buffering=1, encoding="utf-8")
    saved = common._current_input_stream
    common.set_input_stream(stream)
    yield master
    common.set_input_stream(saved)
    stream.close()
    os.close(master)


@pytest.mark.unit
def test_getch_str_with_a_moniker_kwarg_does_not_raise(pty_stream):
    with patch.object(g, "_threadlocal") as tl, \
         patch.object(g, "_check_notifications", return_value=(False, 0)), \
         patch.object(g, "_push_subscribed", return_value=True):
        tl.moniker = "bob"
        assert g.getch_str(timeout=0.2, moniker=None) is None


@pytest.mark.unit
def test_session_moniker_is_used_for_the_check_not_the_kwarg(pty_stream):
    with patch.object(g, "_threadlocal") as tl, \
         patch.object(g, "_check_notifications", return_value=(False, 0)) as chk, \
         patch.object(g, "_push_subscribed", return_value=True):
        tl.moniker = "bob"
        g.getch_str(timeout=0.2, moniker=None)
    assert chk.call_args.args[0] == "bob"
