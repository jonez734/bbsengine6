# bbsengine6 — UI seam specification (generic core)

> **Last updated:** 2026-11-11.
> **Status:** Part A is implemented in `py/src/bbsengine6/seam/` (`codes.py`, `results.py`,
> `events.py`), with tests in `py/tests/test_seam_types.py`. A consuming application (for example
> casino) keeps its per-game sections in its own handbook.
> **Structure:** Part A is generic and lives here. Part B is per game and lives with the game.
> A new game adds a Part B section and does not change Part A.

## 1. Purpose

An application built on bbsengine6 may need more than one user interface: a terminal UI today, and
Tk, GTK, or Qt later. The game and service code must not decide how a result is shown or how
input is read. This spec defines the seam between any game and any UI:

- Game code returns a typed **result** and emits typed **events**. It never calls `io.echo` or
  `io.input*`.
- A UI reads the player's input and sends typed **requests** to the game. It never reads game
  state except through results and events.
- Each UI consumes the same results and events on its own event loop.

## 2. Current state (verified, per game)

The current state is recorded per game in Part B. Across the games today:

- Each game's service returns a plain `dict[str, Any]`. Refusals are
  `{"success": False, "message": "..."}` with no code.
- Slots and yahtzee return their own dict shapes from their dealers and services.
- Services call `io.echo` for logs, status text, and refusal messages. Those calls mix three
  things that the seam separates (sections 5 and 6).

## 3. Result type

```python
@dataclass(frozen=True)
class ActionResult:
    ok: bool                      # True when the action happened
    code: str                     # "ok" on success; otherwise a code from section 4
    message: str = ""             # display text only; never branched on
    data: Mapping[str, Any] = {}  # typed payload for the action (see section 6)
```

- `ok` and `code` are the contract. Logic branches on `code`, never on `message`.
- `message` is for display. A UI may translate it by `code`.
- Every game method returns `ActionResult`. The method's own payload goes in `data`.

## 4. Result codes

**One owner.** The code vocabulary is defined once, as the `ErrorCode` enum in
`bbsengine6.seam.codes`. No other module defines a code. A consuming application imports the
enum and adds its game codes to its own copy of the vocabulary only by adding them here first.

**Current state, not yet met (in casino):** `api/messages.py` has its own `ErrorCode` enum,
`api/_auth.py` defines `CODE_*` constants (for example `CODE_NOT_AUTHENTICATED`), and
`api/handler.py` repeats string literals (for example `"not_at_table"`). Casino moves these to the
bbsengine6 enum before a game migrates. That is the first step of the migration, and it changes
no wire output.

**Generic codes** apply to every game and are the same for every game:

| Code | Meaning |
|---|---|
| `ok` | The action happened |
| `table_not_found` | No table with that moniker |
| `not_at_table` | The member is not seated at the table |
| `invalid_bet` | The bet is not a valid amount |
| `insufficient_funds` | The member cannot pay the amount |
| `invalid_action` | The action is not allowed in the current state |
| `forbidden` | Operation not permitted |
| `service_error` | Unexpected failure inside the service |

**Game codes** are added by a game's section in Part B, and each one goes into the enum. A game
code names a refusal the game makes, not a message. The refusal text stays in `message`.
A game's codes are listed in its own per-game section, which lives with the game (for casino's
blackjack, see `casino/handbook/specs/ui-seam.md`, section 12).

A game may not invent a code that duplicates a generic one (for example `no_funds` next to
`insufficient_funds`).

## 5. Events

Implemented in `bbsengine6.seam.events`: `Event`, `MESSAGE_KINDS`, `game_kind` /
`register_game_kind` (a game registers its kinds before it emits them), and `EventQueue`. The
queue rejects `warn` and any kind that is neither a message kind, `fragment`, nor registered.

A game emits events to a queue. The queue is the only channel for game progress. Events come in
two groups, and the seam treats them differently.

```python
@dataclass(frozen=True)
class Event:
    kind: str            # a message kind (below) or a game kind (Part B)
    table: str           # table moniker
    moniker: str | None  # acting or affected member, when there is one
    payload: Mapping[str, Any]
```

**Message kinds (generic, every game):**

| Kind | Emitted when | Payload |
|---|---|---|
| `debug` | A debug message, when the member's debug setting is on | `text`, `source` |
| `info` | An informational message | `text` |
| `ok` | A confirmed success message | `text` |
| `warning` | A non-fatal problem the member should see | `code`, `text` |
| `error` | An action is refused, when the refusal is worth showing unprompted | `code`, `text` |
| `fragment` | A bottom-bar fragment's value changed (section 5a) | `name`, `value`, `level` |

**Game kinds** (per game, in Part B): round progress such as a card dealt or a hand settled.
A game kind may not reuse a message kind's name.

- Message kinds (`debug`, `info`, `ok`, `warning`, `error`) match the echo levels, so a
  message's level means the same on the echo path and the event path. `warn` is not used;
  `warning` is the only spelling.
- `debug` events are emitted only when the member's debug setting is on. The queue is quiet
  by default. Each UI filters on its own debug setting.
- Refusals are the `error` message kind plus the result `code` (section 4). The code is never
  duplicated in a second vocabulary.
- Events are ordered per table. A UI that drains the queue sees them in the order they
  happened.
- A game kind's payload is fixed by its Part B table, the same way a method's `data` is.
- Logging (`logging`) is the file log only. The event queue is the UI channel; a GUI receives
  debug and info text through it, not through the log.

### 5a. Bottom bar as events

The bottom bar is built from named fragments (`register_bottombar_fragment`). A fragment's
value is game or member state. When that value changes, the game emits a `fragment` event, so
a GUI and the TUI show the same values.

- `name` is the fragment's registered name (for example `balance`, `table`, `moniker`).
- `value` is the fragment's current value as data, not formatted text.
- `level` is the echo level the fragment uses, so a UI can colour it the same way as a message.
- A fragment event is emitted on change only, not on every redraw.
- The TUI renders the bar from the same values. Its drawing is a UI concern and is not part
  of this seam.
- **Open question:** the queue's thread model. How the TUI's event loop and the bottom bar
  share output today is not settled. The queue will be drained by each UI on its own loop
  (Tk and Qt run their own loops), but the exact drain point for the TUI is to be decided
  when the TUI adapter is written.

## 6. Results per method

Implemented in `bbsengine6.seam.results`: `ActionResult` (frozen, with `data` as a read-only
view), `success(data)`, and `refusal(code, message, data)`. `refusal` rejects an unknown code and
rejects `ok`.

Every game method returns `ActionResult`. Each method's `data` payload is fixed by that game's
Part B table. A method that has no payload returns an empty `data`.

## 7. Input

A UI sends a typed request to the game. The game never prompts. Each game's requests are listed
in its Part B section. The generic rule: a request names the table, the member, and the
game-specific arguments, and nothing else.

Prompts, menus, and validation messages belong to the UI.

## 8. Compatibility

- **The API wire shape does not change in the first step of a migration.** `api/handler.py`
  maps each `ActionResult` back to the dict the client receives today.
- The mapping lives in one function per game in `api/handler.py`, so it is removed when clients
  move to `ActionResult` directly.
- A UI (`commands/`, `client/`) keeps printing the same text. Its adapter prints the events it
  used to print.

## 9. Package and file layout

- The framework types live in bbsengine6: `ActionResult` (section 3), `Event` and the queue
  (section 5), and the generic code set (section 4). A consuming application imports them and
  does not redefine them.
- Each consuming application keeps its game services and its wire mapping in its own package.
  Its services return `ActionResult`, and its API layer maps results back to the wire dict
  (section 8).
- A consuming application that adopts the seam updates its own layout document in the same
  change, so the seam is listed where its code lives.

## 10. Verification

Generic checks, for every migration:

- The game's existing tests run before and after each method is migrated. They must pass
  unchanged, except where a test asserts a refusal `message` that is deliberately kept.
- Tests for the framework types: codes are in the enum; the queue preserves per-table order;
  `ActionResult` is immutable; message kinds are only `debug`, `info`, `ok`, `warning`, `error`;
  `debug` events are not queued when debug is off.
- A migration test per method: the result's `ok`, `code`, and `data` match the Part B table, and
  the API's wire dict is unchanged.

