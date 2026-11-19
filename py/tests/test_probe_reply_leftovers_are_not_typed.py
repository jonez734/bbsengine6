"""The terminal probe's reply is not typed input: bytes read with a DA reply are not queued as keys.

query_terminal puts the bytes around a matched reply back on the input queue, so a stray byte that
arrives with the DA reply was typed into the next field (the '?' before the moniker prompt). The
probe passes discard_leftover=True; ordinary callers keep the queuing.
"""

import pytest

from bbsengine6.io import common, terminal


class _Stream:
    encoding = "utf-8"

    def fileno(self):
        return 0


def _run_query(monkeypatch, chunks, **kwargs):
    queued = []
    monkeypatch.setattr(common, "_queue", lambda: queued)
    monkeypatch.setattr(common, "_in_raw_session", lambda: True)
    monkeypatch.setattr(common, "_write_current_output_stream", lambda *a, **k: None)
    monkeypatch.setattr(common, "_restore_cooked", lambda *a, **k: None)
    monkeypatch.setattr(common, "drain_stream_to_queue", lambda *a, **k: None)
    monkeypatch.setattr(common, "_in_stream", lambda: _Stream())
    monkeypatch.setattr(common.termios, "tcgetattr", lambda fd: [])
    reads = iter(chunks)
    monkeypatch.setattr(common.os, "read", lambda fd, n: next(reads, b""))
    monkeypatch.setattr(common.select, "select", lambda r, w, x, t: (r, [], []))
    result = common.query_terminal(terminal.DA1_REQUEST, terminal.DA1_REPLY_RE,
                                   timeout=0.01, **kwargs)
    return result, queued


def test_stray_byte_with_da_reply_is_not_queued_when_discarding(monkeypatch):
    result, queued = _run_query(
        monkeypatch, [b"?\x1b[?61;1;21;22;28c"], discard_leftover=True)
    assert result == "\x1b[?61;1;21;22;28c"
    assert queued == [], "the stray byte is not typed input"


def test_stray_byte_is_queued_by_default(monkeypatch):
    # Ordinary callers still get their typed bytes back in order.
    result, queued = _run_query(monkeypatch, [b"?\x1b[?61;1;21;22;28c"])
    assert result == "\x1b[?61;1;21;22;28c"
    assert "".join(queued) == "?"


def test_probe_da_discards_leftovers(monkeypatch):
    seen = {}

    def fake_query(request, reply_re, timeout=0.5, discard_leftover=False):
        seen["discard"] = discard_leftover
        return "\x1b[?62c"

    monkeypatch.setattr(common, "query_terminal", fake_query)
    assert terminal.probe_da() == "\x1b[?62c"
    assert seen["discard"] is True


if __name__ == "__main__":
    pytest.main([__file__])
