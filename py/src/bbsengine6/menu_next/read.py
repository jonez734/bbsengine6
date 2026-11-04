"""
bbsengine6/menu_next/read.py
Read one command from a menu.

``read_menu`` reads a line with ``io.inputstring`` and resolves it against a
list of ``MenuOption``s. Typed text may be a canonical key or an alias, in any
case. The result is always the canonical key (``Choice.key``).

Rules:
  - The first word selects an option. Case-insensitive.
  - An option with ``subcommands`` takes its subcommand as the next word.
  - An option with a ``parser`` parses the rest of the line into
    ``Choice.args``. A parse failure beeps and re-prompts.
  - An option with no parser accepts no further text. Extra text beeps.
  - Completion offers enabled first words, then enabled subcommand names.

Import policy: as for the rest of ``menu_next``, no ``bbsengine6.util`` and
no ``bbsengine6.database``. ``bbsengine6.io`` is permitted.
"""

from __future__ import annotations

import argparse
import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Optional

from .options import MenuOption
from .visibility import visible_options


@dataclass(frozen=True)
class Choice:
    """The result of ``read_menu``.

    ``key`` is the canonical key of the chosen option. ``subcommand`` is the
    chosen subcommand name for an option with subcommands (e.g. ``"hit"`` for
    ``game hit``), otherwise ``None``. ``args`` is the parsed
    ``argparse.Namespace`` when the option (or subcommand) has a parser,
    otherwise ``None``. ``result`` is what the option's ``action`` returned in
    key mode, or ``None`` when the option has no action.
    """

    key: str
    args: Optional[argparse.Namespace] = None
    subcommand: Optional[str] = None
    result: Any = None


class _ParseError(Exception):
    """Raised by the parser's ``error()`` so a bad line re-prompts instead of exiting."""


def _parse(parser: argparse.ArgumentParser, words: list[str]) -> argparse.Namespace:
    """Parse ``words`` with ``parser`` without letting it exit the session.

    ``argparse`` calls ``sys.exit`` on a bad argument, and a plain parser built by
    a command's ``buildargs()`` does exactly that. Catch the exit and raise
    :class:`_ParseError` so the caller can beep and re-prompt.
    """
    try:
        return parser.parse_args(words)
    except SystemExit as exc:
        raise _ParseError(str(exc)) from None


def _index(spec: Iterable[MenuOption], state: Any, check) -> dict[str, tuple[MenuOption, Optional[str]]]:
    """Map each enabled key and alias (lowercased) to ``(option, subcommand)``.

    ``subcommand`` is ``None`` for a canonical key. For an alias listed in the
    option's ``alias_subcommand``, it is the subcommand that alias runs, so the
    alias needs no subcommand word of its own. Disabled options are not indexed.
    """
    table: dict[str, tuple[MenuOption, Optional[str]]] = {}
    for opt in visible_options(spec, state, check):
        table[opt.letter.lower()] = (opt, None)
        for alias in opt.aliases:
            target = (opt.alias_subcommand or {}).get(alias)
            table[alias.lower()] = (opt, target.lower() if target else None)
    return table


def _split(line: str) -> list[str]:
    """Split a typed line into words. Unbalanced quotes raise ``ValueError``."""
    return shlex.split(line)


def _enabled_subcommands(opt: MenuOption, state: Any, check) -> dict[str, MenuOption]:
    """Subcommand name (lowercased) -> option, for the subcommands that are enabled.

    Each subcommand carries its own gates, so it is filtered by ``visible_options``
    like a top-level option.
    """
    subs = list((opt.subcommands or {}).items())
    sub_opts = [o for _name, o in subs]
    enabled = {id(o) for o in visible_options(sub_opts, state, check)}
    return {name.lower(): o for name, o in subs if id(o) in enabled}


def _resolve(
    line: str,
    table: dict[str, tuple[MenuOption, Optional[str]]],
    state: Any = None,
    check=None,
) -> Optional[tuple[MenuOption, Optional[str], list[str]]]:
    """Return ``(option, subcommand, args)`` for a valid line, or ``None``.

    ``subcommand`` is the subcommand the line selects: from an alias that names
    one, or from the next word for a key with subcommands. ``args`` are the
    remaining words, passed to the subcommand's (or option's) parser.
    """
    try:
        words = _split(line)
    except ValueError:
        return None
    if not words:
        return None
    hit = table.get(words[0].lower())
    if hit is None:
        return None
    opt, alias_sub = hit
    rest = words[1:]
    if alias_sub is not None:
        # The alias already names the subcommand; every typed word is an argument.
        if not _subcommand_enabled(opt, alias_sub, state, check):
            return None
        return opt, alias_sub, rest
    if opt.subcommands:
        if not rest:
            return None
        sub = rest[0].lower()
        if sub not in _enabled_subcommands(opt, state, check):
            return None
        return opt, sub, rest[1:]
    return opt, None, rest


def _subcommand_enabled(opt: MenuOption, sub: str, state: Any, check) -> bool:
    return sub in _enabled_subcommands(opt, state, check)


def _arg_option(opt: MenuOption, sub: Optional[str]) -> MenuOption:
    """The option whose parser and gates apply: the subcommand if one is chosen."""
    if sub is None:
        return opt
    for name, sub_opt in opt.subcommands.items():
        if name.lower() == sub:
            return sub_opt
    return opt


def _accept(line: str, table: dict, state: Any, check) -> bool:
    """``verify`` for ``inputstring``: True only when the line would be accepted."""
    resolved = _resolve(line, table, state, check)
    if resolved is None:
        return False
    opt, sub, args = resolved
    target = _arg_option(opt, sub)
    if target.parser is not None:
        try:
            _parse(target.parser, args)
        except _ParseError:
            return False
        return True
    return not args


def _completions(prefix: str, table: dict, state: Any, check) -> list[str]:
    """Candidates for the buffer ``prefix``.

    With no space yet, complete enabled top-level keys and aliases. After a key
    with subcommands and a space, complete its enabled subcommand names.
    """
    text = prefix.lstrip()
    if " " not in text:
        starts = text.lower()
        return sorted({k for k in table if k.startswith(starts)})
    head, _, tail = text.partition(" ")
    hit = table.get(head.lower())
    if hit is None or not hit[0].subcommands or hit[1] is not None:
        return []
    opt = hit[0]
    starts = tail.lstrip().lower()
    subs = _enabled_subcommands(opt, state, check)
    return sorted(k for k in subs if k.startswith(starts))


#: The exit letters every key-mode menu protects. ``X`` is the official exit; ``Q`` is an
#: alias of it, kept for backward compatibility.
PROTECTED_EXITS = ("X", "Q")


def _protected_table(options: list, protected: tuple) -> dict[str, MenuOption]:
    """Resolve each protected key to the option that owns it, refusing any conflicting spec.

    A protected key is an option's letter, or an alias of one. ``X`` is the exit, and ``Q`` is an
    alias of ``X``. The rules, all enforced at build time:

    - every protected key must resolve to an option in the spec;
    - no option other than the owner may use a protected key, as its letter or as an alias.

    So a spec that defines ``Q`` as its own option is refused, because ``Q`` belongs to the exit.
    """
    wanted = [p.upper() for p in protected]
    by_letter = {o.letter.upper(): o for o in options}
    by_alias: dict[str, MenuOption] = {}
    for opt in options:
        for alias in opt.aliases:
            by_alias.setdefault(alias.upper(), opt)

    table: dict[str, MenuOption] = {}
    for letter in wanted:
        owner = by_letter.get(letter) or by_alias.get(letter)
        if owner is None:
            raise ValueError(f"key-mode menu must define protected key {letter!r}")
        table[letter] = owner

    for opt in options:
        if any(opt is owner for owner in table.values()):
            continue
        claimed = {opt.letter.upper(), *(a.upper() for a in opt.aliases)}
        clash = claimed & set(table)
        if clash:
            raise ValueError(f"option {opt.letter!r} may not use protected key {sorted(clash)[0]!r}")

    # Q is an alias of X. Any protected key other than X must resolve to the exit, so a separate Q
    # option is refused even when X does not declare Q as an alias.
    exit_option = table.get("X")
    for letter in wanted:
        if letter == "X":
            continue
        if exit_option is None or table[letter] is not exit_option:
            if letter in by_letter:
                raise ValueError(f"protected key {letter!r} belongs to the exit, not an option")
    return table


def read_menu(
    prompt: str,
    spec: Iterable[MenuOption],
    *,
    state: Any = None,
    check=None,
    default: str = "",
    help: Any = None,
    reader: Any = None,
    mode: str = "line",
    protected: tuple = PROTECTED_EXITS,
) -> Choice:
    """Read one command line and return the chosen option as a :class:`Choice`.

    Args:
        prompt: prompt text, passed to ``io.inputstring``.
        spec: the menu's ``MenuOption``s.
        state: player state for ``visible_options`` (duck-typed).
        check: optional ``check(module_path, op) -> bool`` gate.
        default: canonical key returned for an empty line. Must be a key in
            ``spec`` when given.
        help: F1 help, passed through to ``io.inputstring``.
        reader: the line reader, called with the same keyword arguments as
            ``io.inputstring``. Defaults to ``io.inputstring``. A hosting program
            passes its own so the menu reads through its terminal.

    Invalid input beeps and re-prompts (``inputstring`` ``verify`` semantics).
    """
    if mode == "key":
        return _read_key(prompt, spec, state=state, check=check, default=default,
                         help=help, reader=reader, protected=protected)
    if mode != "line":
        raise ValueError(f"mode must be 'line' or 'key', not {mode!r}")

    from ..io import inputstring as _default_reader
    from ..io.inputstring import Completer

    read_line = reader if reader is not None else _default_reader

    options = list(spec)
    keys = {o.letter.lower() for o in options}
    if default and default.lower() not in keys:
        raise ValueError(f"default {default!r} is not a menu key")

    table = _index(options, state, check)

    def verify(buffer: str, **_kwargs) -> bool:
        # inputstring passes its own keyword arguments (_history, pagesize, f1_help, ...) to every
        # verify call. Menu validation needs none of them, so accept and ignore them.
        if not buffer.strip() and default:
            return True
        return _accept(buffer, table, state, check)

    completer = Completer(
        lambda prefix, **_kw: _completions(prefix, table, state, check)
    )

    line = read_line(
        prompt,
        verify=verify,
        completer=completer,
        help=help,
    ).strip()

    if not line:
        line = default
    resolved = _resolve(line, table, state, check)
    if resolved is None:
        # Only reachable when verify was bypassed; keep the contract explicit.
        raise ValueError(f"no menu option for {line!r}")
    opt, sub, args = resolved
    target = _arg_option(opt, sub)
    namespace = _parse(target.parser, args) if target.parser is not None else None
    if target.parser is None and args:
        raise ValueError(f"{line!r} takes no arguments")
    return Choice(opt.letter, namespace, sub)


def _read_key(
    prompt: str,
    spec: Iterable[MenuOption],
    *,
    state: Any,
    check,
    default: str,
    help: Any,
    reader: Any,
    protected: tuple,
) -> Choice:
    """Key mode: read one key, run the matched option's action, and return its ``Choice``.

    The key is uppercased, as ``io.inputchoice`` does, so ``Choice.key`` is uppercase here. A key is
    accepted only if it names a visible option or alias; anything else rings the bell and reads again.
    ``default`` is used when Enter is pressed alone. Options with subcommands are not offered in key
    mode, because a single key cannot carry a verb.
    """
    from ..io import inputchoice as _default_reader

    read_key = reader if reader is not None else _default_reader

    options = list(spec)
    protected_table = _protected_table(options, protected)
    table = _index(options, state, check)
    # Protected exits are always offered and never gated.
    for letter, opt in protected_table.items():
        table[letter.lower()] = (opt, None)

    offered = sorted({k.upper() for k in table if table[k][1] is None and table[k][0].subcommands is None})
    if default and default.upper() not in offered:
        raise ValueError(f"default {default!r} is not a key offered in key mode")

    while True:
        key = read_key(prompt, "".join(offered), default.upper() if default else "", help=help)
        if key is None:
            key = ""
        key = key.strip().upper()
        if not key:
            key = default.upper() if default else ""
        if not key:
            continue
        hit = table.get(key.lower())
        if hit is None or hit[0].subcommands:
            # Unmatched, or a verb-carrying option (not offered in key mode): ring and read again.
            from ..io import echo as _echo
            _echo("{bell}", end="", flush=True)
            continue
        opt, _sub = hit
        result = opt.action(state) if opt.action is not None else None
        return Choice(opt.letter.upper(), None, None, result)
