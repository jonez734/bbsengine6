"""Read the login accounting database (utmp) to find where a terminal's login came from.

``sshd`` writes the client address into the ``ut_host`` field of the login's utmp record. That
address is the member's, which the server cannot see on its own socket when bed or zoid6 listens
on localhost. This module reads the record for the current terminal.

Layouts are per platform, keyed by ``sys.platform``. Each one is taken from that platform's own
header, not guessed:

- ``linux``: glibc ``struct utmp`` (``/usr/include/bits/utmp.h``), 384-byte records, verified
  with a compiled probe on this machine.
- ``freebsd``: ``struct utmpx`` (``include/utmpx.h`` in the FreeBSD source). The record size is
  computed from the header, not verified on a FreeBSD host yet (see handbook/todo/utmp-origin.md).

Any other platform returns no origin, and callers fall back to the SSH environment.

Failures never raise into callers: a missing file, a permission error, or an unsupported platform
all return ``None``. A record whose host is not a valid address is kept as text and marked
``unparsed`` rather than dropped.
"""

from __future__ import annotations

import ipaddress
import os
import struct
import sys
from dataclasses import dataclass, field
from typing import Iterator, Optional

__all__ = [
    "UtmpLayout",
    "UtmpRecord",
    "LAYOUTS",
    "layout_for_platform",
    "read_utmp",
    "current_origin",
    "current_tty",
    "parse_host",
]

USER_PROCESS_LINUX = 7
USER_PROCESS_BSD = 4


@dataclass(frozen=True)
class UtmpLayout:
    """Byte layout of one platform's utmp record."""

    name: str
    path: str
    record_size: int
    fmt: str  # struct format; fields are unpacked in the order given by UtmpRecord
    user_process: int
    fields: tuple  # (type, pid, line, user, host, time_sec, time_usec, addr_bytes)


# Linux glibc struct utmp, 32-bit time fields (the 64-bit build keeps the same size, see
# __WORDSIZE_TIME64_COMPAT32 in bits/utmp.h). Offsets verified with offsetof() on this machine:
#   ut_type 0 (2) + pad 2, ut_pid 4 (4), ut_line 8 (32), ut_id 40 (4), ut_user 44 (32),
#   ut_host 76 (256), ut_exit 332 (4), ut_session 336 (4), ut_tv 340 (sec 4 + usec 4),
#   ut_addr_v6 348 (16), reserved 364 (20). Total 384.
# Unpacked as: type, pid, line, id, user, host, exit_term, exit_code, session, sec, usec,
# addr (4 x int32), and the reserved bytes.
_LINUX_FMT = "<h2xi32s4s32s256shhiIi4i20s"
_LINUX = UtmpLayout(
    name="linux",
    path="/run/utmp",
    record_size=384,
    fmt=_LINUX_FMT,
    user_process=USER_PROCESS_LINUX,
    fields=("type", "pid", "line", "id", "user", "host", "exit_term", "exit_code",
            "session", "time_sec", "time_usec", "addr", "reserved"),
)

# FreeBSD struct utmpx (include/utmpx.h). Field order and widths from the header:
#   short ut_type; struct timeval ut_tv; char ut_id[8]; pid_t ut_pid; char ut_user[32];
#   char ut_line[16]; char ut_host[128]; char __ut_spare[64].
# The timeval is 64-bit seconds and microseconds on current FreeBSD (time_t is 64-bit).
# The record size and padding are computed by struct.calcsize() below, not written by hand.
# Field order as in the header; the 2-byte pad aligns the 8-byte timeval, and time_t is 64-bit.
_FREEBSD_FMT = "<h6xqq8si32s16s128s64s"
_FREEBSD = UtmpLayout(
    name="freebsd",
    path="/var/run/utmpx",
    record_size=struct.calcsize(_FREEBSD_FMT),
    fmt=_FREEBSD_FMT,
    user_process=USER_PROCESS_BSD,
    fields=("type", "time_sec", "time_usec", "id", "pid", "user", "line", "host", "spare"),
)

LAYOUTS: dict[str, UtmpLayout] = {"linux": _LINUX, "freebsd": _FREEBSD}


def layout_for_platform(platform: Optional[str] = None) -> Optional[UtmpLayout]:
    """The utmp layout for ``platform`` (default: this interpreter's ``sys.platform``), or None."""
    return LAYOUTS.get(platform or sys.platform)


@dataclass
class UtmpRecord:
    type: int
    pid: int
    line: str
    user: str
    host: str
    time: float
    address: Optional[str] = None  # parsed IP text, when the host is an address
    unparsed: bool = False  # True when host is not a valid IP address (kept as text)
    raw_addr: bytes = field(default=b"", repr=False)


def _text(raw: bytes) -> str:
    """A NUL-terminated C string field, decoded as UTF-8 with replacement."""
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def parse_host(text: str) -> tuple[Optional[str], bool]:
    """Return ``(address, unparsed)`` for a utmp host string.

    ``address`` is the canonical text of an IPv4 or IPv6 address, including an IPv4-mapped IPv6
    address (``::ffff:1.2.3.4``) reduced to its IPv4 form. ``unparsed`` is True when the text is
    not an address (a hostname, or empty). A zone id (``fe80::1%eth0``) is kept as part of the
    text, because ``ipaddress`` accepts it. Bracketed forms are not addresses and are unparsed.
    """
    text = text.strip()
    if not text:
        return None, False
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return None, True
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return str(addr.ipv4_mapped), False
    return str(addr), False


def _decode(layout: UtmpLayout, fields: tuple) -> UtmpRecord:
    values = dict(zip(layout.fields, fields))
    host = _text(values["host"])
    address, unparsed = parse_host(host)
    raw_addr = b""
    if "addr" in values:
        raw_addr = struct.pack("<4i", *values["addr"])
    return UtmpRecord(
        type=int(values["type"]),
        pid=int(values["pid"]),
        line=_text(values["line"]),
        user=_text(values["user"]),
        host=host,
        time=float(values["time_sec"]) + float(values["time_usec"]) / 1_000_000,
        address=address,
        unparsed=unparsed,
        raw_addr=raw_addr,
    )


def read_utmp(path: Optional[str] = None, *, layout: Optional[UtmpLayout] = None) -> list[UtmpRecord]:
    """Read every record in a utmp file. Raises OSError; returns [] for an empty file.

    The file size must be a whole number of records for the layout. A file that is not is
    rejected with ``ValueError`` rather than read at a wrong offset.
    """
    layout = layout or layout_for_platform()
    if layout is None:
        raise ValueError(f"no utmp layout for platform {sys.platform!r}")
    with open(path or layout.path, "rb") as fh:
        data = fh.read()
    if len(data) % layout.record_size:
        raise ValueError(
            f"{path or layout.path}: {len(data)} bytes is not a multiple of "
            f"{layout.record_size}-byte {layout.name} records"
        )
    return [_decode(layout, fields) for fields in _iter_fields(layout, data)]


def _iter_fields(layout: UtmpLayout, data: bytes) -> Iterator[tuple]:
    for fields in struct.iter_unpack(layout.fmt, data):
        yield _normalise(layout, fields)


def _normalise(layout: UtmpLayout, fields: tuple) -> tuple:
    """Return the unpacked struct tuple as a tuple in the order of ``layout.fields``.

    The Linux format unpacks ``addr`` as a 4-tuple of ints; the FreeBSD format has no address
    field, so its address slot is empty (IPv6 is only read from the Linux layout).
    """
    if layout.name == "linux":
        (typ, pid, line, _id, user, host, exit_term, exit_code,
         session, sec, usec, a0, a1, a2, a3, reserved) = fields
        return (typ, pid, line, _id, user, host, exit_term, exit_code,
                session, sec, usec, (a0, a1, a2, a3), reserved)
    typ, sec, usec, ident, pid, user, line, host, spare = fields
    return (typ, pid, line, ident, user, host, 0, 0, 0, sec, usec, (), spare)


def _live_record(
    tty: Optional[str],
    *,
    path: Optional[str],
    layout: Optional[UtmpLayout],
) -> Optional[UtmpRecord]:
    """The newest live USER_PROCESS record for ``tty`` (default: this process's terminal), or None."""
    layout = layout or layout_for_platform()
    if layout is None:
        return None
    if tty is None:
        try:
            tty = os.ttyname(0)
        except OSError:
            return None
    line = tty[len("/dev/"):] if tty.startswith("/dev/") else tty
    try:
        records = read_utmp(path=path, layout=layout)
    except (OSError, ValueError):
        return None
    best: Optional[UtmpRecord] = None
    for rec in records:
        if rec.type != layout.user_process or rec.line != line:
            continue
        if best is None or rec.time >= best.time:
            best = rec
    return best


def current_tty(tty: Optional[str] = None, *, path: Optional[str] = None,
                layout: Optional[UtmpLayout] = None) -> Optional[str]:
    """The tty name of the live login, as utmp records it (for example ``pts/2``), or None.

    Returns the same record the address comes from, so the tty and the address always describe one
    login. None when no live record exists for the terminal.
    """
    rec = _live_record(tty, path=path, layout=layout)
    return rec.line if rec is not None else None


def current_origin(
    tty: Optional[str] = None,
    *,
    path: Optional[str] = None,
    layout: Optional[UtmpLayout] = None,
) -> Optional[str]:
    """The remote address recorded for the live login on ``tty``, or None.

    ``tty`` defaults to the terminal on standard input (``os.ttyname(0)``). The match is on the
    record's ``line`` field (for example ``pts/0``, the tty name without ``/dev/``), and only a
    ``USER_PROCESS`` record counts, so a stale or dead entry is ignored. The newest matching record
    wins. Returns None on any failure: no tty, unsupported platform, missing or unreadable file, or
    no address on the record. A non-address host (a name) is returned as text, as sshd wrote it.
    """
    rec = _live_record(tty, path=path, layout=layout)
    if rec is None or not rec.host:
        return None
    return rec.address if rec.address is not None else rec.host
