from .const import FALLBACK_TERMINAL_WIDTH, OSC, ST

import os
import re
import shutil

MAX_WIDTH = 120


def size() -> os.terminal_size:
    return shutil.get_terminal_size()


def columns():
    """
    Return terminal width in columns, clamped to MAX_WIDTH (or env var BBSENGINE_MAX_WIDTH).
    On OSError (unable to determine size) return a sane fallback (100).
    """
    try:
        w = size()[0]
    except OSError:
        return FALLBACK_TERMINAL_WIDTH

    max_width = os.environ.get("BBSENGINE_MAX_WIDTH")
    if max_width is not None:
        try:
            max_width = int(max_width)
        except ValueError:
            max_width = MAX_WIDTH
    else:
        max_width = MAX_WIDTH

    return min(w, max_width)


width = columns


def lines():
    return size().lines


height = lines


def title(t: str) -> None:
    """Set the terminal window title."""
    from .common import write_current_output_stream

    write_current_output_stream(f"{OSC}0;{t}{ST}", flush=True)


#: Fallback when neither the client TERM nor the member's stored type has a terminfo entry.
DEFAULT_TERM = "xterm"

#: TERM values that cannot drive a full-screen program (refused, not resolved).
UNUSABLE_TERMS = ("", "dumb")


def resolve(stored=None, client=None):
    """Return ``(value, source)`` for the terminal type to use.

    Order: the client's TERM when it has a terminfo entry (``client``), else the member's
    stored terminal type when valid (``stored``), else ``xterm`` (``default``). A client
    TERM with no entry is rejected by :func:`resolve_notice`, not here.
    """
    from . import terminfo

    if client is None:
        client = os.environ.get("TERM", "")
    if client not in UNUSABLE_TERMS and terminfo.has_entry(client):
        return client, "client"
    if stored and terminfo.has_entry(stored):
        return stored, "stored"
    return DEFAULT_TERM, "default"


def resolve_notice(stored=None, client=None):
    """Return a notice when the client TERM was rejected for having no terminfo entry."""
    if client is None:
        client = os.environ.get("TERM", "")
    if client in UNUSABLE_TERMS:
        return None
    from . import terminfo

    if terminfo.has_entry(client):
        return None
    value, _ = resolve(stored=stored, client=client)
    return f"TERM {client!r} has no terminfo entry; using {value!r} instead."


# --------------------------
# ANSI detection (DA query)
# --------------------------

#: Config defaults for the ``terminal.ansi_probe`` block in bed.json / zoid6.json.
_ANSI_PROBE_ENABLED = True
_ANSI_PROBE_TIMEOUT = 0.5

#: DA1 request (primary device attributes) and DA2 fallback (secondary).
DA1_REQUEST = "\x1b[c"
DA2_REQUEST = "\x1b[>c"

#: Replies that count as an ANSI terminal: DA1 (ESC[?...c) or DA2 (ESC[>...c).
DA1_REPLY_RE = re.compile(r"\x1b\[\?[0-9;]*c")
DA2_REPLY_RE = re.compile(r"\x1b\[>[0-9;]*c")
_ANY_DA_RE = re.compile(r"\x1b\[[?>][0-9;]*c")


def configure_ansi_probe(cfg) -> None:
    """Apply the ``terminal.ansi_probe`` block from bed.json / zoid6.json.

    ``cfg`` is the parsed ``terminal`` section (a dict), or None for defaults. Keys:
    ``ansi_probe.enabled`` (bool) and ``ansi_probe.timeout_seconds`` (positive number).
    Bad values raise ValueError.
    """
    global _ANSI_PROBE_ENABLED, _ANSI_PROBE_TIMEOUT
    block = {} if cfg is None else cfg.get("ansi_probe", {})
    if not isinstance(block, dict):
        raise ValueError("terminal.ansi_probe must be an object")
    enabled = block.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("terminal.ansi_probe.enabled must be true or false")
    timeout = block.get("timeout_seconds", 0.5)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("terminal.ansi_probe.timeout_seconds must be a positive number")
    _ANSI_PROBE_ENABLED = enabled
    _ANSI_PROBE_TIMEOUT = float(timeout)


def probe_da(timeout=None):
    """Send DA1, then DA2 if DA1 gets no reply. Return the raw reply, or None.

    Returns None without writing anything when ``terminal.ansi_probe.enabled`` is false,
    and None when neither query gets a reply or there is no terminal. The reply is logged
    at debug level for debugging.
    """
    if not _ANSI_PROBE_ENABLED:
        return None
    from . import common
    from .echo import echo

    wait = _ANSI_PROBE_TIMEOUT if timeout is None else float(timeout)
    try:
        reply = common.query_terminal(DA1_REQUEST, _ANY_DA_RE, timeout=wait)
        if reply is None:
            reply = common.query_terminal(DA2_REQUEST, _ANY_DA_RE, timeout=wait)
    except Exception as exc:  # no terminal, or the tty refused the mode change
        echo(f"terminal.probe_da: no reply ({exc})", level="debug")
        return None
    echo(f"terminal.probe_da: reply {reply!r}", level="debug")
    return reply


def has_ansi() -> bool:
    """True when the probe_da() reply is an approved DA1 or DA2 response."""
    reply = probe_da()
    if not reply:
        return False
    return bool(DA1_REPLY_RE.fullmatch(reply) or DA2_REPLY_RE.fullmatch(reply))
