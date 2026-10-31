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
- [ ] **`menu_next/visibility.py` return shape.** The plan had `visible_options` return
      `(option, enabled)` pairs. It returns plain options, and `menu_entries` returns pairs. Decide
      whether to keep both, since the 52 casino call sites use the list form.
- [x] **`read_menu` dispatch.** The `bet` route (`game bet` for blackjack, `poker bet` for poker)
      lives in casino dispatch (`casino c5602b7`, `0e27174`). No bbsengine6 caller needs it.

## Open (casino and letteredolive, tracked here for the cross-repo picture)

- [x] **Retire `casino/src/casino/menu_lib.py`.** No file imports it. Removed in `ff4aa88`.
- [x] **Client menu via `read_menu`.** `casino/client/menu.py` reads the word-keyed menu with
      `read_menu` (`casino 0e27174`), with aliases and subcommands.
- [x] **Hosted menu input.** Decided differently from the original item: LO's `choose` stays a
      key-membership reader for the letter submenus. The main menu reads through the `read_line`
      seam (`letteredolive 5f8dc18`, `casino c26e6e2`), so hosted and standalone share the rules.
- [ ] **Per-game menu options.** Blackjack, poker, slots, yahtzee, and tictactoe still list their
      actions inline. Decide whether each game's options go into a registry scope
      (`casino.blackjack`, …) that the client menu reads.
- [ ] **Tests for the shipped design.** `casino/tests/test_menu_registration.py` (per-scope
      contract) does not exist. Add one once the scope decision is made.
