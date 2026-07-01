# TODO: `bbsengine6.bottombar` architecture and per-connection plumbing

The bottombar is the BBS-style status bar at the bottom of the terminal.
It has a left side (free-form text from the current game/mode) and a
right side (a list of "fragments" — small str or callable(**kwargs) -> str
items registered by whichever package is currently active).

`bbsengine6.bottombar` is the new (as of 2026) home for the fragment
machinery, replacing the process-global `_bottombar_fragments` list and
the per-package `setbottombar(args, buf, **kwargs)` shims that used to
live in `bbsengine6.io.screen`. See `bbsengine6/py/src/bbsengine6/bottombar.py`
and `bbsengine6/py/tests/test_bottombar.py`.

This TODO file tracks bottombar-specific work. The broader `bbsengine6.io`
sink infrastructure that touches the bottombar primitives is tracked in
the main `TODO.md` (`bbsengine6.io` sink infrastructure for thin-client
BED conversion); only the bottombar-specific facets are mirrored here.

## Status (2026-06-30)

- [x] `bbsengine6.bottombar` module created with `FragmentRegistry`,
      `default_registry()`, `setbottombar`, `register_bottombar_fragment`,
      `unregister_bottombar_fragment`, `clear_bottombar_fragments`.
- [x] `bbsengine6.io.screen` reduced to back-compat shims that emit
      `DeprecationWarning` (see `bbsengine6/io/screen.py:_warn_shim_deprecated`).
- [x] `bbsengine6.startup.lib.setbottombar` and
      `bbsengine6.backend.lib.setbottombar` collapsed to one-liner shims
      that delegate to `bbsengine6.bottombar.setbottombar`.
- [x] `empyre.lib.setbottombar` migrated to call
      `bbsengine6.bottombar.setbottombar` directly (no shim).
- [x] `casino.lib.setbottombar` and `casino.auth` migrated to call
      `bbsengine6.bottombar.*` directly.
- [x] `bbsengine6.ed.common.ui.unregister_bottombar` no longer calls
      `screen.clear_bottombar_fragments()` (which clobbered every
      package's fragments) — it now unregisters only the fragments the
      editor itself registered.
- [x] `bbsengine6/tests/test_bottombar.py` covers registry basics,
      per-package independence, set_context, kwargs forwarding,
      notification prepending, thread safety, and screen-shim routing.
- [x] `bbsengine6/tests/test_screen.py` continues to pass unchanged
      (62 tests; shim preserves the old public API).

## Phase 4a — Per-connection `bbsengine6.bottombar.registry_for(name)` plumbing

`bbsengine6.bottombar` (new in this revision) already exposes
`default_registry()` and the `FragmentRegistry` class, plus a back-compat
shim in `bbsengine6.io.screen`. The BED-sink work in the main `TODO.md`
needs to register/unregister fragments **per connection** instead of
process-globally, so that one player's editor status fragment doesn't
bleed into another player's bottombar.

The remaining work is:

- [ ] Add `bbsengine6.bottombar.registry_for(name: str) -> FragmentRegistry`:
  a module-level factory that returns a named, cached `FragmentRegistry`
  instance. The default registry lives at the key `"default"`. Calling
  `registry_for("empyre")` from inside empyre gives empyre a private
  registry; calling it from a BED per-connection setup gives that
  connection a private registry. Pre-implementation test
  (`test_bottombar.py::TestPerPackageRegistries`) already exercises
  the underlying independence.
- [ ] Add `bbsengine6.bottombar.set_context_for(name, **ctx)` and
  `bbsengine6.bottombar.render_for(name, **kwargs)` so BED-sink code
  can stash args/player/pool and render against a named registry
  without going through the default.
- [ ] Wire `screen.setbottombar` and `screen.register/unregister_bottombar_fragment`
  (the deprecated back-compat shims) to look up the per-connection
  registry from a `contextvars.ContextVar` set by the BED connection
  layer, falling back to `default_registry()` for door mode. This is
  the per-connection plumbing that the BED-sink work in the main
  `TODO.md` (Phase 4) implicitly assumes but does not spell out.
- [ ] Update `bbsengine6.bottombar.setbottombar` and the shim
  to read the per-connection ContextVar first, default registry
  second, so door mode is unchanged.
- [ ] **Backward compat check**: door-mode callers see zero behavior
  change because no `ContextVar` is set. `test_screen.py` and
  `test_bottombar.py` pass unchanged.

## Sink-integration facets (mirrored from the main `TODO.md`)

The main `TODO.md` (`bbsengine6.io` sink infrastructure) covers the
general sink mechanism. The bottombar-specific facets of that work,
extracted:

### Sink protocol (Phase 0 in main `TODO.md`)

- [ ] `bbsengine6.io.sink.Sink` protocol includes
  `screen_setbottombar`, `screen_register_bottombar_fragment`,
  `screen_unregister_bottombar_fragment` methods.
- [ ] `bbsengine6.io.sink.DefaultSink` delegates those to the
  current `bbsengine6.io.screen._impl_*` private functions (the
  back-compat shim paths in `bbsengine6.io.screen` become the
  default-sink targets).

### Per-primitive sink dispatch (Phase 0 in main `TODO.md`)

- [ ] Refactor `bbsengine6.io.screen.setbottombar` into:
  - `def _impl_screen_setbottombar(left, right=None, **kwargs)`:
    the current code path.
  - `def setbottombar(...)`: the public function. If
    `_active_sink.get()` returns a non-`None` sink, dispatch to
    `sink.screen_setbottombar(...)`. Otherwise call
    `_impl_screen_setbottombar(...)`.
- [ ] Same for `register_bottombar_fragment` and
  `unregister_bottombar_fragment`.
- [ ] **Backward compat check**: door-mode callers see zero behavior
  change. `test_screen.py` and `test_bottombar.py` pass.

### Sink variants (Phase 4 in main `TODO.md`)

- [ ] `screen.setbottombar`, `screen.register_bottombar_fragment`,
  `screen.unregister_bottombar_fragment` all need sink-based
  variants.
- [ ] **Backward compat check**: door-mode callers see zero behavior
  change. `test_io_backward_compat.py` passes.

## Cross-references

- `bbsengine6/TODO.md` — main engine TODO; sections `bbsengine6.io`
  sink infrastructure (Phases 0, 3, 4, 5) cover the sink plumbing
  that the bottombar primitives participate in.
- `bbsengine6/TODO.md` — the F2-key "pending message count in
  bottombar" item and the `get_notification_status()` design belong
  to the message-delivery work, not to the bottombar-architecture
  work, so they stay in the main TODO.
- `empyre/TODO.md`, `bed/TODO.md` — per-game bottombar push
  work; the thin-client BED conversion uses the per-connection
  registry plumbing from Phase 4a above.
