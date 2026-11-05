# utmp origin lookup: platforms not yet verified

Status: built for Linux (verified) and FreeBSD (header-derived, not run). Other platforms return
no origin and fall back to the SSH environment.

Code: `py/src/bbsengine6/utmp.py` (layouts, `read_utmp`, `current_origin`) and
`py/src/bbsengine6/util.py` (`getremoteaddr`, `remoteaddr_source`, `current_account`).

## Verify on each platform (no access to these systems yet)

- [ ] FreeBSD: run the layout probe (a C program printing `sizeof` and `offsetof` for
      `struct utmpx`) and compare with `LAYOUTS["freebsd"]`. The record size (276 bytes) is
      derived from the header, not measured. Header used: FreeBSD `include/utmpx.h`.
- [ ] FreeBSD: confirm the utmpx file path (`/var/run/utmpx` in the layout) and that sshd writes
      the client address into `ut_host`.
- [ ] OpenBSD: check whether it uses `utmpx` or `utmp`, its record layout, and its file path.
      Not added to `LAYOUTS` yet.
- [ ] NetBSD: same as OpenBSD.
- [ ] macOS (darwin): check the `utmpx` layout and path. Not added to `LAYOUTS` yet. Apple's
      man page was unreachable when checked.
- [ ] Confirm `sys.platform` values for each (`freebsd`, `openbsd`, `netbsd`, `darwin`).

## Linux: verified on this machine

- [x] `struct utmp` is 384 bytes; offsets confirmed with a compiled probe against the glibc header.
- [x] The live `/run/utmp` parses; the `USER_PROCESS` records match `who`.
- [ ] A live SSH login record (`pts/N` with a client address) has not been read back yet, because
      the session in this check was local. Run `python3 -c "from bbsengine6 import utmp; print(utmp.current_origin())"`
      inside an SSH session to confirm.

## Install and permissions

- [x] `bed` install guide: `usermod -aG utmp <service-user>` (sudo), with restart note.
- [x] `zoid6` install guide: same step for the `zoid6` account.
- [ ] Run the `usermod` step on each host (`bed`'s service account and `zoid6`). Until then the
      origin lookup gets `PermissionError` and falls back to the SSH environment.
- [ ] Verify membership after restart: `id <account>` and `sudo -u <account> test -r /run/utmp`.

## Decisions recorded

- Mismatch between utmp and the SSH environment: keep utmp, log a warning.
- Address text is kept as sshd wrote it when it is not an IP (for example a hostname), and is
  marked unparsed.
- Scope: current terminal only. No wtmp history.
