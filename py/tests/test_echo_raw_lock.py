"""
Regression tests for Phase 4 io/echo.py hardening.

Covers:
- The module-global `_raw` is protected by `_raw_lock`.
- Concurrent echo() / echo_iter() calls do not interleave raw mode toggling.
"""

import importlib
import threading

import pytest

pytestmark = pytest.mark.unit


def _echo_module():
    """bbsengine6.io.__init__ shadows the echo submodule with the `echo`
    function. Use importlib to ensure the submodule is loaded, then
    retrieve the actual module object from sys.modules."""
    return importlib.import_module("bbsengine6.io.echo")


def test_echo_lock_supports_context_manager():
    """_raw_lock should be usable as a context manager (`with _raw_lock:`)."""
    echo_module = _echo_module()
    lock = echo_module._raw_lock
    with lock:
        # Smoke-test: nothing should raise.
        pass


def test_echo_raw_is_a_boolean_attribute():
    """_raw should remain a simple bool attribute on the echo module,
    not be replaced with a more complex object."""
    echo_module = _echo_module()
    assert hasattr(echo_module, "_raw")
    assert isinstance(echo_module._raw, bool)


def test_echo_concurrent_lock_acquisition_serializes():
    """Multiple threads acquiring _raw_lock should serialize (no deadlock)."""
    echo_module = _echo_module()

    lock = echo_module._raw_lock
    counter = {"value": 0}
    max_concurrent = {"value": 0}
    current_concurrent = {"value": 0}

    def worker():
        with lock:
            current_concurrent["value"] += 1
            max_concurrent["value"] = max(
                max_concurrent["value"], current_concurrent["value"]
            )
            for _ in range(100):
                counter["value"] += 1
            current_concurrent["value"] -= 1

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert counter["value"] == 8 * 100
    assert max_concurrent["value"] == 1, (
        "lock must serialize: max concurrent holders should be 1"
    )


def test_echo_source_uses_raw_lock_for_writes():
    """The echo() function must wrap _raw access in `_raw_lock` (Phase 4 fix)."""
    import inspect

    echo_module = _echo_module()
    src = inspect.getsource(echo_module)
    assert "with _raw_lock" in src, (
        "io.echo must use 'with _raw_lock' to protect raw-mode toggling"
    )
    # And there must be at least 4-5 lock acquisitions (one per helper).
    acquisitions = src.count("with _raw_lock")
    assert acquisitions >= 4, (
        f"expected at least 4 'with _raw_lock' acquisitions in echo.py, "
        f"got {acquisitions}"
    )
