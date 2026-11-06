# utmp origin lookup: platforms not yet verified

Status: built and in use on Linux. Linux (glibc) is verified on this host. FreeBSD is
header-derived and not run. OpenBSD, NetBSD, and macOS are not added; they fall back to the SSH
environment. The unverified platforms are deferred: no access to those systems.

Code: `py/src/bbsengine6/utmp.py` (layouts, `read_utmp`, `_live_record`, `current_origin`,
`current_tty`) and `py/src/bbsengine6/util.py` (`getremoteaddr`, `remoteaddr_source`,
`current_account`). The session stores `remoteaddr`, `remoteaddr_source`, and `tty`
(`engine.__session`, `session/lib.py` `buildsession`).

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

## Linux: verified

- [x] `struct utmp` is 384 bytes; offsets confirmed with a compiled probe against the glibc header.
- [x] The live `/run/utmp` parses; the `USER_PROCESS` records match `who`.
- [x] A local SSH login (`pts/2`, host `::1`) is read back: `current_origin()` returns `::1` and
      `current_tty()` returns `pts/2`, from the same record. Accepted as the verification in place
      of a remote test (no second machine). The IPv4 remote path is covered by unit tests only.

## Install and permissions (current method)

- [x] zoid6: the utmp group is granted by the systemd drop-in
      `/etc/systemd/system/zoid6.service.d/utmp.conf` (`SupplementaryGroups=utmp`), installed with
      `make -C zoid6/src install-dropin`. The process has group 22. `usermod` is not needed.
- [x] bed: the same drop-in pattern, named after the instance unit (install guide, section 2).
- [ ] Optional: remove the earlier account membership, `sudo gpasswd -d zoid6 utmp`. Test first:
      remove, restart, and confirm the daemon still lists group 22 in `/proc/<pid>/status`.
- [ ] Run the session migration on each live database (adds `tty`, refreshes `engine.session`):
      `psql -X -d <db> -f bbsengine6/py/src/bbsengine6/sql/migrate_session_remoteaddr.sql` as the
      table owner (`jam`). Done on neither `zoid6test` nor `zoid6` yet.

## Decisions recorded

- Mismatch between utmp and the SSH environment: keep utmp, log a warning.
- Address text is kept as sshd wrote it when it is not an IP (for example a hostname), and is
  marked unparsed.
- Scope: current terminal only. No wtmp history.
- The session records the tty as utmp names it (`pts/N`, `seat0`, `ttyN`), from the same record as the
  address.
