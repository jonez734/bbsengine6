"""Tests for bbsengine6.io.terminfo: the pure-Python terminfo reader (standard capabilities)."""

import re
import shutil
import struct
import subprocess

import pytest

from bbsengine6.io import terminfo as ti


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    monkeypatch.delenv("TERMINFO", raising=False)
    monkeypatch.delenv("TERMINFO_DIRS", raising=False)
    ti.clear_cache()
    yield
    ti.clear_cache()


def _unescape(s):
    s = (
        s.replace("\\E", "\x1b")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\b", "\b")
        .replace("\\f", "\f")
        .replace("\\s", " ")
    )
    s = re.sub(r"\^([@-_?])", lambda m: chr(ord(m.group(1)) ^ 0x40) if m.group(1) != "?" else "\x7f", s)
    s = re.sub(r"\\(\d{3})", lambda m: chr(int(m.group(1), 8)), s)
    return s


def _infocmp_standard(name):
    """Parse ``infocmp -1x`` output into {capname: value} for standard capabilities."""
    out = subprocess.run(["infocmp", "-1x", name], capture_output=True, text=True).stdout
    ref = {}
    for line in out.splitlines()[1:]:
        line = line.strip().rstrip(",")
        if not line or line.startswith("#") or "|" in line:
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            ref[k] = _unescape(v)
        elif "#" in line:
            k, v = line.split("#", 1)
            ref[k] = int(v, 0)
        else:
            ref[line] = True
    return ref


needs_infocmp = pytest.mark.skipif(shutil.which("infocmp") is None, reason="infocmp not installed")


def _has_system_xterm():
    return ti.find("xterm") is not None


needs_xterm = pytest.mark.skipif(not _has_system_xterm(), reason="no xterm terminfo entry")


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


@needs_xterm
def test_xterm_found_and_loads():
    info = ti.load("xterm")
    assert info.name == "xterm"
    assert info.path.is_file()
    assert info.get("cup")


@needs_xterm
def test_has_entry_true_for_known_name():
    assert ti.has_entry("xterm") is True


def test_unknown_name_returns_none_and_false():
    assert ti.find("no-such-terminal-xyzzy") is None
    assert ti.has_entry("no-such-terminal-xyzzy") is False


def test_unknown_name_load_raises():
    with pytest.raises(ti.TerminfoError):
        ti.load("no-such-terminal-xyzzy")


@pytest.mark.parametrize("bad", ["", ".hidden", "a/b", "../etc/passwd", "x\x00y"])
def test_invalid_names_rejected(bad):
    assert ti.find(bad) is None
    assert ti.has_entry(bad) is False


def test_cache_returns_same_result_without_rereading(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    entry = tmp_path / "c" / "cachetest"
    entry.parent.mkdir()
    entry.write_bytes(_minimal_entry())
    assert ti.has_entry("cachetest") is True
    entry.unlink()  # file gone, but the cached answer must still be used
    assert ti.has_entry("cachetest") is True
    ti.clear_cache()
    assert ti.has_entry("cachetest") is False


# ---------------------------------------------------------------------------
# Search order
# ---------------------------------------------------------------------------


def _minimal_entry(*, bools=(), nums=(), strs=()):
    """Build a legacy-format entry with the given (index, value) pairs."""
    names = b"hand|hand test terminal\x00"
    boolvals = bytearray(len(ti.BOOL_CAPS))
    for i, v in bools:
        boolvals[i] = 1
    numvals = [-1] * len(ti.NUM_CAPS)
    for i, v in nums:
        numvals[i] = v
    table = bytearray()
    stroffs = [-1] * len(ti.STR_CAPS)
    for i, v in strs:
        stroffs[i] = len(table)
        table += v.encode("latin-1") + b"\x00"
    body = bytearray(names) + bytes(boolvals)
    if len(body) % 2:
        body += b"\x00"
    body += struct.pack(f"<{len(numvals)}h", *numvals)
    body += struct.pack(f"<{len(stroffs)}h", *stroffs)
    body += bytes(table)
    header = struct.pack(
        "<6h", 0o432, len(names), len(boolvals), len(numvals), len(stroffs), len(table)
    )
    return header + bytes(body)


def test_terminfo_env_is_searched_first(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    entry = tmp_path / "h" / "handtest"
    entry.parent.mkdir()
    entry.write_bytes(_minimal_entry(nums=[(0, 132)], strs=[(10, "\x1b[H")]))
    info = ti.load("handtest")
    assert info.nums["cols"] == 132
    assert info.get("cup") == "\x1b[H"
    assert info.path == entry


def test_hex_directory_layout_is_found(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    d = tmp_path / format(ord("h"), "x")
    d.mkdir()
    (d / "hexlayout").write_bytes(_minimal_entry())
    assert ti.has_entry("hexlayout") is True


def test_terminfo_dirs_empty_entry_means_system_dirs(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO_DIRS", f"{tmp_path}:")
    dirs = ti._search_dirs()
    assert str(tmp_path) in dirs
    assert "/usr/share/terminfo" in dirs


def test_terminfo_dirs_without_empty_entry_skips_system(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO_DIRS", str(tmp_path))
    dirs = ti._search_dirs()
    assert str(tmp_path) in dirs
    assert "/usr/share/terminfo" not in dirs


# ---------------------------------------------------------------------------
# Parsing errors
# ---------------------------------------------------------------------------


def test_bad_magic_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    d = tmp_path / "b"
    d.mkdir()
    (d / "badmagic").write_bytes(b"\x00\x00" + b"\x00" * 40)
    with pytest.raises(ti.TerminfoError, match="bad magic"):
        ti.load("badmagic")


def test_truncated_file_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    d = tmp_path / "t"
    d.mkdir()
    (d / "trunc").write_bytes(b"\x1a\x01")
    with pytest.raises(ti.TerminfoError):
        ti.load("trunc")


def test_string_offset_out_of_table_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMINFO", str(tmp_path))
    data = bytearray(_minimal_entry(strs=[(10, "x")]))
    # Point the first string offset (cup at index 10) past the table.
    names_len = len(b"hand|hand test terminal\x00")
    off = 12 + names_len + len(ti.BOOL_CAPS)
    if off % 2:
        off += 1
    off += len(ti.NUM_CAPS) * 2 + 10 * 2
    struct.pack_into("<h", data, off, 500)
    d = tmp_path / "h"
    d.mkdir()
    (d / "badoff").write_bytes(bytes(data))
    with pytest.raises(ti.TerminfoError):
        ti.load("badoff")


# ---------------------------------------------------------------------------
# Cross-check against the system database
# ---------------------------------------------------------------------------


@needs_xterm
@needs_infocmp
@pytest.mark.parametrize("name", ["xterm", "vt100", "linux", "screen"])
def test_standard_capabilities_match_infocmp(name):
    if ti.find(name) is None:
        pytest.skip(f"no {name} entry")
    info = ti.load(name)
    mine = {**info.bools, **info.nums, **info.strs}
    ref = _infocmp_standard(name)
    common = [k for k in ref if k in mine]
    assert common, "no overlap with infocmp output"
    mismatch = [k for k in common if mine[k] != ref[k]]
    assert mismatch == [], f"mismatched capabilities: {mismatch[:5]}"


@needs_xterm
def test_known_values_for_xterm():
    info = ti.load("xterm")
    assert info.nums["cols"] == 80
    assert info.bools["am"] is True
    assert info.get("cup") == "\x1b[%i%p1%d;%p2%dH"
    assert info.get("bold") == "\x1b[1m"


def test_get_returns_none_for_missing():
    info = ti.Terminfo(name="x", path=ti.Path("x"))
    assert info.get("cup") is None


def test_capability_tables_have_expected_shape():
    assert len(ti.BOOL_CAPS) == len(set(c for _, c in ti.BOOL_CAPS))
    assert len(ti.NUM_CAPS) == len(set(c for _, c in ti.NUM_CAPS))
    assert len(ti.STR_CAPS) == len(set(c for _, c in ti.STR_CAPS))
    assert ("columns", "cols") in ti.NUM_CAPS
    assert ("cursor_address", "cup") in ti.STR_CAPS
