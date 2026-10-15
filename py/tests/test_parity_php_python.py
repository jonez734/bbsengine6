"""
Cross-language byte-exact parity test for bbsengine6.util.datestamp().

Reads the shared JSON fixture at
``bbsengine6/test_parity_php_python.json`` and asserts that
``bbsengine6.util.datestamp(epoch, format)`` produces the
expected output for every (epoch, format) case.

The PHP counterpart
(``bbsengine6/php/test_parity_php_python.php``) reads the same
fixture and asserts the same expected output from PHP's
``\\bbsengine6\\util\\datestamp()``. If the two surfaces ever
drift, one of the two test runners will fail.

The fixture pins the test epoch to a specific UTC timestamp
(1760365800 = 2025-10-13 14:30:00 UTC) and uses only
TZ-independent format tokens (no ``%Z``). The test constructs
the datetime via ``datetime.fromtimestamp(epoch, tz=timezone.utc)``
so the offset-aware ``%:z`` and ``%z`` tokens render the same
``+0000``/``+00:00`` regardless of the server's local TZ.

@since 2026-10-15

Usage:
    cd bbsengine6/py
    python3 -m pytest tests/test_parity_php_python.py -v
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make the bbsengine6 package importable when the test is run
# from any cwd. Adds ``bbsengine6/py/src`` to sys.path once.
_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_PKG_SRC) not in sys.path:
    sys.path.insert(0, str(_PKG_SRC))

from bbsengine6 import util  # noqa: E402

# Fixture path: ../../../test_parity_php_python.json relative to
# this test file (bbsengine6/py/tests/test_parity_php_python.py
# -> bbsengine6/test_parity_php_python.json).
_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "test_parity_php_python.json"


def _load_fixture():
    """Load the parity fixture. Skips the test if not found."""
    if not _FIXTURE_PATH.is_file():
        pytest.skip(f"parity fixture not found at {_FIXTURE_PATH}")
    with _FIXTURE_PATH.open() as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        pytest.skip("parity fixture is empty or malformed")
    return data


@pytest.fixture(scope="module")
def fixture():
    return _load_fixture()


def _epoch_to_datetime(epoch: int) -> datetime:
    """Build a UTC datetime for the given Unix epoch.

    Using tz=timezone.utc (not tzlocal()) so %z / %:z render
    ``+0000`` / ``+00:00`` regardless of the server's local TZ.
    This matches the PHP test, which sets
    ``date_default_timezone_set('UTC')`` to pin the same
    behavior.
    """
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _make_id(case: dict) -> str:
    """Stable pytest test ID from a (name, format) pair."""
    return f"{case['name']} | {case['format']}"


def test_fixture_loads(fixture):
    """Smoke test: fixture is a list with at least one group."""
    assert isinstance(fixture, list)
    assert len(fixture) >= 1
    assert "cases" in fixture[0]
    assert len(fixture[0]["cases"]) >= 1


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(c, id=_make_id(c))
        for group in _load_fixture()
        for c in group["cases"]
    ],
)
def test_php_python_parity_case(fixture, case):
    """For each (epoch, format) case, assert Python's datestamp
    matches the expected output recorded in the shared fixture.

    The PHP test reads the same fixture, so a failure on either
    side indicates a drift between the two surfaces.
    """
    group = fixture[0]
    dt = _epoch_to_datetime(group["epoch"])
    actual = util.datestamp(dt, case["format"])
    assert actual == case["expected"], (
        f"Python datestamp drifted: format={case['format']!r} "
        f"expected={case['expected']!r} got={actual!r}"
    )
