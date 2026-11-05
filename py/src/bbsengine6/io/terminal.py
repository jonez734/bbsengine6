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


def probe_da(timeout=None, block=True):
    """Send DA1, then DA2 if DA1 gets no reply. Return the raw reply, or None.

    ``block=True`` (default): wait up to the timeout for each query and return the reply, or
    None when neither answers.

    ``block=False``: send DA1 and return None at once, without reading. The reply is taken by
    the input reader and kept for :func:`ansi_reply`, so the caller does not wait. Use
    ``ansi_reply()`` later to collect it.

    Returns None without writing anything when ``terminal.ansi_probe.enabled`` is false. The
    reply is logged at debug level for debugging.
    """
    if not _ANSI_PROBE_ENABLED:
        return None
    from . import common
    from .echo import echo

    wait = _ANSI_PROBE_TIMEOUT if timeout is None else float(timeout)
    if not block:
        try:
            common.write_current_output_stream(DA1_REQUEST, flush=True)
        except Exception as exc:  # no terminal
            echo(f"terminal.probe_da: not sent ({exc})", level="debug")
        return None
    try:
        reply = common.query_terminal(DA1_REQUEST, _ANY_DA_RE, timeout=wait)
        if reply is None:
            reply = common.query_terminal(DA2_REQUEST, _ANY_DA_RE, timeout=wait)
    except Exception as exc:  # no terminal, or the tty refused the mode change
        echo(f"terminal.probe_da: no reply ({exc})", level="debug")
        return None
    echo(f"terminal.probe_da: reply {reply!r}", level="debug")
    return reply


def ansi_reply() -> str | None:
    """Return the oldest DA reply the input reader has taken, or None. Removes it.

    Pairs with ``probe_da(block=False)``: the reply arrives in the input and is kept by the
    reader. Call this later, after reading input, to collect it.
    """
    from ..interaction import current_session

    replies = current_session().da_replies
    return replies.pop(0) if replies else None


def has_ansi(block=True) -> bool:
    """True when the probe_da() reply is an approved DA1 or DA2 response.

    ``block=False`` sends the probe and returns False at once. Call ``ansi_reply()`` and
    ``DA1_REPLY_RE``/``DA2_REPLY_RE`` later to check the answer, or use ``has_ansi()`` again.
    """
    reply = probe_da(block=block)
    if not block:
        return False
    if not reply:
        return False
    return bool(DA1_REPLY_RE.fullmatch(reply) or DA2_REPLY_RE.fullmatch(reply))


def decode_da(reply):
    """Decode a probe_da() reply into its parts, or return None if it is not a DA reply.

    Returns a dict:

    - ``kind``: ``"DA1"`` for ``ESC[?...c`` or ``"DA2"`` for ``ESC[>...c``.
    - ``params``: the numbers between the marker and ``c``, as a list of ints. An empty
      reply (``ESC[?c``) gives an empty list.
    - ``class``: DA1 only. The first parameter, the conformance class (for example 62 for
      VT220, 64 for VT420), or None when absent.
    - ``features``: DA1 only. The remaining parameters, the terminal's feature codes.
    - ``terminal_type``: DA2 only. The first parameter (the terminal model code), or None.
    - ``firmware``: DA2 only. The second parameter (the version), or None.

    Parameters that are not numbers are ignored. The reply must match the DA1 or DA2 shape
    exactly; anything else returns None.
    """
    if not reply:
        return None
    if DA1_REPLY_RE.fullmatch(reply):
        kind, body = "DA1", reply[3:-1]
    elif DA2_REPLY_RE.fullmatch(reply):
        kind, body = "DA2", reply[3:-1]
    else:
        return None
    params = [int(p) for p in body.split(";") if p.isdigit()] if body else []
    if kind == "DA1":
        return {
            "kind": kind,
            "params": params,
            "class": params[0] if params else None,
            "features": params[1:],
        }
    return {
        "kind": kind,
        "params": params,
        "terminal_type": params[0] if params else None,
        "firmware": params[1] if len(params) > 1 else None,
    }
