"""Enter inside inputstring() must move the cursor to column 0 (CRLF, not a bare LF).

tty.setraw() clears OPOST, so the tty stops translating "\\n" to "\\r\\n". The Enter key
writes "{f6}", which is a bare "\\n", so without the fix the cursor moved down but not back.
These tests run inputstring() on a real pty and check the bytes written after Enter.
"""

import os
import sys
import time

import pytest

# These tests run the program in a pty (os.forkpty). The stdlib warns that forking a
# multi-threaded process can deadlock in the child. The child execs the interpreter at once,
# so that risk does not apply here. The warning is ignored for this module only.
pytestmark = pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded, use of forkpty\\(\\) may lead to deadlocks:DeprecationWarning"
)

pexpect = pytest.importorskip("pexpect")

from _pty_screen import DSRResponder  # noqa: E402

CODE = (
    "import sys; sys.path.insert(0, 'src')\n"
    "from bbsengine6.io.inputstring import inputstring\n"
    "v = inputstring('name: ')\n"
    "sys.stdout.write('\\nRESULT=%r\\n' % v); sys.stdout.flush()\n"
)


def _pump(child, until, buf, responder, timeout=5.0):
    """Read output into buf, answering cursor-position queries, until `until` appears."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            chunk = child.read_nonblocking(4096, timeout=0.2)
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            break
        buf.extend(chunk)
        # A real terminal answers ESC[6n with its cursor; answer from the screen the program drew.
        for reply in responder.feed(chunk):
            child.send(reply)
        if until in buf:
            return True
    return until in buf


@pytest.fixture
def prompt():
    child = pexpect.spawn(
        sys.executable, ["-c", CODE], timeout=10,
        env={**os.environ, "TERM": "xterm"}, dimensions=(24, 80),
    )
    buf = bytearray()
    responder = DSRResponder(24, 80)
    assert _pump(child, b"name: ", buf, responder), bytes(buf)[-300:]
    yield child, buf, responder
    child.close(force=True)


def test_enter_writes_crlf_not_bare_lf(prompt):
    child, buf, responder = prompt
    time.sleep(0.2)
    child.send(b"abc")
    time.sleep(0.2)
    mark = len(buf)
    child.send(b"\r")
    assert _pump(child, b"RESULT=", buf, responder)
    after = bytes(buf[mark:])
    # Every LF written after Enter must be preceded by CR.
    bare = [i for i, b in enumerate(after) if b == 0x0A and (i == 0 or after[i - 1] != 0x0D)]
    assert bare == [], f"bare LF after Enter at {bare}: {after!r}"


def test_result_returned_intact(prompt):
    child, buf, responder = prompt
    time.sleep(0.2)
    child.send(b"abc")
    time.sleep(0.2)
    child.send(b"\r")
    assert _pump(child, b"RESULT=", buf, responder)
    assert b"RESULT='abc'" in buf
