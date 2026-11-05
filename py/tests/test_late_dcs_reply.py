"""Late XTGETTCAP (DCS) replies are not keys: the queue drops them and getch returns the
keypress that follows. Pty test and a queue unit test."""

import sys
import textwrap

import pytest

pexpect = pytest.importorskip("pexpect")
needs_pty = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")


def test_queue_discard_removes_xtgettcap_reply_and_keeps_keys():
    from bbsengine6.io import common

    q = common._queue()
    q.clear()
    q.extend("\x1bP1+r524742=38\x1b\\q")
    assert common.discard_da_replies() == 1
    assert "".join(q) == "q"
    common._interaction().da_replies.clear()
    q.clear()


@needs_pty
def test_pty_late_xtgettcap_reply_then_key_returns_only_the_key():
    """A late DCS reply is not echoed as keys: getch returns the real keypress alone."""
    import time as _t

    src = textwrap.dedent(
        """
        import sys, time, importlib
        sys.path.insert(0, "src")
        getch = importlib.import_module("bbsengine6.io.getch")
        time.sleep(0.8)
        keys = []
        for _ in range(12):
            k = getch.getch_str(timeout=0.4)
            if k is None:
                break
            keys.append(k)
        sys.stdout.write("KEYS=" + repr(keys) + "\\\\n")
        sys.stdout.flush()
        """
    )
    child = pexpect.spawn(sys.executable, ["-c", src], timeout=30, encoding="utf-8")
    try:
        _t.sleep(0.2)
        child.send("\x1bP1+r524742=38\x1b\\q")
        child.expect(r"KEYS=(\[[^\r\n]*\])")
        keys = child.match.group(1)
    finally:
        child.close(force=True)
    assert keys == "['q']", keys
