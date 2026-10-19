"""
Regression tests for Phase 4 io/inputdate.py hardening.

Covers:
- inputdate() and _verify_date_expression() work when `getdate_next` is
  unavailable, falling back to dateutil.parser.
- Malformed date expressions return False / None (not raise).
- Empty buffer + noneok=False is rejected.
"""

import sys
import importlib

import pytest


pytestmark = pytest.mark.unit


def test_inputdate_module_imports_without_getdate_next(monkeypatch):
    """inputdate.py must import successfully even when the getdate_next
    package is missing. The try/except ImportError guard sets getdate=None
    so the rest of the module can use the dateutil fallback.
    """
    # Force the getdate_next submodule to be unavailable in sys.modules.
    monkeypatch.setitem(sys.modules, "getdate_next", None)

    # Reload inputdate with getdate_next unimportable.
    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    import bbsengine6.inputdate as inputdate_module

    # The module must have set getdate to None.
    assert inputdate_module.getdate is None


def test_inputdate_getdate_present_when_package_available(monkeypatch):
    """When getdate_next.getdate IS importable, inputdate.getdate must NOT
    be None. On this environment getdate_next is a *namespace package*
    without a real ``getdate`` function, so we skip the assertion."""
    # Remove any prior monkeypatch override on sys.modules.
    monkeypatch.delitem(sys.modules, "getdate_next", raising=False)

    # Try the exact import the inputdate module performs; skip if it fails.
    try:
        from getdate_next import getdate as _probe_getdate  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        pytest.skip("getdate_next.getdate is not importable in this environment")

    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    import bbsengine6.inputdate as inputdate_module

    assert inputdate_module.getdate is not None
    assert callable(inputdate_module.getdate)


def test_verify_date_expression_rejects_empty_without_noneok(monkeypatch):
    """Empty buffer must be rejected unless noneok=True."""
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    from bbsengine6 import inputdate

    assert inputdate._verify_date_expression(None, "") is False
    assert inputdate._verify_date_expression(None, "", noneok=True) is True
    assert inputdate._verify_date_expression(None, "   ") is False


def test_verify_date_expression_accepts_iso_date(monkeypatch):
    """An ISO-formatted date string must parse successfully via dateutil."""
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    from bbsengine6 import inputdate

    assert inputdate._verify_date_expression(None, "2026-08-02") is True


def test_verify_date_expression_accepts_human_readable(monkeypatch):
    """dateutil should accept common human-readable forms."""
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    from bbsengine6 import inputdate

    assert inputdate._verify_date_expression(None, "August 2, 2026") is True


def test_verify_date_expression_rejects_garbage(monkeypatch):
    """Truly unparseable strings must return False, not raise."""
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    if "bbsengine6.inputdate" in sys.modules:
        importlib.reload(sys.modules["bbsengine6.inputdate"])
    from bbsengine6 import inputdate

    # Anything dateutil can interpret is "valid" in the original code; the
    # important assertion is no exception is raised on blatantly bad input.
    # dateutil raises ParserError or ValueError on truly bad input.
    for bad in ["not-a-date-at-all-xyz", "", "  "]:
        result = inputdate._verify_date_expression(None, bad)
        assert result is False


def _reload_inputdate():
    if "bbsengine6.inputdate" in sys.modules:
        return importlib.reload(sys.modules["bbsengine6.inputdate"])
    import bbsengine6.inputdate as inputdate_module

    return inputdate_module


def test_namespace_package_is_treated_as_not_installed(monkeypatch, tmp_path):
    """A bare namespace package has no `getdate`; it must not be used.

    Simulate a source checkout on sys.path: a directory named getdate_next
    with no __init__.py. Importing it yields a namespace package whose
    `getdate` attribute does not exist, so the fallback must engage.
    """
    pkg = tmp_path / "getdate_next"
    pkg.mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "getdate_next", raising=False)

    inputdate_module = _reload_inputdate()

    assert inputdate_module.getdate is None
    assert inputdate_module.BACKEND == "dateutil"


def test_backend_reports_dateutil_when_getdate_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    inputdate_module = _reload_inputdate()

    assert inputdate_module.BACKEND == "dateutil"


def test_fallback_warning_is_logged_once(monkeypatch, caplog):
    """Using the dateutil fallback logs one warning per process, not per call."""
    monkeypatch.setitem(sys.modules, "getdate_next", None)
    inputdate_module = _reload_inputdate()

    with caplog.at_level("WARNING", logger="bbsengine6.inputdate"):
        inputdate_module._verify_date_expression(None, "2026-08-02")
        inputdate_module._verify_date_expression(None, "2026-08-03")
        inputdate_module._verify_date_expression(None, "August 4, 2026")

    warnings = [r for r in caplog.records if r.name == "bbsengine6.inputdate"]
    assert len(warnings) == 1
    assert "getdate_next is not installed" in warnings[0].getMessage()


def test_no_warning_when_getdate_installed(monkeypatch, caplog):
    """When getdate_next is importable, the fallback warning is not logged."""
    try:
        from getdate_next import getdate as _probe  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        pytest.skip("getdate_next.getdate is not importable in this environment")

    monkeypatch.delitem(sys.modules, "getdate_next", raising=False)
    inputdate_module = _reload_inputdate()

    with caplog.at_level("WARNING", logger="bbsengine6.inputdate"):
        inputdate_module._verify_date_expression(None, "2026-08-02")

    assert inputdate_module.BACKEND == "getdate_next"
    assert not [r for r in caplog.records if r.name == "bbsengine6.inputdate"]
