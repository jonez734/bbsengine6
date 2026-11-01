# TODO: bottombar push() and pop()

Status: planned, not started. Do not build until the user says so.

## Goal

Add `push()` and `pop()` to `bbsengine6.bottombar` so a caller can save the
current bottom bar state (left side and fragments), install new values, and
later restore the saved state with a repaint.

Called as `bottombar.push(...)` and `bottombar.pop(...)`.

## Decisions

1. **Naming.** Module-level `push(left=None, fragments=None)` and
   `pop(**kwargs)`. Both route through `_resolve_registry()`, so BED
   per-connection registries (ContextVar) work the same way as the existing
   helpers.
2. **Legacy API removed.**
   - `screen.py`: delete `popbottombar`, `poparea`, their `__all__` entries,
     `_bottombarstack_lock`, and the `bottombarstack` read-through.
   - `interaction.py:59-60`: delete the `bottombarstack` field.
   - `py/src/testareastack.py:12` and `py/src/testsetarea.py:23`: port
     `poparea()` calls to `bottombar.pop()`. Do not delete them.
   - `py/tests/test_screen.py:670-688`: delete the `bottombarstack` tests.
   - `py/src/bbsengine6/io/specs/screen.spec`: remove `popbottombar` /
     `poparea` entries and the `bottombarstack` note.
3. **Store original values.** Each frame holds the original `left` (str or
   callable) and a copy of the fragment items. Not rendered output.
4. **Repaint on push.** Push installs the new values and repaints. A
   no-argument push saves a frame and repaints with the current values.
5. **Repaint on pop.** Pop restores the top frame and repaints. A saved
   callable `left` is called again. Pop passes the registry's
   `args`/`player`/`pool` plus any kwargs given to `pop()`.
6. **Empty pop.** Returns `False` and does not repaint.
7. **Scope.** A stack on each `FragmentRegistry` instance, guarded by
   `registry.lock`.

## Current code (as of this plan)

- `py/src/bbsengine6/bottombar.py`
  - `FragmentRegistry` holds `items`, `args`, `player`, `pool`. It has no
    `left` attribute.
  - `setbottombar(args, buf, **kwargs)` renders `buf` through
    `_render_bottombar` and discards it. Nothing is stored for restore.
  - `_render_bottombar(registry, left, right, **kwargs)` does the layout and
    emits via `echo`.
- `py/src/bbsengine6/screen.py`
  - `setbottombar` shim (line ~165) calls `_resolve_registry()` and its own
    `updatebottombar`. It does not record `left`.
  - `popbottombar()` / `poparea` (line ~248) pop strings from
    `interaction.bottombarstack` and repaint with `{var:areacolor}`. Nothing
    in the package pushes onto that stack.
- `py/src/bbsengine6/interaction.py:59-60`: `bottombarstack` field.
- Callers of the legacy API: `py/src/testareastack.py:12`,
  `py/src/testsetarea.py:23`. Tests: `py/tests/test_screen.py:670-688`.

## Implementation steps

1. `bottombar.py`: add `FragmentRegistry.left` (initially `None`).
   `setbottombar` and `_render_bottombar` store the original `left` value on
   the registry before rendering. Store the value as given, not `left_buf`.
2. Add `FragmentRegistry._stack: list` of frames `(left, list(items))`.
3. `FragmentRegistry.push(left=None, fragments=None)`:
   - Under `self.lock`, save a frame with the current `self.left` and a copy
     of `self.items`.
   - Install new values. `None` keeps the current value. `fragments=[]`
     clears the fragments.
   - Repaint via `_render_bottombar(self, left=self.left, **merged)`.
4. `FragmentRegistry.pop(**kwargs)`:
   - Under `self.lock`, pop the top frame. If the stack is empty, return
     `False` without repainting.
   - Restore `self.left` and `self.items`.
   - Repaint via `_render_bottombar(self, left=self.left, **merged)`, where
     `merged` is registry context plus kwargs.
   - Return `True`.
5. Module-level `push()` and `pop()` delegate to `_resolve_registry()`. Add
   both to `__all__`.
6. `screen.setbottombar` shim: record `left` on the registry so a push/pop
   that starts from a shim-drawn bar has state to restore.
7. Remove the legacy API per decision 2. Port `testareastack.py` and
   `testsetarea.py` to `bottombar.pop()`.

## Tests (`py/tests/test_bottombar.py`)

- push then pop restores left and fragments.
- push with new values installs them and repaints.
- push with no arguments saves a frame and repaints.
- A callable `left` is stored as the callable; pop calls it again.
- LIFO nesting.
- Empty pop returns `False` and does not repaint.
- Pop repaints (patch `echo`, check the bottombar sequence).
- Module-level `push`/`pop` route to a ContextVar-set registry.
- Two registries keep independent stacks.
- Remaining `test_screen.py` tests pass after legacy removal.

## Docs

- `handbook/specs/bottombar.md`: add a "Push and pop" section and entries in
  the public API table.
- `py/src/bbsengine6/io/specs/screen.spec`: remove legacy entries and
  document push/pop.

## Repo

Changes belong in the `bbsengine6` inner repo. Per `AGENTS.md`, do not
commit without the user asking. Do not put helper scripts in `/tmp/`.
