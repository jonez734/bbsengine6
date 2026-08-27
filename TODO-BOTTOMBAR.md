# TODO: bottombar thin-client wire push (single source of truth)

> **This file owns every TODO item related to pushing the bottombar
> status bar from the bbsengine6 / bed process to a thin client.**
> Per-package fragment registration (casino, empyre, bed bank, etc.),
> the per-connection `FragmentRegistry`, and the BED-side wire push
> envelope all live here. Non-bottombar items (general `echo`,
> `BEDSink.echo`, `BEDSink.inputchoice`, `WebSocketServer.on_connect_hook`
> as a general mechanism, etc.) stay in their owning TODO files and
> are referenced here only when they intersect with the bottombar.

## Status (2026-08-26)

The in-process `FragmentRegistry` and per-connection routing are done:

- [x] `bbsengine6.bottombar` module with `FragmentRegistry`,
      `default_registry()`, `setbottombar`, register/unregister/clear
      helpers (`bbsengine6/py/src/bbsengine6/bottombar.py`).
- [x] `bbsengine6.io.screen` reduced to back-compat shims
      (`bbsengine6/py/src/bbsengine6/screen.py:157-216`).
- [x] `bbsengine6.bottombar.registry_for(name)` factory +
      `set_context_for` / `render_for` for per-package registries
      (`bottombar.py:316-348`).
- [x] Per-connection ContextVar routing via `_active_registry`,
      `set_active_registry(reg)` / `reset_active_registry(token)`
      (`bottombar.py:267-271, 351-363`). Door mode (no ContextVar
      set) is unchanged.

What's NOT done — the wire push to a thin client — is below.

---

## Phase 5a — `render_structured()` separates "render" from "layout"

The terminal-width mismatch between server (bed's own stdout) and
client (40/80/100 columns) is the reason a fully-pre-rendered
bottombar string cannot be shipped over the wire. The server has no
way to know the client's width without an extra round-trip, and a
fragile one at that (resize events, connect ordering, MCI tokens).

Solution: split `_render_bottombar` into two steps. The server does
**rendering** (MCI substitution, fragment concatenation, notification
prepend). The client does **layout** (terminal-width measurement,
left-truncation, padding, cursor positioning).

- [ ] Add `bbsengine6.bottombar.render_structured(registry, left,
      **kwargs) -> dict` returning
      `{"left": str, "right": List[str], "separator": " | ",
      "left_priority": "truncate", "ts": iso}`.
      - Pre-renders each fragment string via
        `bbsengine6.io.echo.echo(item, wordwrap=False, end="")` so
        the client receives MCI-substituted text (no server-side
        width math baked in).
      - `right` is the post-`FragmentRegistry.render()` list split
        on `" | "` — same shape the door-mode renderer produces
        internally.
      - `left_priority` defaults to `"truncate"` (truncate with
        `...` if too long); a future game may emit `"drop"` or
        `"ellipsize"`.
      - The notification fragment (`F2: messages (N)`) is prepended
        to `right` exactly as today.
- [ ] Refactor `_render_bottombar(registry, left, right, **kwargs)`
      (`bottombar.py:419-467`) into two functions:
      - `_render_bottombar_structured(registry, left, **kwargs) ->
        dict`: calls `render_structured`, returns the dict.
      - `_render_bottombar_layout(structured, width) -> str`: takes
        a structured dict + a width, returns the ANSI cursor
        sequence for the last line (the existing truncation +
        padding + emit logic, parameterized on width).
      - Door mode calls `setbottombar` → `_resolve_registry` →
        `_render_bottombar_structured` → `_render_bottombar_layout(
        structured, terminal.width() - 2)` → existing ANSI
        emission. **Byte-for-byte identical output for door mode.**
- [ ] **Backward compat check**: `py/tests/test_bottombar.py` and
      `py/tests/test_screen.py` pass unchanged. Door-mode
      byte-for-byte parity is the regression bar.

---

## Phase 5b — `echo{stream:"bottombar"}` wire push

The bottombar reaches the thin client via the generic `echo` push
channel already planned in `bed/TODO.md` "`echo` and `echo_ack` —
generic push-based text channel". This phase makes the bottombar a
named `echo` stream; it does not introduce a new top-level wire type.

### Wire shape
```json
# Server → client: bottombar update on the "bottombar" stream
S→C {"type":"echo",
     "request_id":"r42",
     "stream":"bottombar",
     "seq":17,
     "payload":{
       "left":"In casino lobby",
       "right":["127.0.0.1:8765","alice","3 credits","F2: messages (3)"],
       "separator":" | ",
       "left_priority":"truncate"},
     "flush":false,
     "ts":"2026-08-26T11:30:01Z"}
```

The `echo` envelope, `request_id`, `seq`, `flush`, and `ts` semantics
are owned by `bed/TODO.md` "echo and echo_ack". The bottombar
**payload** shape (the four fields above) is owned by this file.

### Why `stream="bottombar"` and not a separate `setbottombar` type
- The `echo` envelope already defines three streams (`main`,
  `bottombar`, `statusline`) at `bed/TODO.md:194-214`. A separate
  top-level `setbottombar` type would duplicate the transport
  contract (seq, flush, ack, cancel, reconnect-resume) without
  reusing it.
- `echo{stream:"bottombar"}` carries the bottombar payload in
  `echo.payload`. The thin client dispatches on
  `msg.get("stream") == "bottombar"`.
- `bed/TODO.md:1067-1071` (BEDSink's bottombar methods) is
  absorbed into the generic `BEDSink.echo` path: the sink checks
  the active registry, calls `render_structured`, and ships the
  payload.

### Tasks
- [ ] Add `bbsengine6.bottombar.to_echo_payload(registry, left,
      **kwargs) -> dict` returning the four-field payload above.
      Thin wrapper over `render_structured` that strips
      `ts`/`request_id`/`seq` (those are added by `EchoService`,
      not by the bottombar).
- [ ] Add `bbsengine6.io.sink._STREAM_BOTTOMBAR: ContextVar[str] =
      ContextVar("bbsengine6_io_sink_stream_bottombar", default="")`.
      Set by `bbsengine6.io.screen.setbottombar` /
      `register_bottombar_fragment` /
      `unregister_bottombar_fragment`'s sink-dispatch path; read
      by `BEDSink.echo` to choose `stream="bottombar"` vs
      `stream="main"`. No kwarg change to the public `setbottombar`
      signature.
- [ ] `BEDSink.echo(text, **kwargs)` (in `bed/sinks/bed_sink.py`,
      defined per `bed/TODO.md:1041-1101`) gains a
      `stream="bottombar"` path: when
      `_STREAM_BOTTOMBAR.get() == "1"`, the sink reads the active
      `FragmentRegistry`, calls
      `bbsengine6.bottombar.to_echo_payload`, and ships an `echo`
      envelope with `stream="bottombar"` instead of `stream="main"`.
      The sink ignores `text` in this path (the structured payload
      is the source of truth).
- [ ] `bbsengine6.io.screen.setbottombar` /
      `register_bottombar_fragment` /
      `unregister_bottombar_fragment` (the back-compat shims at
      `bbsengine6/py/src/bbsengine6/screen.py:157-216`) gain a
      sink-dispatch path: when a sink is installed, they
      `_STREAM_BOTTOMBAR.set("1")`, call
      `sink.setbottombar(...)` /
      `sink.register_bottombar_fragment(...)` /
      `sink.unregister_bottombar_fragment(...)`, then reset the
      contextvar in a `finally` block. The sink is responsible
      for translating to `echo{stream:"bottombar"}`. **Per
      `bed/TODO.md §"Phase 0 — BEDSink for the BED process"`**
      (lines 1067-1071, rephrased to point here).
- [ ] `register_*` / `unregister_*` through the sink trigger a
      **full re-render** on the client — the server pushes a
      fresh `echo{stream:"bottombar"}` envelope with the updated
      `right[]` (no per-fragment delta wire type). The thin
      client never maintains its own fragment registry; the
      structured `payload.right[]` from the server is the
      source of truth.
- [ ] `bed/client/bottombar.py` (new file, ~40 lines): the thin
      client receives `echo` envelopes and dispatches by stream.
      On `stream="bottombar"`, the handler does the client-side
      layout step (terminal width measurement, truncation,
      padding, cursor positioning) — port of
      `_render_bottombar_layout` from Phase 5a. Door-mode games
      that use the existing `sys.modules` swap never see these
      envelopes.

### Tests
- [ ] `bbsengine6/py/tests/test_render_structured.py`:
    - `render_structured` returns the four-field dict for a
      registry with two string fragments + two callable
      fragments.
    - Notification fragment is prepended to `right` when
      `get_notification_status()` returns a non-empty count.
    - `left_priority` defaults to `"truncate"`.
    - Each fragment string in `right` is MCI-substituted (run
      `bbsengine6.io.echo.echo(item, wordwrap=False, end="")` on
      it before adding to the list).
- [ ] `bbsengine6/py/tests/test_render_structured_door_parity.py`:
    - For a battery of `(left, registry contents)` inputs,
      `_render_bottombar_layout(render_structured(...),
      terminal.width() - 2)` produces byte-for-byte identical
      output to the current `_render_bottombar(...)`. Asserts
      equality against a snapshot of the legacy output.
- [ ] `bbsengine6/py/tests/test_sink_stream_bottombar.py`:
    - `_STREAM_BOTTOMBAR.set("1")` before calling
      `sink.echo("hello")` makes the sink ship
      `stream="bottombar"` instead of `stream="main"`.
    - The contextvar is reset in `finally` even when the sink
      raises.
    - Two concurrent asyncio tasks with different contextvar
      values see different streams (contextvar semantics).
- [ ] `bed/tests/test_echo_bottombar_payload.py`:
    - `BEDSink.setbottombar("left")` builds an `echo` envelope
      with `stream="bottombar"` and `payload={left, right,
      separator, left_priority}`.
    - The same call via the sink-dispatched
      `bbsengine6.io.screen.setbottombar` produces the same
      envelope (proves the contextvar → sink path).
    - `register_bottombar_fragment` / `unregister_bottombar_fragment`
      through the sink ship `echo` envelopes with the
      **updated** `right[]` (full re-render, not a delta).
- [ ] `bed/tests/test_thin_client_bottombar_layout.py`:
    - Given an `echo{stream:"bottombar", payload:{...}}` envelope
      and a known terminal width (40, 80, 100), the client-side
      layout produces the expected left-truncated / padded
      string.
    - At 80 columns, the rendered string fits in one line.
    - At 40 columns, `left` is truncated with `...` and `right`
      is preserved in full.
    - At 100 columns, both fit with extra padding.
    - `left_priority="drop"` (future value) is accepted and
      produces a left-empty, right-only string.

### Door-mode byte-for-byte parity
- [ ] Door mode never sets `_STREAM_BOTTOMBAR` and never sends an
      `echo` envelope — there's no websocket to send to.
      `bbsengine6.bottombar.setbottombar` continues to call
      `_render_bottombar_layout` → `bbsengine6.io.echo` with
      byte-for-byte identical output. `py/tests/test_bottombar.py`
      and `py/tests/test_screen.py` pass unchanged.
- [ ] When a sink IS installed but no websocket is attached
      (e.g. a unit test), `setbottombar` falls back to the
      default registry path. The sink is responsible for
      buffering or dropping the call.

---

## Per-package fragment registration (consolidated)

Each game package owns its fragments via
`bbsengine6.bottombar.registry_for(name)`. This section is the
**canonical** list of per-package items; the game repos (`casino`,
`empyre`, `bed bank`, `mistermcfeely`, `murdermotel`, `zoid6`)
cross-reference here instead of duplicating. Game-specific call
sites (e.g. empyre's 14 `setbottombar` calls) stay in the game's
own TODO file.

### `casino` (`bbsengine6.bottombar.registry_for("casino")`)
- [x] `casino/src/casino/lib.py:440` — `_casino_registry =
      bottombar.registry_for("casino")`.
- [x] Three fragments registered in
      `casino/src/casino/lib.py:458-488`:
      `_casino_host_fragment` (host:port or "direct"),
      `_casino_player_fragment` (bound moniker),
      `_casino_credits_fragment` ("N credits" / "a credit" / "no credits").
- [x] `casino/src/casino/lib.py:539-566` —
      `casino.lib.setbottombar(args, buf, **kwargs)` delegates to
      `bbsengine6.bottombar.setbottombar`.
- [x] Registration on entry / cleanup on exit
      (`casino/src/casino/main.py:125, 147`).
- [ ] **Pending**: thin-client fragment `_casino_table_fragment`
      at `casino/src/casino/TODO_CLIENT.md:137-154` —
      `bbsengine6.bottombar.registry_for("casino").register(...)`.
      Migrate from the deprecated back-compat shim to the
      registry API. Tracked here, not in `casino/TODO_CLIENT.md`.
- [ ] **Pending**: casino thin-client path calls
      `BEDSink.setbottombar(...)` on every `bbsengine6.bottombar
      .setbottombar` call, so the live bottombar updates on the
      thin client whenever door-mode casino pushes. Game-repo
      task lives in `casino/TODO.md` cross-reference section
      (single line pointing here).

### `empyre` (`bbsengine6.bottombar.registry_for("empyre")`)
- [ ] **Pending migration** (was
      `bbsengine6/TODO-BOTTOMBAR.md:168-199`):
      `empyre/src/empyre/lib.py:99` constructs
      `bottombar.FragmentRegistry(name="empyre")` directly. Swap
      to `bottombar.registry_for("empyre")` (one-line change;
      cached, so `_empyre_registry.args` / `__contains__` /
      `__iter__` reads continue to work unchanged).
- [ ] **Pending**: review empyre's `setbottombar` call sites
      (14 sites across `empyre.player`, `empyre.main`,
      `empyre.market`, `empyre.combat.joust`,
      `empyre.combat.main`, `empyre.town.main`,
      `empyre.town.lucifersden`,
      `empyre.town.naturaldisasterbank`, `empyre.maint.main`,
      `empyre.generatenpc`, `empyre.quests.main`,
      `empyre.ship.lib`, `empyre.sysopoptions`) for whether
      they should call
      `bottombar.set_context_for("empyre", ...)` before
      `bottombar.setbottombar(...)` to ensure the right
      registry gets the stashed context. Follow-up pass after
      the casino migration is the prototype. **Game-repo task
      lives in `empyre/TODO.md`**, not here.
- [ ] **Pending** (was `empyre/TODO.md:237`): mirror the three
      empyre fragments from `lib.init` to the thin client at
      `auth` time; re-push on every `register_*` call. Adopt
      `BEDSink.setbottombar(...)` in the empyre thin-client
      entry path. **Game-repo task lives in `empyre/TODO.md`**,
      not here.
- [ ] **Pending** (was `empyre/TODO.md:115-122`):
      `screen.setbottombar` / `register_*` / `unregister_*` push
      `echo{stream:"bottombar"}` frames in Phase 5b. Out of
      scope for empyre's Phase 1a (which only handles
      `stream="main"`). **Game-repo task lives in
      `empyre/TODO.md`**, not here.

### `bed bank` (`bbsengine6.bottombar.registry_for("bed")`)
- [x] `bed/src/bed/tools/bank.py:765-810` —
      `_register_bank_fragments` with `_bank_host_fragment` and
      `_bank_moniker_balance_fragment`.
- [x] `bed/src/bed/tools/bank.py:887, 924` —
      `bottombar.setbottombar(...)` call sites in the bank tool.
- [ ] **Pending**: thin-client push — bank tool's `setbottombar`
      calls happen in the BED process, so on a thin-client
      connection the push goes through `BEDSink.setbottombar`
      automatically once the bank tool is given the websocket
      handle. Game-repo task: pass the websocket handle to the
      bank tool from BED's per-connection setup.

### Other packages
- [ ] **Future**: `mistermcfeely` (postoffice), `murdermotel`,
      `zoid6` — `registry_for("<name>")` factory is generic;
      per-package migration is one-line. Cross-reference here
      when each game adopts the bottombar push.

---

## Cross-references

- `bbsengine6/TODO.md` §"Phase 0-5 sink infrastructure" — owns
  the `bbsengine6.io.sink.Sink` protocol and `set_io_sink` /
  `reset_io_sink`. **Phase 5b of this file does not depend on it
  for the bottombar primitives** — the bottombar reaches the wire
  through `BEDSink.setbottombar`, which is a sink method like the
  other 10 primitives but only the bottombar primitives use it.
- `bbsengine6/TODO.md` §"Phase 5 — MessageRouter + MessageRouterMixin
  + WebSocketServer.on_connect_hook" — the hook mechanism. Used
  by `BEDSink` (bed) for installing the per-connection sink.
- `bed/TODO.md` §"echo and echo_ack" — owns the `echo` envelope
  (`type`, `request_id`, `stream`, `seq`, `payload`, `flush`,
  `ts`, `echo_ack`, `echo_cancel`, reconnect-resume). Phase 5b
  of this file uses this envelope as-is and only fills in the
  `payload` shape for `stream="bottombar"`.
- `bed/TODO.md` §"BED Sink integration with bbsengine6.io" —
  owns `BEDSink` and its installation. Phase 5b references this
  for the sink side of the dispatch.
- `casino/TODO.md` — single-line cross-reference: "Bottombar wire
  push: see `bbsengine6/TODO-BOTTOMBAR.md`."
- `empyre/TODO.md` — per-game bottombar items (the 14 call sites,
  the auth-time fragment mirror, the Phase 1a bottombar follow-up)
  live in `empyre/TODO.md` and reference here for the wire shape.
- `zoid6/TODO.md` — single-line cross-reference: "Bottombar wire
  push: see `bbsengine6/TODO-BOTTOMBAR.md`."

---

## Implementation order

1. Phase 5a (`render_structured` + layout split). Door-mode parity
   test (`py/tests/test_screen.py` +
   `py/tests/test_bottombar.py`) is the regression bar.
2. `EchoService` lands in `bed/api/echo.py` per `bed/TODO.md`
   "`echo` and `echo_ack`" + "`echo` envelope plumbing".
3. Phase 5b (`echo{stream:"bottombar"}` wire push via `BEDSink` +
   thin-client layout). Depends on `EchoService` and Phase 5a.
4. Per-package `registry_for("...")` migrations (casino done,
   empyre pending, bed bank done). Game-repo tasks are 1-3 lines
   each, pointing back here.

Backward-compat gates at every step:
- Door-mode byte-for-byte parity (`py/tests/test_screen.py`,
  `py/tests/test_bottombar.py`).
- `py/tests/test_bottombar.py::TestRegistryFor` /
  `TestSetContextForAndRenderFor` / `TestContextVarRouting` /
  `TestScreenShimContextVarRouting` — per-connection plumbing
  invariants.
- `bbsengine6/io/echo` return-value usage stays zero-affecting
  (the `io.echo` Phase 3 return-value change is gated by the
  pre-flight grep result in `bbsengine6/TODO.md` §"Phase 0a
  pre-flight"; the bottombar work touches `io.echo` only via
  `render_structured`'s per-fragment MCI render, which is
  additive and does not depend on the return value).