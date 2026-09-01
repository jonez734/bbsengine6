#
# test_sanitize_args_sh.py - cross-implementation parity tests.
#
# The shell helper (bbsengine6/data/sanitize_args.sh) and the Python
# helper (bbsengine6.util.sanitize_args) implement the same policy.
# These tests run the shell helper against a representative matrix
# of argv inputs and assert each shell verdict matches the Python
# verdict for the same input. They exist to keep the two
# implementations from drifting; if one accepts an arg the other
# rejects, the test fails.
#
# Shell semantics differ from Python semantics in two important ways
# that we explicitly account for:
#
#   1. The kernel strips NUL bytes at exec(3); a shell wrapper can
#      never receive a NUL byte in "$@". The Python helper still
#      checks for NUL (because Python programs can construct argv
#      programmatically with NULs). The shell test matrix therefore
#      omits NUL cases; they are not reachable from the shell side.
#
#   2. The shell tokenizer splits on IFS (default: space, tab, NL)
#      BEFORE the helper sees "$@". So an argv like "--foo;bar" is
#      delivered to the helper as a single token only when quoted by
#      the caller. The shell test matrix uses sh -c '... ...' with
#      quoted tokens to simulate the kernel argv boundary.
#

import os
import shutil
import subprocess
from pathlib import Path

import pytest

sys_path = "src"
import sys

if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from bbsengine6.util import sanitize_args

HELPER = Path(__file__).resolve().parents[1] / "src" / "bbsengine6" / "data" / "sanitize_args.sh"


pytestmark = pytest.mark.unit


# (token_as_python, token_as_shell) pairs. The shell form must be a
# single argv token at the helper boundary; if it contains shell
# metacharacters the test must quote it.
#
# Tokens that the shell tokenizer would split on even when quoted
# (e.g., a literal newline) are out of scope: they cannot reach the
# helper as a single argv element from the kernel argv boundary.
PARITY_CASES = [
    # Empty
    ("", "''"),
    # Bare dash (argparse stdin sentinel)
    ("-", "-"),
    # Single-dash python options
    ("-X", "-X"),
    ("-c", "-c"),
    ("-E", "-E"),
    ("-I", "-I"),
    ("-O", "-O"),
    ("-OO", "-OO"),
    ("-W", "-W"),
    ("-Xfaulthandler", "-Xfaulthandler"),
    # Long opts (valid)
    ("--foo", "--foo"),
    ("--foo-bar", "--foo-bar"),
    ("--foo_bar", "--foo_bar"),
    ("--Foo123", "--Foo123"),
    ("--foo=value", "--foo=value"),
    ("--foo=bar baz", "--foo=bar baz"),
    ("--foo=--nested", "--foo=--nested"),
    ("--foo=", "--foo="),
    ("--", "--"),
    # Long opts (rejected; need shell quoting)
    ("--foo;bar", "'--foo;bar'"),
    ("--foo|bar", "'--foo|bar'"),
    ("--foo$bar", "'--foo$bar'"),
    ("--foo&bar", "'--foo&bar'"),
    ("--foo>bar", "'--foo>bar'"),
    ("--foo<bar", "'--foo<bar'"),
    # Positionals
    ("hello", "hello"),
    ("hello world", "'hello world'"),
    ("abc123", "abc123"),
    ("/path/to/file", "/path/to/file"),
    ("user@host", "user@host"),
]


def _shell_token_repr(token: str) -> str:
    """Render a Python token as a shell-quoted token. Single-quote
    the whole thing; escape embedded single quotes via the standard
    ``'\\''`` sequence.
    """
    return "'" + token.replace("'", "'\\''") + "'"


def _run_shell_sanitize_arg(token: str) -> str:
    """Invoke the shell helper's _sanitize_arg function and return
    its stdout (either ``ok`` or ``reject:<reason>``).
    """
    if not HELPER.is_file():
        pytest.skip(f"shell helper not found at {HELPER}")
    cmd = [
        "sh",
        "-c",
        f'. "{HELPER}" && _sanitize_arg {_shell_token_repr(token)}',
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10, check=False
    )
    return result.stdout.strip()


def _run_shell_sanitize_and_exec_dry(token: str) -> int:
    """Invoke ``sanitize_and_exec`` against a static ``python -m
    nonexistent_module`` prefix with one caller argv token. Returns
    the helper's exit code: 0 if accepted (would exec python), 2 if
    rejected.

    N.B.: when the token is accepted, the helper actually exec(3)s
    python and ``python -m nonexistent_module`` exits with whatever
    ModuleNotFoundError yields. We can't observe that exit code via
    this wrapper. The cleanest way to detect "accepted" is to check
    that the subprocess did NOT print the
    "sanitize_and_exec: refusing to exec" rejection message.
    """
    if not HELPER.is_file():
        pytest.skip(f"shell helper not found at {HELPER}")
    cmd = [
        "sh",
        "-c",
        (
            f'. "{HELPER}" && '
            f'sanitize_and_exec python -m nonexistent_module {_shell_token_repr(token)}'
        ),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10, check=False
    )
    stderr = result.stderr or ""
    if "sanitize_and_exec: refusing to exec" in stderr:
        return 2
    # Accepted; python was exec'd (and failed with ModuleNotFoundError).
    # We don't care about that exit code.
    return 0


def _python_verdict(token: str) -> str:
    """Run sanitize_args on a single-token argv and return the verdict
    in the shell helper's string format (``ok`` or ``reject:<reason>``).
    """
    _cleaned, rejections = sanitize_args([token])
    if not rejections:
        return "ok"
    return "reject:" + rejections[0][2]


@pytest.mark.parametrize("py_token,sh_token", PARITY_CASES)
def test_shell_and_python_sanitize_arg_agree(py_token, sh_token):
    """Per-token parity: the shell helper's _sanitize_arg and the
    Python sanitize_args must reach the same verdict for the same
    token.
    """
    py_verdict = _python_verdict(py_token)
    sh_verdict = _run_shell_sanitize_arg(py_token)
    # Reason strings differ slightly (shell includes the token in
    # single-dash-option, python doesn't); compare on the leading
    # ``reject:<category>`` only.
    py_prefix = py_verdict.split(":", 1)[0]
    sh_prefix = sh_verdict.split(":", 1)[0]
    assert py_prefix == sh_prefix, (
        f"verdict mismatch for {py_token!r}: "
        f"python={py_verdict!r} shell={sh_verdict!r}"
    )


def test_shell_helper_exists_and_is_readable():
    assert HELPER.is_file(), f"shell helper missing at {HELPER}"
    assert os.access(HELPER, os.R_OK), f"shell helper not readable: {HELPER}"


def test_shell_helper_syntax_is_valid():
    if not shutil.which("sh"):
        pytest.skip("no /bin/sh on PATH")
    result = subprocess.run(
        ["sh", "-n", str(HELPER)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"shell helper has syntax errors: {result.stderr}"
    )


def test_sanitize_and_exec_rejects_x_flag():
    """End-to-end: sanitize_and_exec refuses `-X`."""
    rc = _run_shell_sanitize_and_exec_dry("-X")
    assert rc == 2


def test_sanitize_and_exec_rejects_bare_dash():
    rc = _run_shell_sanitize_and_exec_dry("-")
    assert rc == 2


def test_sanitize_and_exec_accepts_clean_argv():
    """End-to-end: sanitize_and_exec accepts `--foo=bar` (would exec
    python, which fails on the bogus module — that's fine, the point
    is the helper did NOT refuse).
    """
    rc = _run_shell_sanitize_and_exec_dry("--foo=bar")
    assert rc == 0


def test_helper_scrubs_dangerous_env_at_source_time(monkeypatch):
    """Sourcing the helper unsets every name in
    ``DANGEROUS_PYTHON_VARS``.

    The scrub runs at source time, so this test sources the helper
    in a subshell where the dangerous vars are pre-set, then dumps
    the resulting env via ``env -0 | grep PYTHON`` (or similar) to
    verify none of the dangerous names remain.

    We don't go through ``sanitize_and_exec`` for this test because
    the scrub is at source time and exec is a no-op for env
    inspection purposes.
    """
    if not HELPER.is_file():
        pytest.skip(f"shell helper not found at {HELPER}")
    monkeypatch.setenv("PYTHONSTARTUP", "/tmp/evil_startup")
    monkeypatch.setenv("PYTHONPATH", "/tmp/evil_path")
    monkeypatch.setenv("PYTHONDEBUG", "1")

    cmd = [
        "sh",
        "-c",
        (
            f'. "{HELPER}" && '
            # Print each PYTHON* env var in name=value form, one per
            # line. After scrubbing, only the safe ones (e.g.
            # PYTHONUNBUFFERED, PYTHONIOENCODING) should appear.
            'env | grep "^PYTHON" | sort'
        ),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0, (
        f"subshell failed: stderr={result.stderr}"
    )
    out = result.stdout
    # Every dangerous var name should NOT appear.
    for name in (
        "PYTHONSTARTUP",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONINSPECT",
        "PYTHONBREAKPOINT",
        "PYTHONDEBUG",
        "PYTHONPYCACHEPREFIX",
        "PYTHONNOUSERSITE",
        "PYTHONUSERBASE",
        "PYTHONFAULTHANDLER",
        "PYTHONTRACEMALLOC",
        "PYTHONDEVMODE",
        "PYTHONDONTWRITEBYTECODE",
    ):
        assert not any(line.startswith(f"{name}=") for line in out.splitlines()), (
            f"{name} was not scrubbed by the helper: {out!r}"
        )


def test_helper_preserves_safe_python_env_vars(monkeypatch):
    """PYTHONUNBUFFERED and PYTHONIOENCODING are NOT in the
    dangerous list; they should survive the scrub."""
    if not HELPER.is_file():
        pytest.skip(f"shell helper not found at {HELPER}")
    monkeypatch.setenv("PYTHONUNBUFFERED", "1")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("PYTHONSTARTUP", "/tmp/evil_startup")

    cmd = [
        "sh",
        "-c",
        f'. "{HELPER}" && env | grep "^PYTHON" | sort',
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=10, check=False
    )
    assert result.returncode == 0, (
        f"subshell failed: stderr={result.stderr}"
    )
    out_lines = result.stdout.splitlines()
    # PYTHONUNBUFFERED and PYTHONIOENCODING should be preserved.
    assert any(line.startswith("PYTHONUNBUFFERED=") for line in out_lines), (
        f"PYTHONUNBUFFERED was scrubbed: {result.stdout!r}"
    )
    assert any(line.startswith("PYTHONIOENCODING=") for line in out_lines), (
        f"PYTHONIOENCODING was scrubbed: {result.stdout!r}"
    )
    # PYTHONSTARTUP must be gone.
    assert not any(
        line.startswith("PYTHONSTARTUP=") for line in out_lines
    ), (
        f"PYTHONSTARTUP was not scrubbed: {result.stdout!r}"
    )