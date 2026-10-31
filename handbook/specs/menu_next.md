# bbsengine6.menu_next — menu options, command entry, and visibility

## Status

Implemented in bbsengine6. `menu_next` holds the menu-option layer: `MenuOption`, the
visibility filter `visible_options`, and the command reader `read_menu`. A menu is a `Registry` of
`MenuOption`s. There is no process-wide menu registry.

- `bbsengine6/py/src/bbsengine6/menu_next/options.py` — `MenuOption`.
- `bbsengine6/py/src/bbsengine6/menu_next/visibility.py` — `visible_options`, `menu_entries`.
- `bbsengine6/py/src/bbsengine6/menu_next/read.py` — `read_menu`, `Choice`.
- `bbsengine6/py/src/bbsengine6/registry.py` — the generic `Registry` the menus are built on.
- `bbsengine6/py/src/bbsengine6/io/echo.py` — the `menu.item.enabled` / `menu.item.disabled` skin keys.

The casino client menu (`casino/src/casino/client/menu.py`) is the first full consumer. Remaining
consumer work is tracked in [`todo/menu_next.md`](../todo/menu_next.md).

## Design

### `Registry`

`bbsengine6.registry.Registry` is a thread-safe container of items, grouped by an optional scope.
It holds no visibility, tier, or letter rules; the caller supplies those.

- `add(key, item, scope=None)` — store an item. Adding an existing key in the same scope replaces it
  in place.
- `remove(key, scope=None)` — drop an item. Raises `KeyError` if absent.
- `get(key, scope=None, default=None)`.
- `items(scope=None)` — one scope's items, in insertion order. `items(all_scopes=True)` returns
  every item, scopes in sorted order (unscoped first).
- `keys(scope=None)`, `scopes()`, `clear()`, `len()`, and `in`.

`items()` and `keys()` return fresh lists. Each registry is independent; two menus share no state.

### `MenuOption`

A frozen dataclass describing one menu entry. Fields:

| Field | Default | Meaning |
|---|---|---|
| `letter` | (required) | The stored key. `read_menu` returns it as `Choice.key`. |
| `label` | (required) | Help and prompt text. |
| `module_path` | `None` | The module the entry dispatches to. With `op`, it is checked by `check`. |
| `requires_seated` | `False` | Shown only when `state.current_table_moniker` is set. |
| `allowed_game_types` | `None` | With `requires_seated`, shown only at a table whose game type is in the set. |
| `hide_if_seated_type` | `None` | Hidden while seated at a table whose game type is in the set. |
| `requires_connected` | `False` | Shown only when `state.connected` is truthy. |
| `aliases` | `()` | Other typed names for this entry. |
| `alias_subcommand` | `None` | Maps an alias to a subcommand name, so the alias runs that subcommand. |
| `parser` | `None` | `argparse.ArgumentParser` from the owning command's `buildargs()`. `None` means no arguments. |
| `sysop_only` | `False` | Shown only when `state.is_sysop` is truthy. |
| `op` | `None` | The access operation passed to the owning module's `access()`. |
| `subcommands` | `None` | Mapping of subcommand name to `MenuOption`. Each carries its own gates. |

`parser`, `alias_subcommand`, and `subcommands` are excluded from equality and hashing. The new
fields are optional and come after the original ones, so existing positional construction still
works.

### `visible_options`

`visible_options(options, state, check=None) -> list[MenuOption]` filters `MenuOption`s against a
duck-typed player state. It reads `current_table_moniker`, `current_table_game_type`, `connected`,
and `is_sysop`. Missing attributes count as false or `None`.

Gates, in order. Any failing gate hides the option:

1. `sysop_only` — hidden unless `state.is_sysop`.
2. `requires_seated` — hidden unless seated.
3. `requires_seated` with `allowed_game_types` — hidden unless the table's game type is in the set.
4. `hide_if_seated_type` — hidden while seated at a matching table.
5. `requires_connected` — hidden unless connected.
6. `check` — when `check` is given and the option has both `module_path` and `op`, the option is
   shown only when `check(module_path, op)` returns exactly `True`. `False`, `None`, and an
   exception all hide it.

`menu_entries(options, state, check=None)` returns `(option, enabled)` pairs for every option.
Help screens use it to show disabled entries dimmed with `menu.item.disabled`.

`visible_options` is pure: it does not import `bbsengine6.util` or `bbsengine6.database`.

### `read_menu`

`read_menu(prompt, spec, *, state=None, check=None, default="", help=None) -> Choice` reads one
command line with `io.inputstring`.

Resolution:

- The first word selects an entry. It matches the stored key or an alias, case-insensitively, and
  only enabled entries are indexed.
- An alias listed in `alias_subcommand` selects its subcommand. With `alias_subcommand={"hit": "hit"}`
  on the `g` entry, `hit` means `g hit`. Every word typed after the alias is an argument.
- Otherwise, for an entry with `subcommands`, the next word selects an enabled subcommand. Its
  remaining words are arguments.
- Arguments go to the selected subcommand's `parser` if it has one, otherwise to the entry's
  `parser`. An entry or subcommand without a parser rejects extra words.

Input rules:

- An invalid line beeps and re-prompts. This is `inputstring`'s `verify` behavior. A line is
  invalid when the key or subcommand is unknown or disabled, the quoting is unbalanced, the
  parser rejects the arguments, or extra words follow a parser-less entry.
- A parser that calls `sys.exit` is caught, so a bad argument never ends the session.
- An empty line returns `default` when one is given. `default` must be a key in the menu, or
  `read_menu` raises `ValueError`.

Completion (`Tab`) offers the enabled keys and aliases for the first word. After an entry with
subcommands and a space, it offers that entry's enabled subcommand names.

`Choice(key, args=None, subcommand=None)`:

- `key` — the canonical stored key. An alias is never returned.
- `subcommand` — the subcommand name, or `None`.
- `args` — the parsed `argparse.Namespace`, or `None` when no parser applies.

Dispatch (for example, sending `bet` to `game bet` or `poker bet`) is the caller's job. It uses
`key`, `subcommand`, and the seated table's game type.

### Skin keys

`menu.item.enabled` and `menu.item.disabled` style help entries. They use the same values as
`listbox.item.normal` and `listbox.item.disabled`, so a menu and a listbox look alike:

| Key | Value |
|---|---|
| `menu.item.enabled` | `{white}` |
| `menu.item.disabled` | `{darkgray}` |

## Removed API

The first version of `menu_next` held a global registry in the module. It is gone. Callers should
not use these names:

| Removed | Replacement |
|---|---|
| `register_menu_options(registrar, *options)` | `registry.add(letter, option, scope=registrar)` |
| `registered_options(name=None)` | `registry.items(scope)` or `registry.items(all_scopes=True)` |
| `clear_registry()` | a new `Registry()` per menu |
| `bbsengine6/menu_next/registry.py` | `bbsengine6.registry.Registry` |

The removal was made without compatibility wrappers.

## Scoping

A registrar name is the scope. Convention, by owner:

- game modules: `casino.blackjack`, `casino.poker`, …
- command hubs: `casino.commands.game` (shared seat-gated operations)
- core casino: `casino.core`, `casino.lib`

The same letter may appear in two scopes; each scope is its own namespace.

## Tests

- `bbsengine6/py/tests/test_registry.py` — the generic container.
- `bbsengine6/py/tests/test_menu_next_registry.py` — menus held in a `Registry`.
- `bbsengine6/py/tests/test_menu_next_visibility.py` — `visible_options`, `sysop_only`, `check`,
  `menu_entries`.
- `bbsengine6/py/tests/test_menu_next_read.py` — `read_menu`: aliases, alias subcommands, parser
  success and failure, extra words, subcommand gating, completion, `default`, and the `check` gate.
- `bbsengine6/py/tests/test_echo_menu_item_skin.py` — the `menu.item.*` skin keys.

## See also

- [`channel.md`](channel.md) — the channels a menu may announce to.
- [`../todo/menu_next.md`](../todo/menu_next.md) — remaining work.
