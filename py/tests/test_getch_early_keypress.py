"""A keypress typed just before a read is returned, not lost.

tty.setraw() defaults to TCSAFLUSH, which discarded keys still in the kernel buffer. The
raw-mode switch now keeps unread input (common._enter_raw uses TCSANOW).
"""

import shutil
import sys
import textwrap

import pytest

pexpect = pytest.importorskip("pexpect")

needs_pty = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")


@needs_pty
def test_key_typed_before_getch_is_returned():
    src = textwrap.dedent(
        """
        import sys, time, importlib
        sys.path.insert(0, "src")
        getch = importlib.import_module("bbsengine6.io.getch")
        time.sleep(1.0)
        k = getch.getch_str(timeout=3.0)
        sys.stdout.write("\\\\nKEY=" + repr(k) + "\\\\nDONE\\\\n")
        sys.stdout.flush()
        """
    )
    child = pexpect.spawn(sys.executable, ["-c", src], timeout=20, encoding="utf-8")
    try:
        import time as _t

        _t.sleep(0.2)
        child.send("q")
        child.expect("DONE")
        out = child.before
    finally:
        child.close(force=True)
    assert "KEY='q'" in out, out
