# bbsengine6.auth → bbsengine6.bank Authorization Flow

This document describes how a websocket connection authenticates via
`bbsengine6.auth` and is then authorized to perform bank operations
via `bbsengine6.bank`.

## Overview

The auth and bank modules cooperate via a shared in-process
`SessionManager`. There is no per-message bearer token on bank
operations; the auth handler binds a session id to a moniker at
`auth login` time, and the bank handler reads that binding on every
request.

## Components

### `bbsengine6.auth` (`py/src/bbsengine6/auth/__init__.py`)

Pure authorization policy. Defines a single `access()` function that
returns `True`/`False` for the four domain verbs:

| op          | meaning                                            |
|-------------|----------------------------------------------------|
| `login`     | issue a fresh bearer token (moniker/password)      |
| `reconnect` | rebind an existing token to a new websocket        |
| `refresh`   | rotate the live session's token                    |
| `revoke`    | delete a token from the store                      |

The actual login (password verification, token signing, store write)
lives in `bed/api/auth.py` outside this repo. `bbsengine6.auth`
exposes the per-op policy decisions only.

### `bbsengine6.session.SessionManager` (`py/src/bbsengine6/session/lib.py`)

Process-local mapping:

```
session_id (int, monotonic) -> { "moniker": str, "is_sysop": bool }
```

Public methods:

- `alloc_session_id() -> int` — issued by the transport on connect.
- `register_session(session_id, moniker, is_sysop=False)` — called by
  the auth handler after a successful `login`/`reconnect`/`refresh`.
- `unregister_session(session_id)` — called by the transport on
  disconnect (see `net/transport.py:956`).
- `get_session(session_id) -> dict | None` — read-only lookup used by
  the bank handler.

### `bbsengine6.bank` (`py/src/bbsengine6/bank/__init__.py`)

Pure authorization policy for bank operations. Defines `access()`
with ops `balance`, `add`, `remove`, `history`, `pending`,
`transfer`, `approve`, `reject`, `list_all`. Reads
`message["claims"]` first (HMAC-verified bearer), falls back to
`session.moniker` / `session.is_sysop`.

### `bbsengine6.bank.api.handler` (`py/src/bbsengine6/bank/api/handler.py`)

The WebSocket dispatch entry point. Maps incoming wire message types
to bank ops via `OP_MAP`, then delegates the per-op authorization
decision to `bbsengine6.bank.access`. The session id is
`id(websocket)` — the same value the transport hands to
`SessionManager.alloc_session_id()`.

## End-to-end sequence

1. Client opens websocket to the transport.
2. Transport calls `SessionManager.alloc_session_id()` → integer.
3. Client sends `{"type": "auth", "op": "login", "moniker": "alice", "password": "..."}`.
4. `bed/api/auth.py` (consumer of `bbsengine6.auth.access`) verifies
   creds, asks `bbsengine6.auth.access(args, "login", session=None,
   message=msg)`, signs a token, calls
   `SessionManager.register_session(session_id, "alice", is_sysop)`.
5. Client sends `{"type": "bank_balance", "moniker": "alice"}`.
6. Transport dispatches to `BankServiceHandler.handle_message`.
7. Handler calls `_check_auth(args, "bank_balance", session_id,
   message, sessions)`.
8. `_check_auth` looks up `session_id` in the SessionManager, wraps
   the dict in `SessionState`, and calls
   `bank_access(args, "balance", session=..., message=...)`.
9. `bank_access` returns `True` (alice owns her own account), the
   handler proceeds with `bank_service.get_balance("alice")`.
10. On disconnect, transport calls
    `router.unregister_session(session_id)` → bank router removes
    the SessionManager entry.

## Wire-level mapping (bank)

| ws message type             | op       | required session state                          |
|-----------------------------|----------|-------------------------------------------------|
| `bank_balance`              | balance  | self moniker == target, or sysop                |
| `bank_add`                  | add      | self moniker == target, or sysop                |
| `bank_remove`               | remove   | self moniker == target, or sysop                |
| `bank_history`              | history  | self moniker == target, or sysop                |
| `bank_pending`              | pending  | self moniker == target (defaults to caller), or sysop |
| `bank_transfer_request`     | transfer | self moniker == `from`, or sysop                |
| `bank_transfer_approve`     | approve  | valid `transfer_id`, optional `responded_by` match |
| `bank_transfer_reject`      | reject   | valid `transfer_id`, optional `responded_by` match |
| `bank_list_all`             | list_all | sysop only                                      |

On denial the handler returns:

```json
{"type": "error", "code": "forbidden", "message": "not authorized"}
```

## Token-aware path (future)

When `bed/api/auth.py` verifies a bearer token for a request, it
stashes the decoded claims under `message["claims"]` before calling
`bank_access`. `bank_access` then prefers claim-derived
`moniker` / `is_sysop` over the in-memory session attributes
because the claims are HMAC-verified. The handler does not need to
decode the token itself — only the auth handler does.

## Failure modes

| Condition                                | Effect on bank handler                           |
|------------------------------------------|--------------------------------------------------|
| websocket never logged in                | `SessionManager.get_session` returns None → `bank_access(..., session=None)` returns False → `forbidden` |
| `auth login` succeeded but `register_session` not called | same as above |
| session expired and transport did not unregister | stale session may still resolve until explicit logout; refresh path is the safe way to rebind |
| token issued for `session_id=A` is presented to websocket `B` | `bbsengine6.auth.access("refresh")` denies; for bank ops, the in-memory session only reflects the current websocket, so a tampered session is invisible to `bank_access` |

## Files involved

- `py/src/bbsengine6/auth/__init__.py` — policy
- `py/src/bbsengine6/session/lib.py` — SessionManager
- `py/src/bbsengine6/bank/__init__.py` — bank policy
- `py/src/bbsengine6/bank/api/handler.py` — WS dispatch + `_check_auth`
- `py/src/bbsengine6/net/transport.py` — session_id lifecycle
- `py/tests/test_bank_access.py` — unit tests for `bank_access`
- `py/tests/test_auth_access.py` — unit tests for `auth.access`
