"""bbsengine6/tests/test_menu_next_registry.py

Tests for a menu held in a ``bbsengine6.registry.Registry`` instance, using
``MenuOption`` items scoped by registrar name:

  - ``add(key, option, scope=registrar)`` -- register an option.
  - ``items(scope)`` -- one registrar's options, in insertion order.
  - ``items(all_scopes=True)`` -- every option, registrars sorted by name.

Pins the determinism contract (alphabetical-by-registrar ordering), the
per-registrar isolation contract, and instance isolation: two menus share
no state, so there is no process-wide registry to reset between tests.
"""

from __future__ import annotations

import threading

import pytest

from bbsengine6.menu_next import MenuOption, Registry


pytestmark = pytest.mark.unit


def test_single_registrar_keeps_insertion_order():
    """A single registrar with multiple options keeps insertion order."""
    menu = Registry()
    menu.add("a", MenuOption("a", "Alpha-1"), scope="test.alpha")
    menu.add("b", MenuOption("b", "Alpha-2"), scope="test.alpha")
    out = menu.items("test.alpha")
    assert [o.label for o in out] == ["Alpha-1", "Alpha-2"]


def test_all_scopes_sorted_alphabetically_by_registrar():
    """``items(all_scopes=True)`` returns registrars in alphabetical order so
    the menu draw is deterministic across processes."""
    menu = Registry()
    menu.add("z", MenuOption("z", "Z"), scope="test.zzz")
    menu.add("a", MenuOption("a", "A"), scope="test.aaa")
    menu.add("m", MenuOption("m", "M"), scope="test.mmm")
    labels = [o.label for o in menu.items(all_scopes=True)]
    assert labels == ["A", "M", "Z"]


def test_per_registrar_filter():
    """``items(scope)`` returns ONLY that registrar's options, in the order
    they were registered."""
    menu = Registry()
    menu.add("1", MenuOption("1", "X-1"), scope="test.x")
    menu.add("2", MenuOption("2", "Y-1"), scope="test.y")
    menu.add("3", MenuOption("3", "X-2"), scope="test.x")
    assert [o.label for o in menu.items("test.x")] == ["X-1", "X-2"]
    assert [o.label for o in menu.items("test.y")] == ["Y-1"]


def test_unknown_registrar_returns_empty():
    """Asking for a registrar that has not registered returns an empty list."""
    menu = Registry()
    assert menu.items("test.never.registered") == []


def test_items_returns_fresh_list():
    """Mutating the returned list does not affect the menu."""
    menu = Registry()
    menu.add("a", MenuOption("a", "X"), scope="test.x")
    out = menu.items("test.x")
    out.append(MenuOption("z", "Z"))
    assert menu.items("test.x") == [MenuOption("a", "X")]


def test_two_menus_share_no_state():
    """Two menus are independent: options in one are not visible in the other."""
    first = Registry()
    second = Registry()
    first.add("a", MenuOption("a", "A"), scope="test.a")
    assert second.items(all_scopes=True) == []
    assert first.items(all_scopes=True) == [MenuOption("a", "A")]


def test_same_letter_in_two_registrars_is_two_options():
    """Registrars are separate namespaces: the same letter may appear in two
    registrars (for example two game launchers both using ``p``)."""
    menu = Registry()
    menu.add("p", MenuOption("p", "Poker"), scope="casino.poker")
    menu.add("p", MenuOption("p", "Play"), scope="casino.play")
    assert [o.label for o in menu.items(all_scopes=True)] == ["Play", "Poker"]


def test_concurrent_registration_does_not_lose_options():
    """Concurrent ``add`` calls from many threads do not lose options."""
    menu = Registry()
    n_threads = 8
    n_per = 50

    def worker(prefix: str) -> None:
        for i in range(n_per):
            menu.add(f"{prefix}{i}", MenuOption(f"{prefix}{i}", f"{prefix}-{i}"),
                     scope=f"test.thread.{prefix}")

    threads = [threading.Thread(target=worker, args=(str(t),)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(menu.items(all_scopes=True)) == n_threads * n_per
