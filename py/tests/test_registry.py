"""bbsengine6/tests/test_registry.py

Tests for the generic ``bbsengine6.registry.Registry``:

  - add / get / remove / contains / len / clear
  - scopes: per-scope items, unscoped items, scope listing order
  - ordering: insertion order within a scope; sorted scope order for all items
  - fresh lists: callers cannot change the registry through a returned list
  - replacement: re-adding a key keeps its position
  - instance isolation: two registries share no state
  - thread safety: concurrent adds do not lose items
"""

from __future__ import annotations

import threading

import pytest

from bbsengine6.registry import Registry


pytestmark = pytest.mark.unit


def test_add_and_get_by_key():
    r = Registry()
    r.add("a", "alpha")
    assert r.get("a") == "alpha"


def test_get_missing_returns_default():
    r = Registry()
    assert r.get("nope") is None
    assert r.get("nope", default="fallback") == "fallback"


def test_add_replaces_existing_key_in_place():
    r = Registry()
    r.add("a", 1)
    r.add("b", 2)
    r.add("a", 3)
    assert r.get("a") == 3
    assert r.keys() == ["a", "b"]


def test_remove_drops_item():
    r = Registry()
    r.add("a", 1)
    r.remove("a")
    assert r.get("a") is None
    assert "a" not in r


def test_remove_missing_raises_key_error():
    r = Registry()
    with pytest.raises(KeyError):
        r.remove("missing")


def test_remove_respects_scope():
    r = Registry()
    r.add("a", 1, scope="x")
    with pytest.raises(KeyError):
        r.remove("a")  # unscoped: not present
    r.remove("a", scope="x")
    assert r.get("a", scope="x") is None


def test_same_key_in_two_scopes_is_two_items():
    r = Registry()
    r.add("a", 1, scope="x")
    r.add("a", 2, scope="y")
    assert r.get("a", scope="x") == 1
    assert r.get("a", scope="y") == 2
    assert len(r) == 2


def test_contains_checks_all_scopes():
    r = Registry()
    r.add("k", 1, scope="s")
    assert "k" in r
    assert "other" not in r


def test_len_counts_all_items():
    r = Registry()
    r.add("a", 1)
    r.add("b", 2, scope="s")
    assert len(r) == 2


def test_clear_drops_everything():
    r = Registry()
    r.add("a", 1)
    r.add("b", 2, scope="s")
    r.clear()
    assert len(r) == 0
    assert r.scopes() == []


def test_items_for_one_scope_keep_insertion_order():
    r = Registry()
    r.add("3", "c", scope="x")
    r.add("1", "a", scope="x")
    r.add("2", "b", scope="x")
    assert r.items("x") == ["c", "a", "b"]


def test_items_for_missing_scope_is_empty():
    r = Registry()
    assert r.items("never") == []


def test_items_all_scopes_sorted_by_scope_name():
    r = Registry()
    r.add("z", "Z", scope="zzz")
    r.add("a", "A", scope="aaa")
    r.add("m", "M", scope="mmm")
    assert r.items(all_scopes=True) == ["A", "M", "Z"]


def test_items_all_scopes_puts_unscoped_first():
    r = Registry()
    r.add("s", "scoped", scope="aaa")
    r.add("u", "unscoped")
    assert r.items(all_scopes=True) == ["unscoped", "scoped"]


def test_scopes_lists_names_unscoped_first_then_sorted():
    r = Registry()
    r.add("1", 1, scope="beta")
    r.add("2", 2)
    r.add("3", 3, scope="alpha")
    assert r.scopes() == [None, "alpha", "beta"]


def test_removing_last_item_drops_scope():
    r = Registry()
    r.add("a", 1, scope="only")
    r.remove("a", scope="only")
    assert r.scopes() == []


def test_items_returns_fresh_list():
    r = Registry()
    r.add("a", 1, scope="x")
    out = r.items("x")
    out.append(99)
    assert r.items("x") == [1]


def test_keys_in_scope_insertion_order():
    r = Registry()
    r.add("b", 1, scope="x")
    r.add("a", 2, scope="x")
    assert r.keys("x") == ["b", "a"]


def test_two_registries_share_no_state():
    first = Registry()
    second = Registry()
    first.add("a", 1, scope="s")
    assert second.get("a", scope="s") is None
    assert len(second) == 0
    second.clear()
    assert first.get("a", scope="s") == 1


def test_concurrent_adds_do_not_lose_items():
    r = Registry()

    def worker(n: int) -> None:
        for i in range(200):
            r.add((n, i), (n, i), scope=f"w{n}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(r) == 8 * 200


def test_all_scopes_read_does_not_deadlock_on_its_own_lock():
    """items(all_scopes=True) takes the lock and then calls scopes(), which takes it again on the
    same thread. The lock is reentrant, so this returns; a plain Lock would block forever.
    """
    r = Registry()
    r.add("a", 1, scope="x")
    r.add("b", 2, scope="y")
    result = {}

    def read() -> None:
        result["items"] = r.items(all_scopes=True)

    t = threading.Thread(target=read, daemon=True)
    t.start()
    t.join(timeout=2)
    assert not t.is_alive(), "items(all_scopes=True) deadlocked on the registry lock"
    assert result["items"] == [1, 2]
