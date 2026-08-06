"""
Tests for module.load() and module.run() with the ``package=`` kwarg.

These cover the cross-package-call plumbing that lets e.g.
bbsengine6.startup.main resolve a bare short name like
``"checkfunctions"`` against ``"bbsengine6.backend"``.
"""

import argparse
import sys
from pathlib import Path

import pytest


# Make sure the in-tree package is importable.
_REPO_PY_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_REPO_PY_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_PY_SRC))


def _import_module_pkg():
    from bbsengine6 import module
    return module


def test_load_bare_name_with_package_resolves():
    module = _import_module_pkg()
    m = module.load(None, "checkfunctions", package="bbsengine6.backend")
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_load_dotted_name_ignores_package():
    module = _import_module_pkg()
    m = module.load(
        None, "bbsengine6.backend.checkfunctions", package="bbsengine6.startup"
    )
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_load_bad_package_raises_module_not_found():
    module = _import_module_pkg()
    with pytest.raises(ModuleNotFoundError):
        module.load(None, "checkfunctions", package="bbsengine6.startup")


def test_get_forwards_package_to_load():
    module = _import_module_pkg()
    m = module.get("checkfunctions", None, package="bbsengine6.backend")
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_load_relative_dotted_name_with_package():
    """A leading-dot modulepath like '.backend.checkfunctions' should
    resolve relative to the supplied package, just like
    'from bbsengine6 import backend.checkfunctions' / a relative import.
    """
    module = _import_module_pkg()
    m = module.load(
        None, ".backend.checkfunctions", package="bbsengine6"
    )
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_load_relative_dotted_name_without_package_raises():
    """importlib rejects a leading-dot name when no package anchor is given
    (TypeError, not ImportError); module.load() should surface that error.
    """
    module = _import_module_pkg()
    with pytest.raises((ImportError, ModuleNotFoundError, TypeError)):
        module.load(None, ".backend.checkfunctions")


def test_load_bare_name_with_relative_package_resolves():
    """A bare modulepath with a leading-dot relative ``package=`` must
    resolve to the absolute package using the calling frame's
    ``__package__`` as the anchor. Regression: previously, passing
    ``package='.backend'`` (a relative form) from a caller in
    ``bbsengine6.backend`` would feed a relative name into
    ``importlib.import_module()`` and raise
    ``ModuleNotFoundError: No module named '.backend'``.
    """
    module = _import_module_pkg()
    m = module.load(None, "checkfunctions", package=".backend")
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_load_relative_dotted_name_with_relative_package_resolves():
    """A leading-dot dotted modulepath with a relative ``package=``
    should also resolve: the relative package is first converted to its
    absolute form, then ``importlib`` uses it as the anchor for the
    dotted modulepath.
    """
    module = _import_module_pkg()
    m = module.load(
        None, ".checkfunctions", package=".backend"
    )
    assert m.__name__ == "bbsengine6.backend.checkfunctions"


def test_run_with_package_resolves_and_does_not_leak_kwarg(monkeypatch):
    """module.run(args, 'checkfunctions', package='bbsengine6.backend', ...)
    must resolve the bare name AND must NOT forward ``package`` to the
    inner main()/init()/access()/buildargs() callbacks.
    """
    module = _import_module_pkg()

    captured = {}

    def fake_init(args, **kwargs):
        captured["init"] = dict(kwargs)
        return True

    def fake_access(args, op, **kwargs):
        captured["access"] = dict(kwargs)
        return True

    def fake_buildargs(args, **kwargs):
        captured["buildargs"] = dict(kwargs)
        return None

    def fake_main(args, **kwargs):
        captured["main"] = dict(kwargs)
        return True

    # Patch the callbacks on the real bbsengine6.backend.checkfunctions module
    import bbsengine6.backend.checkfunctions as cf
    monkeypatch.setattr(cf, "init", fake_init)
    monkeypatch.setattr(cf, "access", fake_access)
    monkeypatch.setattr(cf, "buildargs", fake_buildargs)
    monkeypatch.setattr(cf, "main", fake_main)

    args = argparse.Namespace(debug=False)
    res = module.run(
        args,
        "checkfunctions",
        package="bbsengine6.backend",
        marker="hello",
    )
    assert res is True
    for cb_name in ("init", "access", "buildargs", "main"):
        assert cb_name in captured, f"{cb_name} was never called"
        assert captured[cb_name].get("package") is None, (
            f"package leaked into {cb_name}()"
        )
        assert captured[cb_name].get("marker") == "hello", (
            f"marker dropped from {cb_name}()"
        )
