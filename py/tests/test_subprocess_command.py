"""Tests for bbsengine6.subprocess_command: TERM check, child exit, and screen redraw."""

import pytest

from bbsengine6 import subprocess_command as sc
from bbsengine6.interaction import current_session, new_session, use_session


@pytest.fixture
def calls(monkeypatch):
    """Record the order of raw-session changes, the child run, and the redraw."""
    log = []
    monkeypatch.setattr(sc, "redraw_all", lambda bottom_buf="": log.append(("redraw", bottom_buf)))
    import bbsengine6.io.common as common

    monkeypatch.setattr(common, "end_raw_session", lambda: log.append(("end_raw",)))
    return log


class TestTermCheck:
    def test_dumb_and_empty_are_unusable(self):
        assert sc.term_ok("dumb") is False
        assert sc.term_ok("") is False

    def test_xterm_is_usable(self):
        assert sc.term_ok("xterm-256color") is True

    def test_check_refuses_when_on(self):
        with pytest.raises(sc.SubprocessCommandError):
            sc.check_term("dumb")

    def test_check_passes_when_off_per_session(self):
        s = new_session(name="harness")
        s.subprocess_term_check = False
        with use_session(s):
            sc.check_term("dumb")  # no raise

    def test_setting_is_per_session(self):
        s = new_session(name="other")
        s.subprocess_term_check = False
        with use_session(s):
            assert current_session().subprocess_term_check is False
        assert current_session().subprocess_term_check is True

    def test_refused_launch_does_not_run_or_redraw(self, calls, monkeypatch):
        ran = []
        monkeypatch.setattr(sc.subprocess, "run", lambda *a, **k: ran.append(a))
        with pytest.raises(sc.SubprocessCommandError):
            sc.run_child(["snake"], term="dumb")
        assert ran == []
        assert calls == []


class TestRunChild:
    def test_returns_exit_status_and_redraws(self, calls):
        status = sc.run_child(["sh", "-c", "exit 3"], term="xterm")
        assert status == 3
        assert calls[-1][0] == "redraw"

    def test_raw_session_ended_before_child(self, calls):
        sc.run_child(["true"], term="xterm")
        assert calls[0] == ("end_raw",)
        assert calls[-1][0] == "redraw"

    def test_redraw_runs_when_child_fails(self, calls):
        with pytest.raises(OSError):
            sc.run_child(["/nonexistent/program-xyz"], term="xterm")
        assert calls[-1][0] == "redraw"

    def test_bottom_buf_is_passed_to_redraw(self, calls):
        sc.run_child(["true"], term="xterm", bottom_buf="status")
        assert calls[-1] == ("redraw", "status")


class TestRedrawAll:
    """redraw_all() writes the screen restore in order and marks the prompt line dirty."""

    def test_order_reset_then_region_then_bar_then_dirty(self, monkeypatch):
        import bbsengine6.io.common as common
        from bbsengine6 import bottombar, screen

        log = []
        monkeypatch.setattr(bottombar, "init", lambda *a, **k: log.append("region"))
        monkeypatch.setattr(screen, "updatebottombar", lambda buf: log.append(("bar", buf)))
        monkeypatch.setattr(common, "_set_input_dirty", lambda v: log.append(("dirty", v)))

        import sys

        # bbsengine6.io.echo is shadowed by the echo() function in the package, so
        # take the module from sys.modules.
        echo_mod = sys.modules["bbsengine6.io.echo"]
        monkeypatch.setattr(echo_mod, "echo", lambda text, **k: log.append(("echo", text)))
        sc.redraw_all("left")

        names = [x if isinstance(x, str) else x[0] for x in log]
        assert names == ["echo", "echo", "region", "bar", "dirty"]
        assert log[1] == ("echo", "\x1b[H\x1b[2J")
        assert log[3] == ("bar", "left")
        assert log[4] == ("dirty", True)


# ---------------------------------------------------------------------------
# Registry integration: a subprocess command is a registry entry whose spec names a
# wrapper module, launched through module.run(); it is overridable and availability-gated.
# ---------------------------------------------------------------------------

import argparse  # noqa: E402

from bbsengine6 import commands as cmds  # noqa: E402


def test_wrapper_main_runs_child_through_module_run(monkeypatch):
    """module.run() on a wrapper calls run_child with its argv and returns the status."""
    import bbsengine6.module as module
    import bbsengine6.backend.checkfunctions as cf

    seen = {}

    def fake_run_child(argv, **kwargs):
        seen["argv"] = list(argv)
        return 7

    monkeypatch.setattr(sc, "run_child", fake_run_child)

    # Use the real main() shape a wrapper would have: it delegates to run_child.
    def wrapper_main(args, **kwargs):
        return sc.run_child(["snake"], term="xterm") == 0

    monkeypatch.setattr(cf, "main", wrapper_main)
    monkeypatch.setattr(cf, "access", lambda args, op, **k: True)
    monkeypatch.setattr(cf, "init", lambda args, **k: True)
    monkeypatch.setattr(cf, "buildargs", lambda args, **k: None)

    res = module.run(argparse.Namespace(debug=False), "checkfunctions", package="bbsengine6.backend")
    assert seen["argv"] == ["snake"]
    assert res is False  # status 7 is not success


def test_subprocess_entry_is_overridable_by_session_name():
    """A session may replace a subprocess entry (default tier) by name, like exit."""
    r = cmds.CommandRegistry(mode=cmds.MODE_EXTEND)
    r.use_default([cmds.Entry("snake", cmds.TIER_DEFAULT, spec={"module": "games.snake"})])
    r.register("snake", cmds.TIER_SESSION, spec={"module": "casino.snake"})
    kind, entry = r.resolve("snake", {})
    assert kind == cmds.RESOLVE_EXACT
    assert entry.spec == {"module": "casino.snake"}


def test_unavailable_subprocess_entry_takes_no_part():
    """A subprocess entry hidden by its predicate does not match, so a prefix elsewhere runs."""
    r = cmds.CommandRegistry(mode=cmds.MODE_EXTEND)
    r.use_default([
        cmds.Entry("snake", cmds.TIER_DEFAULT, spec={"module": "games.snake"}),
        cmds.Entry("stats", cmds.TIER_DEFAULT),
    ])
    r.lookup("snake").available = lambda state: False
    kind, entry = r.resolve("s", {})
    assert (kind, entry.name) == (cmds.RESOLVE_UNIQUE, "stats")


class TestInterrupt:
    """Ctrl-C on a real pty ends the child, redraws, and returns INTERRUPTED_STATUS."""

    def test_ctrl_c_returns_status_and_redraws(self):
        import os
        import sys

        pexpect = pytest.importorskip("pexpect")
        if not sys.stdin.isatty() and not hasattr(os, "openpty"):
            pytest.skip("needs a pty")

        code = (
            "import sys; sys.path.insert(0, 'src')\n"
            "from bbsengine6 import subprocess_command as sc\n"
            "sc.redraw_all = lambda bottom_buf='': print('REDRAW', flush=True)\n"
            "st = sc.run_child(['sh', '-c', \"echo READY; trap 'exit 130' INT; "
            "while :; do sleep 0.1; done\"], term='xterm')\n"
            "print('RETURNED', st, flush=True)\n"
        )
        child = pexpect.spawn(
            sys.executable, ["-c", code], encoding="utf-8", timeout=10,
            env={**os.environ, "TERM": "xterm"},
        )
        child.expect("READY", timeout=5)
        child.sendintr()
        child.expect(pexpect.EOF)
        out = child.before
        assert "RAISED" not in out
        assert "REDRAW" in out
        assert f"RETURNED {sc.INTERRUPTED_STATUS}" in out


class TestRestoreTypedText:
    """Caller-reprompt: after a child, the caller passes the typed text back to inputstring.

    oldvalue is positional-only in inputstring(); passing it by keyword raised TypeError,
    so the caller passes it positionally. This pins the flow on a real pty.
    """

    def test_typed_text_is_redrawn_and_editable_after_child(self):
        import os
        import sys
        import time

        pexpect = pytest.importorskip("pexpect")
        code = (
            "import sys; sys.path.insert(0, 'src')\n"
            "from bbsengine6.io.inputstring import inputstring\n"
            "from bbsengine6 import subprocess_command as sc\n"
            "typed = inputstring('name: ')\n"
            "sc.run_child(['sh', '-c', 'sleep 0.2; exit 3'], term='xterm')\n"
            "sys.stderr.write('AFTER_CHILD\\n'); sys.stderr.flush()\n"
            "after = inputstring('name: ', typed)\n"
            "sys.stdout.write('RESULT=%r\\n' % after); sys.stdout.flush()\n"
        )
        child = pexpect.spawn(
            sys.executable, ["-c", code], encoding="utf-8", timeout=15,
            env={**os.environ, "TERM": "xterm"}, dimensions=(24, 80),
        )
        out = []
        # A real terminal answers the cursor query (ESC[6n); the harness must too, or the
        # prompt times out. Answer each query as the output arrives.
        def answer(until, t=10):
            end = time.time() + t
            while time.time() < end:
                try:
                    chunk = child.read_nonblocking(4096, timeout=0.2)
                except pexpect.TIMEOUT:
                    continue
                except pexpect.EOF:
                    return None
                out.append(chunk)
                for _ in range(chunk.count("\x1b[6n")):
                    child.send("\x1b[1;1R")
                if until in "".join(out):
                    return True
            return False

        assert answer("name: ")
        time.sleep(0.3)
        child.send("abc")
        time.sleep(0.3)
        child.send("\r")
        # Wait for the child to finish, then for the second prompt to draw. A key sent in the
        # gap between the child exiting and the prompt reading is dropped (measured: no
        # settle time loses X), so pause briefly after the prompt draws before typing.
        assert answer("AFTER_CHILD", 8), "".join(out)[-300:]
        end = time.time() + 8
        while "".join(out).count("name: ") < 2 and time.time() < end:
            answer("name: ", 0.2)
        assert "".join(out).count("name: ") >= 2, "".join(out)[-300:]
        time.sleep(0.5)
        child.send("X")
        time.sleep(0.3)
        child.send("\r")
        assert answer("RESULT=", 8), "".join(out)[-300:]
        assert "RESULT='abcX'" in "".join(out)
