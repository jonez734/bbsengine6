"""
Regression tests for Phase 2 util.get_safe_path() hardening.

Covers:
- Joining components stays inside the first (base) component.
- `..` traversal attempts raise ValueError.
- Absolute path attempts are normalised but still contained.
- Empty components list raises ValueError.
- Legitimate subpath is returned.
- Tilde and env-var expansion are applied to components.
"""

import os

import pytest

from bbsengine6.util import get_safe_path


pytestmark = pytest.mark.unit


def test_safe_path_raises_on_empty_components():
    with pytest.raises(ValueError, match="At least one"):
        get_safe_path(None)  # type: ignore[arg-type]


def test_safe_path_returns_subpath_under_base(tmp_path):
    base = str(tmp_path)
    sub = str(tmp_path / "a" / "b.txt")
    result = get_safe_path(None, base, sub)
    # relpath between resolved result and base must stay inside base.
    assert os.path.relpath(result, os.path.realpath(base)).startswith(".") is False
    assert os.path.commonpath([result, os.path.realpath(base)]) == os.path.realpath(base)


def test_safe_path_rejects_parent_traversal(tmp_path):
    base = str(tmp_path)
    # Try to escape by going .. past the base.
    with pytest.raises(ValueError, match="directory traversal"):
        get_safe_path(None, base, str(tmp_path / ".."))


def test_safe_path_rejects_relative_traversal(tmp_path):
    base = str(tmp_path)
    with pytest.raises(ValueError, match="directory traversal"):
        get_safe_path(None, base, str(tmp_path / "a" / ".." / ".."))


def test_safe_path_accepts_simple_subdir(tmp_path):
    sub = tmp_path / "inner"
    sub.mkdir()
    base = str(tmp_path)
    result = get_safe_path(None, base, str(sub))
    assert os.path.commonpath([result, base]) == base


def test_safe_path_expands_tilde(tmp_path, monkeypatch):
    """~ should be expanded to the home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    base = str(tmp_path)
    # "~/inner" expands to "<tmp>/inner" (relative to HOME).
    result = get_safe_path(None, base, "~/inner")
    # After expansion and abs/rel check, result should be inside base.
    assert os.path.commonpath([result, base]) == base


def test_safe_path_expands_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("BBSENGINE_TESTDIR", str(tmp_path))
    base = str(tmp_path)
    result = get_safe_path(None, base, "$BBSENGINE_TESTDIR/inner")
    assert os.path.commonpath([result, base]) == base


def test_safe_path_sibling_prefix_not_bypassable(tmp_path):
    """A sibling directory whose prefix matches the base must not be
    treated as inside the base.

    E.g. base='/var/lib/bbs' and target='/var/lib/bbsengine6/foo' must
    NOT be considered inside '/var/lib/bbs'.
    """
    base = str(tmp_path / "base")
    os.makedirs(base, exist_ok=True)
    sibling = tmp_path / "base_sibling"
    os.makedirs(sibling, exist_ok=True)
    with pytest.raises(ValueError, match="directory traversal"):
        get_safe_path(None, base, str(sibling / "foo.txt"))


def test_safe_path_no_components_raises():
    with pytest.raises(ValueError):
        get_safe_path(None)
