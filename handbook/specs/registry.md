# bbsengine6.registry — the generic, instance-based registry

## Status

Implemented: `bbsengine6/py/src/bbsengine6/registry.py`. Used by `bbsengine6.menu_next` (menus),
`bbsengine6.commands` (`CommandRegistry` storage), and casino and letteredolive (menus and command
lists built on it). Tests: `bbsengine6/py/tests/test_registry.py`.

## Purpose

A small container of items, grouped by an optional scope, with no knowledge of what the items mean.
Visibility, tiers, letters, and naming rules belong to the caller. Each menu, shell, or host creates
its own `Registry`, so there is no process-wide state to share or reset.

## Interface

| Method | Behaviour |
|---|---|
| `add(key, item, scope=None)` | Store `item` under `key` in `scope`. Adding an existing key in the same scope replaces the item and keeps its position. |
| `remove(key, scope=None)` | Drop the item. Raises `KeyError` if it is not present. Removing a scope's last item drops the scope. |
| `get(key, scope=None, default=None)` | The item, or `default`. |
| `__contains__(key)` | True if `key` is present in **any** scope. See "Membership" below. |
| `items(scope=None, *, all_scopes=False)` | One scope's items in insertion order. With `all_scopes=True`, every item, scopes in sorted order with unscoped first. |
| `keys(scope=None)` | One scope's keys in insertion order. |
| `scopes()` | Scope names holding items: unscoped (`None`) first, then sorted. |
| `clear()` | Drop everything. |
| `len(registry)` | Number of items across all scopes. |

`items()` and `keys()` return fresh lists, so a caller may sort or filter them without changing the
registry.

## Ordering

- Within a scope, insertion order. Replacing a key does not move it.
- Across scopes, `items(all_scopes=True)` sorts scope names, so a menu draws the same way every run.

## Membership

`key in registry` answers "is this key in any scope?", not "is it in a particular scope". That is the
documented behaviour and is pinned by `test_contains_checks_all_scopes`.

It differs from `get`, which needs a scope. Use `get(key, scope)` or `keys(scope)` when the scope
matters. The cross-scope check is convenient for the common case of one scope per registry, and that
is how the menus use it.

## Thread safety, and why the lock is an `RLock`

Every public method holds one lock for its whole body. The lock guards the scope dictionary, so a
reader never sees a half-applied `add` or `remove`, and two threads adding at once do not lose items
(`test_concurrent_adds_do_not_lose_items`).

The lock is a **reentrant** lock (`threading.RLock`), and this is required, not incidental:

- `items(all_scopes=True)` holds the lock and then calls `self.scopes()`, which takes the lock again
  on the same thread. With a plain `threading.Lock` that second acquire would block forever.

Do not replace the `RLock` with a `Lock` without also removing that re-entry. Do not remove the lock
as unused: the registry is shared by menu and command code that can run on more than one thread.

## What the registry does not do

- It does not validate items. Callers decide what an item is.
- It does not sort items. Ordering comes from insertion order and scope names only.
- It does not persist. A registry lives as long as its owner.

## Consumers

- `bbsengine6.menu_next` — menus of `MenuOption` items, one registry per menu. See
  [`menu_next.md`](menu_next.md).
- `bbsengine6.commands.CommandRegistry` — the typed-name store, under one scope (`"commands"`).
- casino `casino/menus.py` — `MAIN_MENU`, and the scope `casino.lib`.
- letteredolive `shell/lib.py` — the command store, scope `"commands"`.

## Tests

- `test_registry.py` — add, get, remove, scopes, ordering, fresh lists, instance isolation, and
  concurrent adds.
- `test_menu_next_registry.py` — menus held in a `Registry`.
- `test_commands.py` — `CommandRegistry` over `Registry`, including storage after an override.
