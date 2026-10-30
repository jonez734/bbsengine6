# bbsengine6.menu_next — menu options and the registry they live in

## Status

Implemented. `menu_next` is the menu-option layer. Each menu is a `Registry` instance. There is no
process-wide menu registry.

- `bbsengine6/py/src/bbsengine6/menu_next/` — `MenuOption`, `visible_options`.
- `bbsengine6/py/src/bbsengine6/registry.py` — the generic `Registry` the menus are built on.
- casino's `casino/src/casino/menus.py` — `MAIN_MENU`, the first consumer.
- letteredolive's `shell/menu.py` — `choose`, the function a hosted menu is read through.

Open work is tracked in [`todo/menu_next.md`](../todo/menu_next.md).

## Design

### `Registry`

`bbsengine6.registry.Registry` is a thread-safe container of items, grouped by an optional scope.
It holds no visibility, tier, or letter rules; the caller supplies those.

- `add(key, item, scope=None)` — store an item. Adding an existing key in the same scope replaces it
  in place.
- `remove(key, scope=None)` — drop an item. Raises `KeyError` if absent.
- `get(key, scope=None, default=None)`.
- `items(scope=None)` — one scope's items, in insertion order. `items(all_scopes=True)` returns
  every item, scopes in sorted order (unscoped first), so a menu draws deterministically.
- `keys(scope=None)`, `scopes()`, `clear()`, `len()`, and `in`.

`items()` and `keys()` return fresh lists, so a caller may sort or filter without changing the
registry. Each registry is independent; two menus share no state.

### `MenuOption`

A dataclass describing one menu entry: its letter, label, the module it runs, and the visibility
gates (`requires_seated`, `requires_connected`, `allowed_game_types`, `hide_if_seated_type`).

### `visible_options`

`visible_options(options, state)` filters `MenuOption`s against a duck-typed player state. It is
pure: no database and no `psycopg` import.

### Choosing from a menu

A menu is read through a function with the signature `choose(prompt, registry, default="", help=None)`.
The valid answers are the registry's keys. The key is returned as stored, with no case change. An
empty line returns `default`, and a `default` that is not a key raises `ValueError`. `help` is
shown on F1.

Two implementations exist:

- **Standalone (casino CLI):** `io.inputchoice`, which reads one key and returns it uppercased.
  Callers that depend on case normalise the result.
- **Hosted (letteredolive):** `shell.menu.choose`, built on `io.inputstring` with a membership
  check. Hosted callers receive the key as stored.

casino's `casino/host.py` routes to one or the other: `register_menu` installs the hosted function,
and `choose` falls back to `io.inputchoice` when no host is registered.

## Removed API

The first version of `menu_next` held a global registry in the module. It is gone. Callers should
not use these names:

| Removed | Replacement |
|---|---|
| `register_menu_options(registrar, *options)` | `registry.add(letter, option, scope=registrar)` |
| `registered_options(name=None)` | `registry.items(scope)` or `registry.items(all_scopes=True)` |
| `clear_registry()` | a new `Registry()` per menu |
| `bbsengine6/menu_next/registry.py` | `bbsengine6.registry.Registry` |

The removal was made without compatibility wrappers. The call sites that were updated:

- `casino/src/casino/__init__.py` — `init()` now calls `register_casino_lib_options()` in
  `casino/menus.py`.
- `bbsengine6/py/src/bbsengine6/__init__.py` — exports `Registry` and `MenuOption` and no longer
  exports the removed functions.

## Scoping

A registrar name is the scope. Convention, by owner:

- game modules: `casino.blackjack`, `casino.poker`, …
- command hubs: `casino.commands.game` (shared seat-gated operations)
- core casino: `casino.core`, `casino.lib`

Registrar names are chosen by the module that owns the options. The same letter may appear in two
scopes; each scope is its own namespace.

## Tests

- `bbsengine6/py/tests/test_registry.py` — the generic container: add, get, remove, scopes,
  ordering, fresh lists, instance isolation, thread safety.
- `bbsengine6/py/tests/test_menu_next_registry.py` — menus held in a `Registry`: per-scope and
  all-scope ordering, isolation between menus, concurrent registration.
- `bbsengine6/py/tests/test_menu_next_visibility.py` — `visible_options`.
- casino `tests/test_host_seam.py` — routing between hosted and standalone `choose`.
- letteredolive `shell/tests/test_shell_menu_choose.py` — the hosted `choose` rules.

## See also

- [`channel.md`](channel.md) — the channels a menu may announce to.
- [`../todo/menu_next.md`](../todo/menu_next.md) — remaining work.
