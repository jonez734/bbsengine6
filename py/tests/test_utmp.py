"""utmp: Linux record layout, host/IPv6 parsing, and current_origin on synthetic and live files."""

import os
import struct
import sys
import time

import pytest

from bbsengine6 import utmp

LINUX = utmp.LAYOUTS["linux"]


def _linux_record(*, typ=7, pid=1234, line="pts/0", user="jam", host="", addr=(0, 0, 0, 0), sec=None):
    """One glibc utmp record, packed with the verified layout (384 bytes)."""
    sec = int(time.time()) if sec is None else sec
    return struct.pack(
        LINUX.fmt,
        typ, pid,
        line.encode().ljust(32, b"\x00"),
        b"ts/0",
        user.encode().ljust(32, b"\x00"),
        host.encode().ljust(256, b"\x00"),
        0, 0, 0, sec, 0,
        *addr,
        b"\x00" * 20,
    )


def _write(tmp_path, *records, layout=LINUX):
    path = tmp_path / "utmp"
    path.write_bytes(b"".join(records))
    return str(path)


# --- layout -----------------------------------------------------------------

def test_linux_record_size_matches_the_compiled_probe():
    assert LINUX.record_size == 384
    assert struct.calcsize(LINUX.fmt) == 384


def test_linux_user_process_code_is_seven():
    assert LINUX.user_process == 7


def test_freebsd_layout_size_is_from_its_header_fields():
    fb = utmp.LAYOUTS["freebsd"]
    assert fb.record_size == struct.calcsize(fb.fmt)
    assert len(fb.fields) == len(struct.unpack(fb.fmt, b"\x00" * fb.record_size))
    assert fb.user_process == 4


def test_layout_for_platform_selects_by_platform_name():
    assert utmp.layout_for_platform("linux") is LINUX
    assert utmp.layout_for_platform("freebsd") is utmp.LAYOUTS["freebsd"]
    assert utmp.layout_for_platform("win32") is None
    assert utmp.layout_for_platform("darwin") is None


# --- host parsing (IPv4 and IPv6) -------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("192.0.2.10", "192.0.2.10"),
    ("2001:db8::1", "2001:db8::1"),
    ("2001:0db8:0000:0000:0000:0000:0000:0001", "2001:db8::1"),
    ("::1", "::1"),
    ("::ffff:198.51.100.7", "198.51.100.7"),  # IPv4-mapped, reduced to IPv4
    ("fe80::1%eth0", "fe80::1%eth0"),  # ipaddress keeps the zone id; it is a valid IPv6 text
])
def test_parse_host_addresses(text, expected):
    address, unparsed = utmp.parse_host(text)
    assert address == expected and unparsed is False


@pytest.mark.parametrize("text", ["login screen", "tty2", "falcon.example.net", "999.1.1.1"])
def test_parse_host_names_are_kept_as_unparsed(text):
    address, unparsed = utmp.parse_host(text)
    assert address is None and unparsed is True


def test_parse_host_empty_is_neither_address_nor_unparsed():
    assert utmp.parse_host("") == (None, False)


# --- reading records ----------------------------------------------------------

def test_read_utmp_decodes_fields(tmp_path):
    path = _write(tmp_path, _linux_record(user="jam", line="pts/0", host="35.148.234.214", sec=1000))
    (rec,) = utmp.read_utmp(path, layout=LINUX)
    assert (rec.type, rec.pid, rec.line, rec.user) == (7, 1234, "pts/0", "jam")
    assert rec.host == "35.148.234.214" and rec.address == "35.148.234.214"
    assert rec.time == 1000.0 and rec.unparsed is False


def test_read_utmp_ipv6_host_and_binary_address(tmp_path):
    raw = (0x20010DB8, 0, 0, 1)
    path = _write(tmp_path, _linux_record(host="2001:db8::1", addr=raw))
    (rec,) = utmp.read_utmp(path, layout=LINUX)
    assert rec.address == "2001:db8::1"
    assert rec.raw_addr == struct.pack("<4i", *raw)


def test_read_utmp_rejects_a_file_that_is_not_whole_records(tmp_path):
    path = tmp_path / "utmp"
    path.write_bytes(b"\x00" * 100)
    with pytest.raises(ValueError):
        utmp.read_utmp(str(path), layout=LINUX)


def test_read_utmp_empty_file_is_no_records(tmp_path):
    path = tmp_path / "utmp"
    path.write_bytes(b"")
    assert utmp.read_utmp(str(path), layout=LINUX) == []


# --- current_origin ------------------------------------------------------------

def test_origin_is_the_live_record_for_the_tty(tmp_path):
    path = _write(tmp_path, _linux_record(line="pts/0", host="203.0.113.9", sec=100))
    assert utmp.current_origin("/dev/pts/0", path=path, layout=LINUX) == "203.0.113.9"


def test_origin_accepts_a_tty_name_without_dev(tmp_path):
    path = _write(tmp_path, _linux_record(line="pts/3", host="203.0.113.9"))
    assert utmp.current_origin("pts/3", path=path, layout=LINUX) == "203.0.113.9"


def test_origin_ignores_dead_and_other_ttys(tmp_path):
    path = _write(
        tmp_path,
        _linux_record(typ=8, line="pts/0", host="198.51.100.1"),   # DEAD_PROCESS
        _linux_record(line="pts/1", host="198.51.100.2"),          # other tty
    )
    assert utmp.current_origin("/dev/pts/0", path=path, layout=LINUX) is None


def test_origin_newest_record_wins(tmp_path):
    path = _write(
        tmp_path,
        _linux_record(line="pts/0", host="198.51.100.1", sec=100),
        _linux_record(line="pts/0", host="2001:db8::7", sec=200),
    )
    assert utmp.current_origin("/dev/pts/0", path=path, layout=LINUX) == "2001:db8::7"


def test_origin_returns_text_for_a_name_host(tmp_path):
    path = _write(tmp_path, _linux_record(line="tty2", host="tty2"))
    assert utmp.current_origin("/dev/tty2", path=path, layout=LINUX) == "tty2"


def test_origin_none_for_a_record_with_no_host(tmp_path):
    path = _write(tmp_path, _linux_record(line="pts/0", host=""))
    assert utmp.current_origin("/dev/pts/0", path=path, layout=LINUX) is None


def test_origin_none_when_file_missing(tmp_path):
    assert utmp.current_origin("/dev/pts/0", path=str(tmp_path / "nope"), layout=LINUX) is None


def test_origin_none_on_unsupported_platform(monkeypatch):
    monkeypatch.setattr(utmp.sys, "platform", "win32")
    assert utmp.current_origin("/dev/pts/0") is None


@pytest.mark.skipif(not os.path.exists("/run/utmp") or not sys.platform.startswith("linux"),
                    reason="needs a Linux host with /run/utmp")
def test_live_utmp_parses_every_record():
    records = utmp.read_utmp(layout=LINUX)
    assert all(r.type in range(0, 10) for r in records)


def test_current_tty_and_origin_come_from_one_record(tmp_path):
    path = _write(
        tmp_path,
        _linux_record(line="pts/2", host="::1", sec=100),
        _linux_record(line="seat0", host="login screen", sec=50),
    )
    assert utmp.current_tty("/dev/pts/2", path=path, layout=LINUX) == "pts/2"
    assert utmp.current_origin("/dev/pts/2", path=path, layout=LINUX) == "::1"


def test_current_tty_none_for_dead_or_missing(tmp_path):
    path = _write(tmp_path, _linux_record(typ=8, line="pts/9", host="198.51.100.1"))
    assert utmp.current_tty("/dev/pts/9", path=path, layout=LINUX) is None
    assert utmp.current_tty("/dev/pts/8", path=path, layout=LINUX) is None
