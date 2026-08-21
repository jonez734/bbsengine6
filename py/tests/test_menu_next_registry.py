"""bbsengine6/tests/test_menu_next_registry.py

Tests for the bbsengine6.menu_next registry primitives:

  - ``register_menu_options(name, *options)`` -- append under a
    registrar name.
  - ``registered_options(name=None)`` -- flat list sorted by
    registrar name; or per-registrar in insertion order.
  - ``clear_registry()`` -- test helper that drops every entry.

Pins the determinism contract (alphabetical-by-registrar ordering)
and the per-registrar isolation contract (registrar A's options do
not leak into registrar B's lookup).
"""

from __future__ import annotations

import pytest

from bbsengine6.menu_next import (
    MenuOption,
    register_menu_options,
    registered_options,
)
from bbsengine6.menu_next.registry import clear_registry


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_registry():
    """Wipe the registry before and after each test so order/state
    from a prior test cannot leak in."""
    clear_registry()
    yield
    clear_registry()


def test_register_single_registrar():
    """A single registrar with multiple options keeps insertion order."""
    register_menu_options(
        "test.alpha",
        MenuOption("a", "Alpha-1"),
        MenuOption("b", "Alpha-2"),
    )
    out = registered_options(name="test.alpha")
    assert [o.label for o in out] == ["Alpha-1", "Alpha-2"]


def test_register_multiple_registrars_sorted_alphabetically():
    """``registered_options()`` with no filter returns registrars in
    alphabetical order so the menu draw is deterministic across
    processes."""
    register_menu_options("test.zzz", MenuOption("z", "Z"))
    register_menu_options("test.aaa", MenuOption("a", "A"))
    register_menu_options("test.mmm", MenuOption("m", "M"))

    out = registered_options()
    labels = [o.label for o in out]
    assert labels == ["A", "M", "Z"]


def test_register_per_registrar_filter():
    """``registered_options(name="...")`` returns ONLY that registrar's
    options, in the order they were registered."""
    register_menu_options("test.x", MenuOption("1", "X-1"))
    register_menu_options("test.y", MenuOption("2", "Y-1"))
    register_menu_options("test.x", MenuOption("3", "X-2"))

    x = registered_options(name="test.x")
    y = registered_options(name="test.y")
    assert [o.label for o in x] == ["X-1", "X-2"]
    assert [o.label for o in y] == ["Y-1"]


def test_register_unknown_registrar_returns_empty():
    """Asking for a registrar that has not registered returns an empty
    list (not an error)."""
    assert registered_options(name="test.never.registered") == []


def test_register_no_options_is_noop():
    """Calling ``register_menu_options`` with zero options does not
    create an empty bucket."""
    register_menu_options("test.empty")
    assert registered_options(name="test.empty") == []
    assert "test.empty" not in [o.label for o in registered_options()]


def test_registered_options_returns_fresh_list():
    """Mutating the returned list does not affect the registry."""
    register_menu_options("test.x", MenuOption("a", "X"))
    out = registered_options(name="test.x")
    out.append(MenuOption("z", "Z"))
    assert registered_options(name="test.x") == [MenuOption("a", "X")]


def test_clear_registry_drops_everything():
    """``clear_registry()`` removes all entries."""
    register_menu_options("test.a", MenuOption("a", "A"))
    register_menu_options("test.b", MenuOption("b", "B"))
    assert len(registered_options()) == 2
    clear_registry()
    assert registered_options() == []


def test_register_menu_options_thread_safe_smoke():
    """Concurrent ``register_menu_options`` calls do not lose entries
    (smoke test; the lock is an RLock so this should always succeed)."""
    import threading

    n_threads = 8
    n_per = 50

    def worker(prefix):
        for i in range(n_per):
            register_menu_options(
                f"test.thread.{prefix}",
                MenuOption(f"{prefix}{i}", f"{prefix}-{i}"),
            )

    threads = [threading.Thread(target=worker, args=(str(t),)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    out = registered_options()
    assert len(out) == n_threads * n_per
