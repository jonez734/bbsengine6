"""Enter inside inputstring() must move the cursor to column 0 (CRLF, not a bare LF).

tty.setraw() clears OPOST, so the tty stops translating "\\n" to "\\r\\n". The Enter key
writes "{f6}", which is a bare "\\n", so without the fix the cursor moved down but not back.
These tests run inputstring() on a real pty and check the bytes written after Enter.
"""

import os
import sys
import time

import pytest

pexpect = pytest.importorskip("pexpect")

CODE = (
    "import sys; sys.path.insert(0, 'src')\n"
    "from bbsengine6.io.inputstring import inputstring\n"
    "v = inputstring('name: ')\n"
    "sys.stdout.write('\\nRESULT=%r\\n' % v); sys.stdout.flush()\n"
)


def _pump(child, until, buf, timeout=5.0):
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
        # A real terminal answers ESC[6n; answer it so the prompt does not time out.
        for _ in range(chunk.count(b"\x1b[6n")):
            child.send(b"\x1b[1;1R")
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
    assert _pump(child, b"name: ", buf), bytes(buf)[-300:]
    yield child, buf
    child.close(force=True)


def test_enter_writes_crlf_not_bare_lf(prompt):
    child, buf = prompt
    time.sleep(0.2)
    child.send(b"abc")
    time.sleep(0.2)
    mark = len(buf)
    child.send(b"\r")
    assert _pump(child, b"RESULT=", buf)
    after = bytes(buf[mark:])
    # Every LF written after Enter must be preceded by CR.
    bare = [i for i, b in enumerate(after) if b == 0x0A and (i == 0 or after[i - 1] != 0x0D)]
    assert bare == [], f"bare LF after Enter at {bare}: {after!r}"


def test_result_returned_intact(prompt):
    child, buf = prompt
    time.sleep(0.2)
    child.send(b"abc")
    time.sleep(0.2)
    child.send(b"\r")
    assert _pump(child, b"RESULT=", buf)
    assert b"RESULT='abc'" in buf
