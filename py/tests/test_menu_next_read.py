"""bbsengine6/tests/test_menu_next_read.py

Tests for ``bbsengine6.menu_next.read_menu`` and the new ``MenuOption``
fields (aliases, parser, sysop_only, op, subcommands), plus the ``check``
gate and ``menu_entries``.

``io.inputstring`` is stubbed. Each test captures the ``verify`` and
``completer`` that ``read_menu`` hands it, then drives them directly, so
the tests cover the real rules without a terminal.
"""

from __future__ import annotations

import argparse
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bbsengine6.menu_next import Choice, MenuOption, menu_entries, read_menu, visible_options


def _table_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False, prog="table")
    p.add_argument("gametype", nargs="?", choices=["blackjack", "poker"])
    p.add_argument("moniker", nargs="?")
    return p


def _matches(completer, prefix):
    """Candidates ``Completer.get_matches`` offers for ``prefix`` (``None`` -> [])."""
    return list(completer.get_matches(prefix) or [])


class _Harness:
    """Run ``read_menu`` with ``io.inputstring`` stubbed.

    The stub behaves like ``inputstring``: each typed line is offered to the
    ``verify`` callback, and a rejected line re-prompts with the next scripted
    line. ``lines`` is the sequence of lines the user types, in order.

    ``verify`` and ``completer`` are recorded so a test can also call them
    directly.
    """

    def __init__(self, *lines: str) -> None:
        self.lines = list(lines) or [""]
        self.verify = None
        self.completer = None
        self.rejected: list[str] = []

    def fake_inputstring(self, prompt, *a, **kw):
        self.verify = kw.get("verify")
        self.completer = kw.get("completer")
        while True:
            if not self.lines:
                raise AssertionError(
                    f"input script exhausted; rejected so far: {self.rejected!r}"
                )
            line = self.lines.pop(0)
            if self.verify is None or self.verify(line):
                return line
            self.rejected.append(line)

    def read(self, spec, **kw) -> Choice:
        with patch("bbsengine6.io.inputstring", side_effect=self.fake_inputstring):
            return read_menu("> ", spec, **kw)


def _spec():
    return [
        MenuOption("t", "Table", "casino.commands.table", parser=_table_parser(),
                   subcommands=None),
        MenuOption("g", "Game", "casino.commands.game", aliases=("hit", "stand"),
                   subcommands={
                       "hit": MenuOption("h", "Hit", op="hit", requires_seated=True,
                                         allowed_game_types=frozenset({"blackjack"})),
                   }),
        MenuOption("q", "Quit"),
    ]


class TestAliasResolution(unittest.TestCase):
    def test_canonical_key_returns_canonical_key(self):
        r = _Harness("t").read(_spec())
        self.assertEqual(r.key, "t")

    def test_alias_resolves_to_canonical_key(self):
        r = _Harness("hit").read([MenuOption("g", "Game", aliases=("hit",))])
        self.assertEqual(r.key, "g")

    def test_alias_is_case_insensitive(self):
        r = _Harness("HIT").read([MenuOption("g", "Game", aliases=("hit",))])
        self.assertEqual(r.key, "g")

    def test_key_is_case_insensitive(self):
        r = _Harness("Q").read([MenuOption("q", "Quit")])
        self.assertEqual(r.key, "q")

    def test_alias_is_not_returned_as_key(self):
        r = _Harness("stand").read([MenuOption("g", "Game", aliases=("hit", "stand"))])
        self.assertNotEqual(r.key, "stand")
        self.assertEqual(r.key, "g")


def _verify_of(spec, seed: str = "q", **kw):
    """The ``verify`` callback ``read_menu`` gives ``inputstring`` for ``spec``.

    ``seed`` must be a line that is valid for ``spec`` (it is typed once so the
    callback is captured the same way it is in real use). The test then calls
    the returned ``verify`` directly on any candidate line.
    """
    h = _Harness(seed)
    h.read(spec, **kw)
    return h.verify


class TestParserAndArgs(unittest.TestCase):
    def test_option_without_parser_returns_args_none(self):
        r = _Harness("q").read([MenuOption("q", "Quit")])
        self.assertIsInstance(r, Choice)
        self.assertIsNone(r.args)

    def test_option_without_parser_rejects_extra_text(self):
        verify = _verify_of([MenuOption("q", "Quit")])
        self.assertFalse(verify("q extra"))

    def test_parser_returns_namespace(self):
        r = _Harness("t blackjack Lobby1").read(_spec())
        self.assertEqual(r.key, "t")
        self.assertEqual(r.args.gametype, "blackjack")
        self.assertEqual(r.args.moniker, "Lobby1")

    def test_parser_optional_positionals_may_be_omitted(self):
        r = _Harness("t").read(_spec())
        self.assertIsNone(r.args.gametype)
        self.assertIsNone(r.args.moniker)

    def test_parser_bad_choice_beeps_via_verify(self):
        self.assertFalse(_verify_of(_spec(), seed="t")("t craps"))

    def test_parser_good_line_passes_verify(self):
        self.assertTrue(_verify_of(_spec(), seed="t")("t poker Main"))

    def test_quoted_moniker_is_one_word(self):
        r = _Harness('t blackjack "Main Room"').read(_spec())
        self.assertEqual(r.args.moniker, "Main Room")

    def test_unbalanced_quote_beeps(self):
        self.assertFalse(_verify_of(_spec(), seed="t")('t blackjack "Main'))


class TestSubcommands(unittest.TestCase):
    def test_enabled_subcommand_passes_verify(self):
        state = SimpleNamespace(current_table_moniker="T1", current_table_game_type="blackjack")
        self.assertTrue(_verify_of(_spec(), seed="t", state=state)("g hit"))

    def test_disabled_subcommand_beeps(self):
        # hit is blackjack-only; the player is at a poker table
        state = SimpleNamespace(current_table_moniker="T1", current_table_game_type="poker")
        self.assertFalse(_verify_of(_spec(), seed="t", state=state)("g hit"))

    def test_unknown_subcommand_beeps(self):
        self.assertFalse(_verify_of(_spec(), seed="t")("g nosuch"))

    def test_bare_key_with_subcommands_beeps(self):
        self.assertFalse(_verify_of(_spec(), seed="t")("g"))

    def test_completer_offers_enabled_subcommands_only(self):
        state = SimpleNamespace(current_table_moniker="T1", current_table_game_type="poker")
        h = _Harness("q")
        h.read(_spec() + [], state=state)
        self.assertEqual(_matches(h.completer, "g h"), [])


class TestCompletion(unittest.TestCase):
    def _completer(self, spec, **kw):
        h = _Harness("q" if any(o.letter == "q" for o in spec) else spec[0].letter)
        h.read(spec, **kw)
        return h.completer

    def test_top_level_completion_lists_keys_and_aliases(self):
        c = self._completer([MenuOption("g", "Game", aliases=("hit",)), MenuOption("q", "Quit")])
        self.assertEqual(_matches(c, "h"), ["hit"])

    def test_top_level_completion_is_prefix_and_case_insensitive(self):
        c = self._completer([MenuOption("q", "Quit")])
        self.assertEqual(_matches(c, "Q"), ["q"])


class TestDefaultAndEmpty(unittest.TestCase):
    def test_empty_line_returns_default(self):
        r = _Harness("").read([MenuOption("q", "Quit")], default="q")
        self.assertEqual(r.key, "q")

    def test_empty_line_with_no_default_is_invalid(self):
        verify = _verify_of([MenuOption("q", "Quit")], seed="q")
        self.assertFalse(verify(""))

    def test_default_must_be_a_menu_key(self):
        with self.assertRaises(ValueError):
            _Harness("").read([MenuOption("q", "Quit")], default="z")


class TestSysopAndCheck(unittest.TestCase):
    def test_sysop_only_hidden_from_non_sysop(self):
        spec = [MenuOption("a", "Admin", sysop_only=True), MenuOption("q", "Quit")]
        state = SimpleNamespace(is_sysop=False)
        self.assertEqual([o.letter for o in visible_options(spec, state)], ["q"])

    def test_sysop_only_shown_to_sysop(self):
        spec = [MenuOption("a", "Admin", sysop_only=True)]
        state = SimpleNamespace(is_sysop=True)
        self.assertEqual([o.letter for o in visible_options(spec, state)], ["a"])

    def test_check_true_keeps_option(self):
        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables")]
        self.assertEqual(len(visible_options(spec, None, check=lambda m, o: True)), 1)

    def test_check_false_hides_option(self):
        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables")]
        self.assertEqual(visible_options(spec, None, check=lambda m, o: False), [])

    def test_check_none_hides_option(self):
        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables")]
        self.assertEqual(visible_options(spec, None, check=lambda m, o: None), [])

    def test_check_raising_hides_option(self):
        def boom(m, o):
            raise RuntimeError("access failed")

        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables")]
        self.assertEqual(visible_options(spec, None, check=boom), [])

    def test_check_not_called_without_module_path_and_op(self):
        calls = []
        spec = [MenuOption("q", "Quit")]
        visible_options(spec, None, check=lambda m, o: calls.append((m, o)) or False)
        self.assertEqual(calls, [])

    def test_check_receives_module_path_and_op(self):
        seen = []
        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables")]
        visible_options(spec, None, check=lambda m, o: seen.append((m, o)) or True)
        self.assertEqual(seen, [("casino.commands.table", "list_tables")])

    def test_check_hides_option_from_read_menu(self):
        spec = [MenuOption("t", "Table", "casino.commands.table", op="list_tables"),
                MenuOption("q", "Quit")]
        verify = _verify_of(spec, seed="q", check=lambda m, o: False)
        self.assertFalse(verify("t"))
        self.assertTrue(verify("q"))


class TestMenuEntries(unittest.TestCase):
    def test_disabled_entries_are_kept_with_flag(self):
        spec = [MenuOption("a", "Admin", sysop_only=True), MenuOption("q", "Quit")]
        pairs = menu_entries(spec, SimpleNamespace(is_sysop=False))
        self.assertEqual([(o.letter, e) for o, e in pairs], [("a", False), ("q", True)])

    def test_menu_entries_keeps_order(self):
        spec = [MenuOption("z", "Z"), MenuOption("a", "A")]
        pairs = menu_entries(spec, None)
        self.assertEqual([o.letter for o, _ in pairs], ["z", "a"])


class TestMenuOptionCompat(unittest.TestCase):
    def test_existing_positional_construction_still_works(self):
        o = MenuOption("q", "Quit", "x.y", True, frozenset({"a"}), None, False)
        self.assertEqual(o.letter, "q")
        self.assertEqual(o.module_path, "x.y")

    def test_parser_and_subcommands_excluded_from_equality(self):
        a = MenuOption("t", "T", parser=_table_parser())
        b = MenuOption("t", "T", parser=None)
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))


if __name__ == "__main__":
    unittest.main()


class TestAliasSubcommand(unittest.TestCase):
    """An alias that names a subcommand runs it; typed words after it are arguments."""

    def _game(self):
        hit = MenuOption("h", "Hit", op="hit", requires_seated=True,
                         allowed_game_types=frozenset({"blackjack"}))
        return MenuOption("g", "Game", "casino.commands.game", aliases=("hit",),
                          alias_subcommand={"hit": "hit"}, subcommands={"hit": hit})

    def _state(self, gt):
        return SimpleNamespace(current_table_moniker="T1", current_table_game_type=gt)

    def test_alias_runs_its_subcommand(self):
        r = _Harness("hit").read([self._game()], state=self._state("blackjack"))
        self.assertEqual(r.key, "g")
        self.assertEqual(r.subcommand, "hit")

    def test_alias_words_are_arguments_not_a_subcommand(self):
        p = argparse.ArgumentParser(add_help=False, prog="hit")
        p.add_argument("amount", type=int)
        hit = MenuOption("h", "Hit", op="hit", requires_seated=True,
                         allowed_game_types=frozenset({"blackjack"}), parser=p)
        game = MenuOption("g", "Game", "casino.commands.game", aliases=("hit",),
                          alias_subcommand={"hit": "hit"}, subcommands={"hit": hit})
        r = _Harness("hit 5").read([game], state=self._state("blackjack"))
        self.assertEqual(r.subcommand, "hit")
        self.assertEqual(r.args.amount, 5)

    def test_alias_hidden_when_subcommand_disabled(self):
        spec = [self._game(), MenuOption("q", "Quit")]
        verify = _verify_of(spec, seed="q", state=self._state("poker"))
        self.assertFalse(verify("hit"))

    def test_canonical_subcommand_still_works(self):
        r = _Harness("g hit").read([self._game()], state=self._state("blackjack"))
        self.assertEqual((r.key, r.subcommand), ("g", "hit"))


class TestReaderParameter(unittest.TestCase):
    """A hosting program supplies its own line reader; the menu rules are unchanged."""

    def test_supplied_reader_is_used_instead_of_io(self):
        calls = []

        def reader(prompt, **kw):
            calls.append(prompt)
            return "q"

        with patch("bbsengine6.io.inputstring", side_effect=AssertionError("io must not be used")):
            choice = read_menu("> ", [MenuOption("q", "Quit")], reader=reader)
        self.assertEqual(calls, ["> "])
        self.assertEqual(choice.key, "q")

    def test_supplied_reader_receives_verify_and_completer(self):
        seen = {}

        def reader(prompt, **kw):
            seen.update(kw)
            return "q"

        read_menu("> ", [MenuOption("q", "Quit")], reader=reader)
        self.assertIn("verify", seen)
        self.assertIn("completer", seen)
