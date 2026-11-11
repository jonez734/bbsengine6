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


def _note_timeout(name: str) -> None:
    """Remember that the probe ``name`` got no reply in time, so a late reply for it is recorded."""
    from ..interaction import current_session

    current_session().da_timed_out.add(name)


def _record(sent: bool, reply) -> dict:
    """One ``report()["da"]`` entry. ``timed_out`` means it was sent and no reply came in time."""
    return {
        "sent": bool(sent),
        "reply": reply if sent else None,
        "timed_out": bool(sent) and reply is None,
        "late": False,
    }


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
            _note_timeout("da1")
            reply = common.query_terminal(DA2_REQUEST, _ANY_DA_RE, timeout=wait)
        if reply is None:
            _note_timeout("da2")
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
    from ..interaction import current_session

    if not block:
        return False
    cached = current_session().terminal_report
    reply = cached["ansi"] if cached is not None else probe_da(block=True)
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


# --------------------------------------------------------------------------
# XTGETTCAP (DCS + q) capability query, for truecolor detection
# --------------------------------------------------------------------------

#: Hex of "RGB", the terminfo/ncurses direct-color capability name.
XTGETTCAP_RGB_NAME = "524742"

#: Request: DCS + q <hex name> ST. ST is written as ESC \ (ESC 0x5c).
XTGETTCAP_RGB_REQUEST = f"\x1bP+q{XTGETTCAP_RGB_NAME}\x1b\\"

#: Reply: DCS 1 + r <hex name> [= <hex value>] ST  (valid) or DCS 0 + r ST (invalid).
#: Hex digits are matched case-insensitively. The name is not checked here.
XTGETTCAP_REPLY_RE = re.compile(
    r"\x1bP(?P<status>[01])\+r(?P<name>[0-9A-Fa-f]+)(?:=(?P<value>[0-9A-Fa-f]*))?\x1b\\"
)


def xtgettcap_request(name: str) -> str:
    """The XTGETTCAP request for capability ``name``: DCS + q <hex of name> ST.

    The name must be printable ASCII (a terminfo capability name); anything else is refused, since
    it would not encode to a name the terminal can match.
    """
    if not name or not all(33 <= ord(c) <= 126 for c in name):
        raise ValueError(f"capability name must be printable ASCII: {name!r}")
    return f"\x1bP+q{name.encode('ascii').hex()}\x1b\\"


def _unhex(text: str) -> str | None:
    """Decode a hex string to text. None when the text is not even-length hex."""
    if not text:
        return ""
    if len(text) % 2:
        return None
    return bytes.fromhex(text).decode("latin-1")


def parse_xtgettcap_reply(reply):
    """Parse an XTGETTCAP reply to the RGB query.

    Returns a dict with ``valid`` (bool), ``name`` (the decoded capability name), and
    ``value`` (the decoded value string, or None when the reply has no ``=value``).
    Name and value are hex-encoded on the wire (two digits per character), so both are
    decoded. Returns None when ``reply`` is not an XTGETTCAP reply, or when a name or value
    is not valid hex.
    """
    if not reply:
        return None
    m = XTGETTCAP_REPLY_RE.fullmatch(reply)
    if not m:
        return None
    name = _unhex(m.group("name"))
    raw_value = m.group("value")
    value = _unhex(raw_value) if raw_value is not None else None
    if name is None or (raw_value is not None and value is None):
        return None
    return {"valid": m.group("status") == "1", "name": name, "value": value}


def query_cap(name: str, timeout=None):
    """Ask the terminal for capability ``name`` over XTGETTCAP.

    Returns the value as a str when the terminal gives one, True when it has the capability with no
    value, False when it says it does not, and None when it does not answer for ``name`` in time.
    Blocking, like :func:`report`. Terminfo is the static lookup (``terminfo.load(term).get(cap)``);
    this asks the running terminal.
    """
    from . import common

    wait = _ANSI_PROBE_TIMEOUT if timeout is None else float(timeout)
    try:
        reply = common.query_terminal(xtgettcap_request(name), XTGETTCAP_REPLY_RE, timeout=wait)
    except Exception:  # no terminal
        return None
    parsed = parse_xtgettcap_reply(reply) if reply is not None else None
    if not parsed or parsed["name"] != name:
        return None
    if not parsed["valid"]:
        return False
    value = parsed["value"]
    return True if value in (None, "") else value


def rgb_from_reply(parsed) -> bool | None:
    """True/False for the RGB capability from a parsed reply, or None when unknown.

    A valid reply whose value is an integer of 8 or more means direct color (8 bits per
    component). A valid reply with no numeric value is treated as direct color too, since
    the capability is present. An invalid reply, or a name other than RGB, gives None.
    """
    if not parsed or parsed["name"] != "RGB":
        return None
    if not parsed["valid"]:
        return False
    value = parsed["value"]
    if value is None or value == "":
        return True
    if value.isdigit():
        return int(value) >= 8
    return None


TRUECOLOR_COLORS = 1 << 24  # 16777216, the 24-bit palette


def in_screen() -> bool:
    """True when this process runs under GNU screen: STY is set, or TERM names screen.

    screen does not carry 24-bit colour, and it passes the outer terminal's COLORTERM through, so
    the report must not take truecolor from the environment there.
    """
    term = os.environ.get("TERM", "")
    return bool(os.environ.get("STY")) or term == "screen" or term.startswith("screen.") or term.startswith("screen-")


def _terminfo_colors(term: str):
    """The terminfo ``colors`` number for ``term``, or None when it has no entry."""
    from . import terminfo

    if not term or not terminfo.has_entry(term):
        return None
    return terminfo.load(term).nums.get("colors")


def report(timeout=None, refresh=False) -> dict:
    """Describe the terminal this process runs in: color depth and where it came from.

    ``term`` is the terminal type this process uses, from :func:`resolve` (the client TERM when it
    has a terminfo entry, else the default). ``dumb`` (and an empty TERM) is reported as itself, so a
    test can see it; :func:`resolve` would refuse it.

    Order for ``true_color``:
    1. The XTGETTCAP RGB query (DCS + q), if the terminal answers it.
    2. ``COLORTERM`` set to ``truecolor`` or ``24bit``.
    3. Unknown (None). Silence is not evidence of no color; callers must not treat it as one.

    ``colors`` is the terminfo ``colors`` number for the resolved TERM (None when there is no
    entry), except that a truecolor terminal reports ``TRUECOLOR_COLORS`` (16777216), since terminfo
    often lags behind. ``color_256`` is True when ``colors`` is at least 256 or ``true_color`` is True,
    False when ``colors`` is known and smaller, and None when neither is known.

    ``source`` is ``"query"``, ``"colorterm"``, or ``"unknown"``, and says which step gave
    ``true_color``. The query uses the same timeout as the DA probe.

    Returns ``source="unknown"`` with no tty. Runs the DA probe first (ansi detection; the
    result is in ``ansi``), then the RGB query. Blocking only. A silent terminal costs up to
    three timeouts: DA1, DA2, and the RGB query.
    """
    from ..interaction import current_session
    from . import common

    cached = current_session().terminal_report
    if cached is not None and not refresh:
        return cached

    wait = _ANSI_PROBE_TIMEOUT if timeout is None else float(timeout)
    term = os.environ.get("TERM", "")
    if term not in UNUSABLE_TERMS:
        term, _ = resolve()
    colors = _terminfo_colors(term)
    ansi = probe_da(timeout=wait)
    # probe_da sends DA2 only when DA1 gets no reply, so DA2 was sent exactly when DA1 timed out.
    # A DA1 reply is "ESC[?"; a DA2 reply is "ESC[>".
    probing = _ANSI_PROBE_ENABLED
    da1_reply = ansi if (ansi and ansi.startswith("\x1b[?")) else None
    da2_reply = ansi if (ansi and ansi.startswith("\x1b[>")) else None
    da = {
        "da1": _record(probing, da1_reply),
        "da2": _record(probing and da1_reply is None, da2_reply),
    }

    true_color = None
    source = "unknown"
    # COLORTERM is decided first. When it already says truecolor the RGB query is not sent: a
    # terminal that does not answer it echoes the query text back as stray input characters, and
    # the reply would only confirm what COLORTERM says.
    colorterm = os.environ.get("COLORTERM", "").strip().lower()
    under_screen = in_screen()
    if under_screen:
        # screen passes the outer terminal's COLORTERM through, but has no 24-bit colour.
        colorterm = ""
    rgb_sent = colorterm not in ("truecolor", "24bit") and not under_screen
    reply = None
    if rgb_sent:
        try:
            reply = common.query_terminal(XTGETTCAP_RGB_REQUEST, XTGETTCAP_REPLY_RE, timeout=wait)
        except Exception:  # no terminal
            reply = None
        if reply is None:
            _note_timeout("rgb")
    if reply is not None:
        rgb = rgb_from_reply(parse_xtgettcap_reply(reply))
        if rgb is not None:
            true_color, source = rgb, "query"

    if under_screen:
        true_color, source = False, "screen"
    elif source == "unknown" and not rgb_sent:
        true_color, source = True, "colorterm"

    # A truecolor terminal has a 24-bit palette whatever terminfo says (xterm's entry still says 8),
    # so colors and true_color agree.
    if true_color:
        colors = TRUECOLOR_COLORS

    if under_screen:
        # screen does not do colour here: its terminfo count is not evidence of usable colour.
        color_256 = False
    elif true_color or (colors is not None and colors >= 256):
        color_256 = True
    elif colors is not None:
        color_256 = False
    else:
        color_256 = None

    da["rgb"] = _record(rgb_sent, reply)
    late = {name: text for name, text in current_session().late_da_replies}
    for name, entry in da.items():
        # Only a probe that was sent can have a late reply.
        if entry["sent"] and name in late:
            entry["late"] = True
            entry["reply"] = late[name]
    result = {
        "term": term,
        "colors": colors,
        "true_color": true_color,
        "color_256": color_256,
        "source": source,
        "ansi": ansi,
        "da": da,
    }
    current_session().terminal_report = result
    return result
