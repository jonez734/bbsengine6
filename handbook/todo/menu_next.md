# menu_next — remaining work

Spec: [`../specs/menu_next.md`](../specs/menu_next.md). This file tracks what is still open.
Finished work is described in the spec, not here.

## Done (bbsengine6)

- `Registry` replaces the global menu registry (`3eca3ab`, `0a0a1a4`); `CommandRegistry` storage
  moved onto `Registry` (`52053c1`).
- `MenuOption` gains `aliases`, `alias_subcommand`, `parser`, `sysop_only`, `op`, `subcommands`
  (`76f9b04`).
- `visible_options` gains the `sysop_only` and `check` gates; `menu_entries` returns enabled flags
  for help (`75132d2`).
- `read_menu` and `Choice` for alias-aware command entry (`ed6bdda`), with tests (`7f97b9e`).
- `menu.item.enabled` / `menu.item.disabled` skin keys match `listbox.item.*` (`fd04d09`,
  `a25c76e`).

## Superseded

The earlier plan was a module-based registry: each game's `__init__.py` would declare
`menu(args, **kw)`, `init()` would register it with `apis={"menu": ...}`, and
`registered_options()` would walk `get_all_modules()`. That was not built. The shipped design
keeps one `Registry` per menu. These items are closed, not carried forward:

- rewrite `registered_options()` to walk `get_all_modules()`;
- drop `register_menu_options` from `menu_next/__init__.py` and `bbsengine6/__init__.py`
  (already done, by a different route);
- rewrite `test_menu_next_registry.py` for the module shape;
- per-game `menu()` in `casino/blackjack`, `poker`, `slots`, `yahtzee`, `commands/game`, and a
  `commands/tictactoe` shim;
- `casino/client/__init__.py` as a registered module.

## Open (bbsengine6)

- [x] **Handbook: `architecture.md`, `decisions.md`, `flows.md`, `dependencies.md`** now point at
      the spec and no longer name the removed API.
- [x] **Handbook: `io/io_inputchoice.md`** checked; it documents the `inputchoice` primitive and
      does not describe menus, so it stays as it is.
- [x] **`menu_next/visibility.py` return shape.** Decided: keep both. `visible_options` returns the
      list of options a caller may pick (menu, `read_menu`, slots), and `menu_entries` returns
      `(option, enabled)` pairs for help screens that show disabled entries dimmed. Changing
      `visible_options` to pairs would touch every caller for no gain.
- [x] **`read_menu` dispatch.** The `bet` route (`game bet` for blackjack, `poker bet` for poker)
      lives in casino dispatch (`casino c5602b7`, `0e27174`). No bbsengine6 caller needs it.

## Open (casino and letteredolive, tracked here for the cross-repo picture)

- [x] **Retire `casino/src/casino/menu_lib.py`.** No file imports it. Removed in `ff4aa88`.
- [x] **Client menu via `read_menu`.** `casino/client/menu.py` reads the word-keyed menu with
      `read_menu` (`casino 0e27174`), with aliases and subcommands.
- [x] **Hosted menu input.** Decided differently from the original item: LO's `choose` stays a
      key-membership reader for the letter submenus. The main menu reads through the `read_line`
      seam (`letteredolive 5f8dc18`, `casino c26e6e2`), so hosted and standalone share the rules.
- [x] **Per-game menu options.** Decided: no per-game registry scopes. Every entry lives on the
      client menu spec (`casino/client/menu.py`), each naming its owning package and access op.
      The leftover registry in `casino/menus.py` (the old door menu, read by nothing) and the
      dead `casino/games/menu.py` were removed in the casino commit that closes this item.
- [x] **Tests for the shipped design.** Closed without `test_menu_registration.py`: it pinned the
      per-scope contract, which is not shipped. The shipped menu is covered by
      `casino/tests/test_client.py` (visibility, help) and `test_menu_inline_prompt.py`
      (the prompt), and by bbsengine6's `test_menu_next_read.py`.
