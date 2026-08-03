# TODO: GnuPG signing/encryption for `__notify` body (follow-up to TODO-notify.md)

> **STATUS (2026-07-22): SUPERSEDED / MOOT.** The notify→message.py
> migration is complete. The `bbsengine6/notify/` and
> `bbsengine6/message_delivery/` packages, the
> `engine.__notify*` tables, and the `engine.notify*` views were
> all deleted in Phase 7 of `TODO-message-migration.md`. Every
> item in this document refers to a `__notify` table, a
> `__notify_recipient` row, or a `message_delivery/lib.py`
> function that no longer exists.
>
> GPG signing/encryption is still a desirable feature, but the
> schema for it must be reworked against `bbsengine6.message`
> (`engine.__message`, `engine.__message_recipient`) and the
> `bbsengine6.member` GPG-key work in
> `bbsengine6/TODO.md` "GPG Key Support for Message Signing"
> (which itself is still pending). This file is preserved for
> the **decisions** captured below (privacy via encryption at
> rest, client-side crypto, single key per user, MIME-wrapped
> PGP payload, no HMAC for encrypted rows) but **no checklist
> item below is actionable** until the new schema is decided.

Work item: provide end-to-end privacy and integrity for `__notify`
message bodies using GnuPG-compatible keys. The same keypair used
to sign and/or encrypt `__notify` messages is also the user's email
key — one key per user, multiple uses.

This is a follow-up to `TODO-notify.md` (the audit work — `datedelivered`,
`deliverymethod`, FK change, `should_persist` removal). Land that
first, then plan and execute this work.

Decisions captured in plan (2026-07-06):

- [x] Privacy is delivered by encrypting the message body at rest
      and decrypting on the client. The DB **is** written — the
      body is stored as ciphertext. Skipping the DB is **not** the
      privacy mechanism.
- [x] Each user has a GnuPG keypair. The same keypair signs and/or
      encrypts email and `__notify` messages — single key per user.
- [x] Encryption is **client-side**. The server never sees the
      plaintext body. The TUI (or WWW) holds the private key
      transiently in memory; never on disk unencrypted.
- [x] Public key registration is **external** — the user uploads
      their public key via TUI command or WWW form. Stored in
      `engine.__member` (column TBD) or a dedicated key table.
- [x] `template` and `notification_type` stay plaintext (routing
      metadata). `rendered_message`, `template_vars`, and `data`
      are encrypted when encryption is requested.
- [x] The `__notify` table gets a new `encrypted_message bytea`
      column. `rendered_message text` is kept for plaintext rows.
      An `is_encrypted boolean` column marks which form is active
      for a given row.
- [x] Encrypted payload is **MIME** (PGP/MIME, RFC 3156). The
      ciphertext in `encrypted_message` is the MIME-wrapped
      PGP message, base64-encoded into bytea.
- [x] **No HMAC for encrypted rows** — the GPG signature already
      provides integrity. The existing `mac` column continues to
      be used for plaintext rows only.
- [x] Server pushes a "you have a new encrypted message"
      indicator to the live queue. The recipient fetches the
      ciphertext on demand (lazy fetch model, not live-stream).
- [x] Defense in depth: for encrypted rows, the GPG signature
      is verified on read, and the `is_encrypted` flag plus the
      existence of `encrypted_message` provides a secondary
      check.
- [x] TUI search is **disabled for encrypted message bodies** —
      the server has no plaintext to search. Metadata search
      (sender, date, urgency) still works.
- [x] TUI decrypts via a `gpg --decrypt` subprocess (or
      `python-gnupg` equivalent). The TUI process holds the
      private key in memory only, never on disk.
- [x] `send()` API evolves to accept `signed: bool = False` and
      `encrypted: bool = False`. The four combinations
      (neither, signed only, encrypted only, both) are all
      valid.
- [x] No BC concerns for the `__notify` table. Schema changes
      land directly. No migration script.

## Work items (high level — to be detailed when this TODO is activated)

### Schema

- [ ] Add `encrypted_message bytea` to `engine.__notify`.
- [ ] Add `is_encrypted boolean default false` to `engine.__notify`.
- [ ] Add `signature bytea` to `engine.__notify` (sender's
      GPG signature over the ciphertext, when `signed=True`).
- [ ] Add `sender_gpg_fingerprint text` to `engine.__notify`
      (or split into a separate `__notify_signature` table).
- [ ] Add `recipient_gpg_fingerprint text` to
      `engine.__notify_recipient` (or split into a separate
      table).
- [ ] Add `gpg_fingerprint text` to `engine.__member` (one key
      per user) or a dedicated `__member_gpg_key` table (multiple
      keys per user).
- [ ] Update `engine.notify` view to expose the new columns
      (excluding `encrypted_message` and `signature` from the
      view — clients fetch those via a dedicated encrypted-fetch
      endpoint or include them via a separate `engine.notify_encrypted`
      view).

### Server: key registration

- [ ] `member.register_gpg_key(fingerprint, armored_public_key)`
      — validate the armored key with `gpg --show-keys`, store
      the fingerprint and armored public key in `__member_gpg_key`.
- [ ] `member.unregister_gpg_key(fingerprint)` — remove a key
      from the user's registered keys.
- [ ] `member.list_gpg_keys()` — list the user's registered
      public keys.
- [ ] `member.get_gpg_key_for_user(moniker, fingerprint=None)` —
      fetch a public key for a given user. If multiple keys
      registered and no fingerprint specified, return the
      primary.
- [ ] `member.verify_gpg_key(fingerprint)` — re-validate a
      stored public key against the current keyring state.

### Server: send-side crypto

- [ ] Update `send()` signature to add `signed: bool = False`
      and `encrypted: bool = False` parameters.
- [ ] When `encrypted=True`:
  - [ ] Fetch the recipient's public key (via
        `member.get_gpg_key_for_user`).
  - [ ] Encrypt the body envelope (`rendered_message`,
        `template_vars`, `data`) using `python-gnupg.encrypt`.
  - [ ] Wrap the ciphertext in PGP/MIME (RFC 3156) format.
  - [ ] Store the MIME-wrapped ciphertext in `encrypted_message`.
  - [ ] Set `is_encrypted=true`. `rendered_message` stays NULL
        for encrypted rows.
  - [ ] No `mac` column write for encrypted rows.
- [ ] When `signed=True` (with or without encryption):
  - [ ] If `encrypted=False`, sign `rendered_message` with the
        sender's private key (the server temporarily holds the
        sender's private key for this operation, or the TUI
        pre-signs the message before calling `send()`).
  - [ ] If `encrypted=True`, sign the ciphertext with the
        sender's private key.
  - [ ] Store the detached signature in `signature`.
  - [ ] Record the sender's GPG fingerprint in
        `sender_gpg_fingerprint`.
- [ ] When both `signed=False` and `encrypted=False`:
  - [ ] Existing behavior. Plaintext `rendered_message`,
        `is_encrypted=false`, `mac` column populated as today.
- [ ] Update `get_notifications()` to return both plaintext and
      encrypted rows. For encrypted rows, exclude
      `encrypted_message` and `signature` from the regular
      SELECT; the client fetches them on demand via a new
      `fetch_encrypted(notify_id, recipient_moniker)` API.
- [ ] Update `mark_read()` / `mark_delivered()` — work
      identically for encrypted and plaintext rows. The
      `deliverymethod` field (from `TODO-notify.md` audit work)
      tracks the same way for both.

### Server: receive-side verification (defense in depth)

- [ ] On read of an encrypted row, verify the signature against
      the stored `sender_gpg_fingerprint`. If the fingerprint
      doesn't match the signature, raise a tamper error
      (analogous to the existing `NotificationTamperError`).
- [ ] On read of an encrypted row, verify the ciphertext is
      well-formed PGP/MIME (basic structural check, not full
      crypto verification).
- [ ] If signature verification fails, do not return the
      ciphertext to the client. Log a security event.

### TUI: key registration

- [ ] TUI command `key register` — paste an ASCII-armored
      public key, validate with `gpg --show-keys`, call
      `member.register_gpg_key`.
- [ ] TUI command `key list` — show the user's registered
      public keys with fingerprints and creation dates.
- [ ] TUI command `key remove <fingerprint>` — call
      `member.unregister_gpg_key`.
- [ ] TUI command `key import` — import a public key from the
      local GPG keyring (uses `gpg --export` with a chosen
      fingerprint, then register).
- [ ] TUI command `key show <moniker>` — display another user's
      registered public key (ASCII-armored).

### TUI: receive encrypted messages

- [ ] TUI command `mail encrypted` — list encrypted messages
      for the current user. Shows metadata only (sender, date,
      urgency, notification_type). Body is hidden until fetched.
- [ ] TUI command `mail fetch <notify_id>` — fetch the
      ciphertext for a specific encrypted message and shell out
      to `gpg --decrypt` to display the body. The TUI process
      holds the user's private key in memory for the duration
      of the decrypt operation, then clears it.
- [ ] TUI command `mail verify <notify_id>` — verify the
      signature on an encrypted message without decrypting the
      body. Reports the signer's fingerprint and validity.
- [ ] TUI command `mail send --encrypted --signed ...` — send
      a new message. The TUI collects the body, optionally
      signs and/or encrypts it client-side, then calls
      `send(signed=..., encrypted=...)` with the pre-processed
      payload.
- [ ] TUI: when displaying a message list, indicate
      encryption/signing status with a marker (e.g. `[E]`
      encrypted, `[S]` signed, `[ES]` both, `[ ]` neither).

### TUI: security hygiene

- [ ] Private key handling: TUI loads the private key into
      memory only when a decrypt operation is in progress.
      Clears the key from memory immediately after.
- [ ] Never write the private key to disk in the TUI's
      working directory.
- [ ] Never log the private key or any decrypted plaintext
      via `io.echo` or similar.
- [ ] When the TUI exits normally or crashes, ensure the
      in-memory key buffer is zeroed (best-effort — Python
      doesn't guarantee this, but the TUI should make a
      reasonable attempt).

### WWW frontend parity

- [ ] WWW form for key registration (paste ASCII-armored
      public key).
- [ ] WWW list view for encrypted messages (metadata only).
- [ ] WWW fetch-and-decrypt view. Browser-based decryption
      requires the user's private key in the browser (via
      OpenPGP.js or a server-side proxy that holds the key
      transiently). Decide between client-side JS crypto
      (strongest privacy, requires the user to upload the
      key to the browser session) and server-side proxy
      with a session-bound key (simpler UX, server sees
      plaintext briefly).

### Audit and security logging

- [ ] Log every key registration event (who registered what
      fingerprint when).
- [ ] Log every encryption event (sender, recipient,
      fingerprint, timestamp) — but **not** the plaintext
      body.
- [ ] Log every signature verification failure (security
      event).
- [ ] Feed into the existing `__notify_history` table or a
      new `__notify_audit` table. Decision: extend
      `__notify_history` (existing pattern) or add a new
      table (cleaner separation). Default: extend existing
      table for consistency.

### Threat model documentation

- [ ] Document when the TUI's private key is in memory,
      how it is cleared, and what the residual risks of a
      compromised TUI process are.
- [ ] Document the trust model: server is honest-but-curious
      (sees metadata, doesn't see body); TUI is trusted to
      handle the private key correctly; user is trusted to
      keep their private key secure.
- [ ] Document the key recovery story: if a user loses their
      private key, encrypted messages sent to them are
      unrecoverable. Escrow options (server-side wrapped
      copy of the private key) are out of scope and should
      be a separate decision.
- [ ] Document the key rotation story: when a user rotates
      their GPG key, encrypted messages sent to the old key
      remain encrypted to the old key. New messages use the
      new key.

## Out of scope

- Server-side key escrow.
- Keyserver integration (no automatic fetch from public
  keyservers — users register keys manually).
- Multi-device key sync (the BBS is the sync point — the
  key is registered once, available wherever the TUI
  runs).
- End-to-end encryption for messages that need server-side
  processing (search, filtering, anti-spam) — those features
  are plaintext-only.
- Replacing the existing HMAC for plaintext rows (the existing
  HMAC stays; encryption is additive).
- WWW browser-side GPG via WebCrypto / OpenPGP.js — design
  decision pending; the WWW frontend will likely use a
  server-side proxy that holds the key transiently, with
  documentation of the privacy trade-off.

## Relationship to `TODO-notify.md`

`TODO-notify.md` lands first. It establishes:

- The `datedelivered` / `deliverymethod` audit fields on
  `__notify_recipient` (work in this file builds on these).
- The `engine._append_delivery_method` helper.
- The FK `on delete set null` behavior (audit rows survive
  `expunge()`).
- The removal of `should_persist`.
- **Phase 7 of `TODO-notify.md`** — re-enabling the notify
  tables in `startup` so the production bootstrap stages
  install the notify schema. **This must land before the
  schema additions in this file become installable on a
  fresh database.** Without Phase 7, the new
  `engine.__member.gpg_fingerprint` and the new
  `engine.__notify` columns would not be installed during
  `stage_one` / `stage_zero`; the test conftest would still
  load them for tests, but a fresh production database would
  not have them.

This file assumes all of the above are in place. Schema
changes in this file are additive to `TODO-notify.md`'s
schema changes (new columns on `__notify`, new columns on
`__member`).

### Recommended execution order

1. **`TODO-notify.md` Phases 1-6** (audit work, `should_persist`
   removal, helper function).
2. **`TODO-notify.md` Phase 7** (re-enable notify tables in
   `startup`).
3. **`TODO-notify-encryption.md` Part 1** (schema additions
   for `__notify` and `__member`).
4. **`TODO-notify-encryption.md` Part 2** (server-side
   `send()` encryption and signing).
5. **`TODO-notify-encryption.md` Part 3** (TUI-side key
   registration and message decryption).
6. **`TODO-notify-encryption.md` Part 4** (WWW frontend
   parity).
7. **`TODO-notify-encryption.md` Part 5** (threat model
   documentation, audit logging, edge cases).

## Estimated scope

This is a multi-PR effort. Suggested breakdown:

- **PR 1 (this file, part 1):** Schema additions for
  `__notify` (encrypted_message, is_encrypted, signature,
  fingerprints) and `__member` (gpg_fingerprint). No behavior
  change yet — just schema and a stub for the `send()` API
  to accept the new parameters but ignore them.
- **PR 2 (this file, part 2):** Server-side `send()` encryption
  and signing. Server temporarily holds the sender's private
  key (this is a stopgap; the proper TUI-side encryption
  comes later). `get_notifications()` returns encrypted rows
  with placeholder ciphertext.
- **PR 3 (this file, part 3):** TUI-side key registration and
  message decryption. TUI holds the user's private key
  transiently. Remove the server-side stopgap from PR 2 —
  sender encryption moves entirely to the TUI.
- **PR 4 (this file, part 4):** WWW frontend parity. Browser
  crypto or server-side proxy.
- **PR 5 (this file, part 5):** Threat model documentation,
  audit logging, and the long-tail of edge cases (key
  rotation, lost keys, signature verification on read).

Each PR is independently shippable. The audit work in
`TODO-notify.md` should land before PR 1 of this file.
