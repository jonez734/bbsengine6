# menu_next — remaining work

Spec: [`../specs/menu_next.md`](../specs/menu_next.md). This file tracks what is still open.
Items already done are recorded in the spec's Status, not here.

## Done (for reference)

- `Registry` replaces the global menu registry (bbsengine6 `3eca3ab`, `0a0a1a4`).
- `CommandRegistry` storage moved onto `Registry` (bbsengine6 `52053c1`).
- casino's door menu is a `Registry` in `casino/menus.py` (casino `392d3fc`).
- letteredolive's `choose` reads a `Registry` through `io.inputstring` (letteredolive `d2c75a0`).

## Superseded

The earlier plan was a module-based registry: each game's `__init__.py` would declare
`menu(args, **kw)`, `init()` would register it with `apis={"menu": ...}`, and
`registered_options()` would walk `get_all_modules()`. That was not built. The shipped design
keeps one `Registry` per menu, and the spec describes it. These are closed, not carried forward:

- rewrite `registered_options()` to walk `get_all_modules()`;
- drop `register_menu_options` from `menu_next/__init__.py` and `bbsengine6/__init__.py`
  (already done, by a different route);
- rewrite `test_menu_next_registry.py` for the module shape;
- per-game `menu()` in `casino/blackjack`, `poker`, `slots`, `yahtzee`, `commands/game`, and a
  `commands/tictactoe` shim;
- `casino/client/__init__.py` as a registered module.

## Open

- [ ] **Retire `casino/src/casino/menu_lib.py`.** Seven files still import it: `client/menu.py`,
      `commands/slots/lib.py`, `main.py`, and the tests. Move each to
      `bbsengine6.menu_next` (`MenuOption`, `visible_options`) and delete the module.
      (casino repo.)
- [ ] **Decide the client menu.** The WS-client menu in `casino/client/menu.py` still uses its own
      option tuple. Decide whether it becomes a second `Registry` (scope `casino.client`) in
      `casino/menus.py`, as the door menu is. Its letters differ from the door menu's, so the
      scopes must stay separate.
- [ ] **Per-game menu options.** Blackjack, poker, slots, yahtzee, and the tictactoe commands
      still list their actions inline. Decide whether each game's options go into a registry
      scope (`casino.blackjack`, …) that the door menu reads, or stay where they are.
- [ ] **Tests for the shipped design.** `casino/tests/test_menu_registration.py` (per-scope
      contract) does not exist. Add one for each scope once the decision above is made.
- [ ] **Handbook.** `bbsengine6/handbook/specs/architecture.md`, `decisions.md`, `flows.md`, and
      `dependencies.md` still describe `register_menu_options`. Point them at the spec.
      (Tracked in this repo; see the pointer work in the same change.)
