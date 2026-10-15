# BBS auth: Dovecot on merlin, Cyrus on falcon

This document covers the BBS auth backend integration with the IMAP
daemons on the two hosts. It is the operator-facing counterpart to
`bbsengine6/py/src/bbsengine6/auth/README.md` (which is the
developer-facing reference for the verifier and entry points).

## Topology

| Host  | IMAP daemon | Auth backend                  | Deploy target         |
|-------|-------------|-------------------------------|-----------------------|
| merlin | Dovecot     | `bbsengine6-auth-checkpassword` (Dovecot `passdb checkpassword`) + `bbsengine6-auth-pam` (Dovecot `auth-system.conf.ext` → `/etc/pam.d/dovecot` → `/etc/pam.d/bbsengine6`) | `$(ENGINEHOST) = merlin` |
| falcon | Cyrus       | `bbsengine6-auth-pam` (Cyrus `auxprop-pam` → `/etc/pam.d/imap` → `/etc/pam.d/bbsengine6`) + optional saslauthd + postoffice-authd | `$(CYRUSHOST) = falcon` |

Both hosts run the same `bbsengine6` Python package. The verifier
function is the same; the entry points wrap different protocols
(Dovecot checkpassword vs. `pam_exec.so`).

## Install

The bbsengine6 submodule's `Makefile` provides the deploy targets
(additions for this auth integration; the rest of the Makefile is
unchanged):

| Target | What it does |
|--------|--------------|
| `make build-auth-wheel` | Build the bbsengine6 wheel into `/tmp/bbsengine6-auth-$$/` |
| `make install-bbsengine6-auth-helper` | Push the wheel to merlin and falcon, create `/opt/bbsengine6-auth-venv/`, `pip install` the wheel, symlink the two entry points to `/usr/local/bin/` |
| `make install-pam-bbsengine6-on-merlin` | Land `/etc/pam.d/bbsengine6` on merlin (the file content is staged in the meta-repo at `etc-postoffice/pam.d-bbsengine6`) |
| `make install-bbsengine6-everything` | Umbrella that runs the three above in order |
| `make uninstall-bbsengine6-auth-helper` | Remove `/usr/local/bin/bbsengine6-auth-*` and `/opt/bbsengine6-auth-venv/` from both hosts |
| `make uninstall-pam-bbsengine6-on-merlin` | Remove `/etc/pam.d/bbsengine6` from merlin |

Override hosts on the command line:

```sh
make CYRUSHOST=staging-cyrus install-bbsengine6-auth-helper
```

## Configuration

The entry points read their DSN from the standard `bbsengine6.database`
DSN chain, which resolves from `BBSENGINE6_DB*` env vars:

| Env var | Default | Used by |
|---------|---------|---------|
| `BBSENGINE6_DBNAME` | (none — required) | verifier |
| `BBSENGINE6_DBHOST` | `localhost` | verifier |
| `BBSENGINE6_DBPORT` | `5432` | verifier |
| `BBSENGINE6_DBUSER` | (none — required for non-peer auth) | verifier |
| `BBSENGINE6_DBPASSWORD` | (none — peer auth via UNIX socket if unset) | verifier |
| `BBSENGINE6_AUTH_MAIL_HOME` | `/var/vmail/%d/%n` | `bbsengine6-auth-checkpassword` (Dovecot userdb line) |
| `BBSENGINE6_AUTH_MAIL_LOCATION` | `maildir:~/Maildir` | `bbsengine6-auth-checkpassword` (Dovecot userdb line) |
| `BBSENGINE6_AUTH_VMAIL_UID` | `vmail` | `bbsengine6-auth-checkpassword` |
| `BBSENGINE6_AUTH_VMAIL_GID` | `vmail` | `bbsengine6-auth-checkpassword` |
| `BBSENGINE6_AUTH_LOG` | `INFO` | both entry points (stderr; journald picks it up) |

The `BBSENGINE6_AUTH_*_MAIL_*` env vars match the existing
`zoidlan/merlin/jammy/dovecot/local.conf` values so the existing
ACL/quota/sieve setup keeps working without Dovecot-side changes.

## Schema dependency

The `bbsengine6.auth.verify` query consults
`engine.__member.accountexpires`. Apply
`sql/008_add_member_accountexpires.sql` to existing DBs before
deploying:

```sh
psql -d zoid6 -f /path/to/sql/008_add_member_accountexpires.sql
```

For fresh DBs the column is part of the canonical
`bbsengine6/py/src/bbsengine6/sql/member.sql` schema.

## Auth flow

For a `LOGIN alice <password>` from an IMAP client:

```
Dovecot
  → passdb checkpassword (auth-checkpassword.conf.ext)
  → /usr/local/bin/bbsengine6-auth-checkpassword
    → reads AUTH_USER + stdin (Dovecot checkpassword protocol)
    → bbsengine6.auth.verify.verify_member(alice, password)
      → per-user path: SELECT ... FROM engine.__member WHERE moniker='alice'
      → crypt.crypt(password, stored_hash) → compare
      → returns (ok, outcome)
    → exit 0 + userdb lines on success
```

For a `LOGIN alice@bbsengine.org <password>` (per-mailbox):

```
Cyrus
  → sasl_auxprop_plugin = pam
  → /etc/pam.d/imap
  → pam_exec.so expose_authtok /usr/local/bin/bbsengine6-auth-pam
    → reads PAM_USER + PAM_AUTHTOK
    → scrubs PAM_AUTHTOK from os.environ
    → bbsengine6.auth.verify.verify_member(alice@bbsengine.org, password)
      → per-mailbox path: SELECT ... FROM postoffice.mailbox_password ...
      → crypt.crypt → compare
      → returns (ok, outcome)
    → exit 0/1/2
```

## Test commands (operator smoke test)

On merlin:

```sh
# Python verifier in isolation
echo pw | bbsengine6-auth-checkpassword --test alice
# (Note: --test mode is not implemented in this entry point; the
# verifier is exercised via the checkpassword protocol instead.
# To smoke-test the verifier without going through Dovecot, set
# the BBSENGINE6_TEST_* env vars and call verify_member from a
# Python REPL on merlin.)

# Dovecot passdb
doveadm auth test alice <password>
# Expected: passdb: bbsengine6-auth-checkpassword auth: succeeded

# Dovecot full IMAP
openssl s_client -connect merlin.zoidtechnologies.com:993 <<< $'a1 LOGIN alice <password>\na2 LIST "" "*"\na3 LOGOUT'

# PAM helper directly
PAM_USER=alice PAM_AUTHTOK=<pw> /usr/local/bin/bbsengine6-auth-pam; echo $?
# Expected: 0 on success, 1 on wrong password, 2 on DB error

# Negative
doveadm auth test alice wrongpw
# Expected: failed
```

On falcon (Cyrus, default auxprop-pam):

```sh
# After the etc-postoffice install (Phase 5) lands
ssh falcon sudo systemctl restart cyrus-imapd
ssh falcon testsaslauthd -u alice -p <pw> -s imap
# Expected: 0: OK "Success."

# Full IMAP
openssl s_client -connect falcon.zoidtechnologies.com:993 <<< $'a1 LOGIN alice <password>\na2 LIST "" "*"\na3 LOGOUT'

# Per-mailbox path
openssl s_client -connect falcon.zoidtechnologies.com:993 <<< $'a1 LOGIN alice@bbsengine.org <mailbox-pw>\na2 LIST "" "*"\na3 LOGOUT'
```

## Rollback

```sh
# Remove from both hosts
make uninstall-bbsengine6-auth-helper
# Remove from merlin
make uninstall-pam-bbsengine6-on-merlin
# Restore the previous /etc/pam.d/dovecot content
ssh merlin 'sudo cp /etc/pam.d/dovecot.pkgdist.<timestamp> /etc/pam.d/dovecot'
# Disable the new Dovecot passdb
ssh merlin 'sudo sed -i /^!include\ auth-checkpassword.conf.ext/s/^/#/ /etc/dovecot/conf.d/10-auth.conf && sudo systemctl reload dovecot'
```

The Makefile's `uninstall-bbsengine6-auth-helper` is idempotent
(re-runnable). The PAM file is also idempotent in install but a
`make uninstall-pam-bbsengine6-on-merlin` removes it without backup;
operators should snapshot `/etc/pam.d/bbsengine6` before uninstalling
in production.

## Cross-references

- `bbsengine6/py/src/bbsengine6/auth/README.md` — the verifier,
  dispatch, and security model developer reference.
- `etc-postoffice/pam.d-bbsengine6` (meta-repo) — the staged PAM
  service file.
- `etc-postoffice/imapd.conf` (meta-repo, Phase 5) — Cyrus
  auxprop-pam default.
- `zoidlan/merlin/jammy/dovecot/conf.d/10-auth.conf` (Phase 6) —
  the Dovecot include that enables the new passdb.
- `src/mcfeely_authd/auth_verify.py` (Phase 7) — the saslauthd-path
  gate change to use `accountexpires`.
