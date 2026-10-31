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
    otherwise ``None``.
    """

    key: str
    args: Optional[argparse.Namespace] = None
    subcommand: Optional[str] = None


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


def read_menu(
    prompt: str,
    spec: Iterable[MenuOption],
    *,
    state: Any = None,
    check=None,
    default: str = "",
    help: Any = None,
    reader: Any = None,
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
    from ..io import inputstring as _default_reader
    from ..io.inputstring import Completer

    read_line = reader if reader is not None else _default_reader

    options = list(spec)
    keys = {o.letter.lower() for o in options}
    if default and default.lower() not in keys:
        raise ValueError(f"default {default!r} is not a menu key")

    table = _index(options, state, check)

    def verify(buffer: str) -> bool:
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
