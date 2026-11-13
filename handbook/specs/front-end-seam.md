# bbsengine6 — front-end seam specification (generic core)

> **Last updated:** 2026-11-11.
> **Status:** Part A is implemented in `py/src/bbsengine6/seam/`, with tests in
> `py/tests/test_seam_types.py` and `py/tests/test_seam_domain.py`. The consuming application
> (casino, zoidoffice) keeps its per-application sections in its own handbook.
>
> **Terms:** the *seam* is this contract. The *domain* is the back end's logic for one application.
> A *front end* is any presentation (TUI, Tk, GTK, Qt, a mobile app). "Game" is not used here. "Table" is an
> application's noun, not a generic one: the generic unit is the *scope*.
> **Structure:** Part A is generic and lives here. Part B is per application and lives with the application.
> A new application adds a Part B section and does not change Part A.

## 1. Purpose

An application built on bbsengine6 may need more than one front end: a terminal front end today, and
Tk, GTK, or Qt later. The application and service code must not decide how a result is shown or how
input is read. This spec defines the seam between any application and any front end:

- Application code returns a typed **result** and emits typed **events**. It never calls `io.echo` or
  `io.input*`.
- A front end reads the player's input and sends typed **requests** to the application. It never reads application
  state except through results and events.
- Each front end consumes the same results and events on its own event loop.

## 2. Current state (verified, per application)

The current state is recorded per application in Part B. Across the applications today:

- Each application's service returns a plain `dict[str, Any]`. Refusals are
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
- `message` is for display. A front end may translate it by `code`.
- Every application method returns `ActionResult`. The method's own payload goes in `data`.

## 4. Result codes

**One owner.** The code vocabulary is defined once, as the `ErrorCode` enum in
`bbsengine6.seam.codes`. No other module defines a code. A consuming application imports the
enum and adds its application codes to its own copy of the vocabulary only by adding them here first.

**Migration status (casino):** the generic codes take their values from this enum. In casino,
`api/_auth.py` imports `CODE_NOT_AUTHENTICATED` and `CODE_FORBIDDEN` from it, `api/messages.py`
imports the shared members of `ErrorCode`, and `api/handler.py` uses the enum for its shared
responses (no literals remain). Casino's table, bet, and balance codes (`not_at_table`,
`table_not_found`, `invalid_bet`, `insufficient_funds`) are casino's own, defined in casino, with
their wire values unchanged.

**Generic codes** apply to every application and are the same for every application:

| Code | Meaning |
|---|---|
| `ok` | The action happened |
| `scope_not_found` | No scope (table, document, folder, or other unit the application defines) with that name |
| `not_in_scope` | The member is not allowed in the scope the request names |
| `invalid_action` | The action is not allowed in the current state |
| `forbidden` | Operation not permitted |
| `not_authenticated` | The request needs a logged-in member and there is none |
| `service_error` | Unexpected failure inside the service |

Money, wagers, and an application's own nouns are not generic. Codes such as `insufficient_funds`,
`invalid_bet`, or a table's `table_not_found` belong to the application that has them. They are
defined in the application's enum with their own wire values.

**Application codes** are added in each application's own enum, and listed in its own per-application
section (for casino's blackjack, see `casino/handbook/specs/front-end-seam-casino.md`, section 12). An
application code names a refusal, not a message. The refusal text stays in `message`.

An application may not invent a code that duplicates a generic one.

## 5. Events

Implemented in `bbsengine6.seam.events` (`Event`, `EventLog`, `Subscription`) and
`bbsengine6.seam.kinds` (`KindRegistry`). Each domain owns one registry, so a kind registered in one
domain is unknown to another. A domain rejects `warn`, and any kind that is neither a message kind,
`fragment`, nor registered in that domain.

An application emits events to a queue. The queue is the only channel for application progress. Events come in
two groups, and the seam treats them differently.

```python
@dataclass(frozen=True)
class Event:
    kind: str            # a message kind (below) or an application kind (Part B)
    scope: str           # the scope the event belongs to (see Request)
    moniker: str | None  # acting or affected member, when there is one
    payload: Mapping[str, Any]
```

**Message kinds (generic, every application):**

| Kind | Emitted when | Payload |
|---|---|---|
| `debug` | A debug message, when the member's debug setting is on | `text`, `source` |
| `info` | An informational message | `text` |
| `ok` | A confirmed success message | `text` |
| `warning` | A non-fatal problem the member should see | `code`, `text` |
| `error` | An action is refused, when the refusal is worth showing unprompted | `code`, `text` |
| `fragment` | A bottom-bar fragment's value changed (section 5a) | `name`, `value`, `level` |

**Application kinds** (per application, in Part B): round progress such as a card dealt or a hand settled.
An application kind may not reuse a message kind's name.

- Message kinds (`debug`, `info`, `ok`, `warning`, `error`) match the echo levels, so a
  message's level means the same on the echo path and the event path. `warn` is not used;
  `warning` is the only spelling.
- `debug` events are kept for a subscription only when that subscription has debug on. Debug is
  off by default and can be changed for a subscription at any time (`Domain.set_debug`).
- Refusals are the `error` message kind plus the result `code` (section 4). The code is never
  duplicated in a second vocabulary.
- Events are ordered in the order they were appended, so the events of any one scope keep their
  order for every subscriber.
- An application kind's payload is fixed by its Part B section, the same way a method's `data` is.
- Logging (`logging`) is the file log only. The event queue is the front-end channel; a GUI receives
  debug and info text through it, not through the log.

### 5a. Bottom bar as events

The bottom bar is built from named fragments (`register_bottombar_fragment`). A fragment's
value is application or member state. When that value changes, the application emits a `fragment` event, so
a GUI and the TUI show the same values.

- `name` is the fragment's registered name (for example `balance`, `scope`, `moniker`).
- `value` is the fragment's current value as data, not formatted text.
- `level` is the echo level the fragment uses, so a front end can colour it the same way as a message.
- A fragment event is emitted on change only, not on every redraw.
- The TUI renders the bar from the same values. Its drawing is a front-end concern and is not part
  of this seam.
- The bottom bar is a front-end concern: the front end decides where a fragment is drawn. The
  domain only emits the `fragment` event.

## 6. Results per method

Implemented in `bbsengine6.seam.results`: `ActionResult` (frozen, with `data` as a read-only
view), `success(data)`, and `refusal(code, message, data)`. `refusal` rejects an unknown code and
rejects `ok`.

Every application method returns `ActionResult`. Each method's `data` payload is fixed by that application's
Part B section. A method that has no payload returns an empty `data`.

## 7. Input

A front end sends a typed request to the domain with `Domain.request(req)`. The request is a
frozen dataclass that subclasses `bbsengine6.seam.requests.Request` and names the scope and the
member, plus its own fields. The domain dispatches on the request's type, and each type has exactly
one handler, registered with `Domain.on(RequestType, handler)`. A request with no handler returns
`invalid_action`. The call is synchronous: it returns the `ActionResult` directly. The domain never
prompts.

Prompts, menus, and validation messages belong to the front end.

## 7a. Subscriptions, lag, and expiry

- A front end calls `Domain.subscribe(debug=False)` to get a subscription id, and `Domain.read(id)`
  to take the events it has not read yet. Reading advances only that subscription's cursor.
- The log keeps the most recent `capacity` events (default 1000). A subscription that falls further behind
  gets one `lagged` event first, with `missed` (the count it lost), and then resumes from the oldest
  event still kept. The lag is also written to the log, as a warning.
- A subscription that has not been read for `idle_seconds` expires (default 300; `Domain.expire_idle`). Its cursor
  is released, so it no longer holds back anything, and a later `read` raises `KeyError`. Expiry is
  also written to the log, as a warning.
- Lag and expiry warnings go through `bbsengine6.util.logentry()` at `warning` level, with the
  logger name `logger_name` (default `bbsengine6.seam`), so an operator can filter them. The event
  log is not the file log: front ends read events, and operators read the log.

### 7a.1 Configuration

The three settings live in `bbsengine6.seam.config`:

| Setting | Default | Meaning |
|---|---|---|
| `capacity` | 1000 | Events kept per domain before a slow front end lags. Positive integer. |
| `idle_seconds` | 300 | Seconds a subscription may go unread before it expires. Positive number. |
| `logger_name` | `bbsengine6.seam` | Logger for lag and expiry warnings. Non-empty string. |

`config.configure(**settings)` sets any subset of them. It checks each value and rejects an unknown
key before anything changes. A domain or log built after the call uses the new values; one already
built keeps the values it was given. A consumer calls `configure` once at startup. Bed does this from
its config's `bbsengine6.seam` section, and zoid6's packaged `zoid6.json` carries that section.

## 7b. Thread model

- Any thread may call `emit`, `subscribe`, `read`, `set_debug`, `expire_idle`, and `request`.
- The log and the subscription table are lock-protected.
- The domain never calls a front end. There are no callbacks in version 1, so no domain code runs
  on a front end's thread. A front end drains by calling `read` on its own loop.
- A handler runs on the thread that called `request`. A handler must not block on a front end.

## 7c. Wire form

A front end on another runtime (a mobile client) uses the JSON form in `bbsengine6.seam.wire`. Only
JSON types appear: strings, numbers, booleans, null, lists, and objects.

- `ActionResult`: `{"ok": bool, "code": str, "message": str, "data": {...}}`.
- `Event`: `{"kind": str, "scope": str, "moniker": str | null, "payload": {...}}`.
- `Request`: `{"type": str, "fields": {...}}`, where `type` is the request class name. The receiving
  side maps the name to its class.
- The `lagged` event has `kind` `lagged` and `payload` `{"missed": int}`.

## 8. Compatibility

- **The API wire shape does not change in the first step of a migration.** `api/handler.py`
  maps each `ActionResult` back to the dict the client receives today.
- The mapping lives in one function per application in its API handler, so it is removed when clients
  move to `ActionResult` directly.
- A front end (`commands/`, `client/`) keeps printing the same text. Its adapter prints the events it
  used to print.

## 9. Package and file layout

- The framework types live in bbsengine6: `ActionResult` (section 3), `Event` and the queue
  (section 5), and the generic code set (section 4). A consuming application imports them and
  does not redefine them.
- Each consuming application keeps its services and its wire mapping in its own package.
  Its services return `ActionResult`, and its API layer maps results back to the wire dict
  (section 8).
- A consuming application that adopts the seam updates its own layout document in the same
  change, so the seam is listed where its code lives.

## 10. Verification

Generic checks, for every migration:

- The application's existing tests run before and after each method is migrated. They must pass
  unchanged, except where a test asserts a refusal `message` that is deliberately kept.
- Tests for the framework types (`test_seam_types.py`): codes are in the enum; `ActionResult` is
  immutable; message kinds are only `debug`, `info`, `ok`, `warning`, `error`; a kind may not reuse
  a message name.
- Tests for the domain (`test_seam_domain.py`): kinds are per domain; each subscriber sees every
  event; debug is per subscription; lag gives one marker and then the head; expiry releases the
  cursor; requests dispatch to one handler; the wire form round-trips; no seam module imports `io`.
- A migration test per method: the result's `ok`, `code`, and `data` match the Part B table, and
  the API's wire dict is unchanged.

