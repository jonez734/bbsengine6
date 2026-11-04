"""Key mode for menu_next: one key runs the option's action, uppercase throughout.

Key mode reads one key through ``reader`` (the same call shape as ``io.inputchoice``). A key is
uppercased, a matched option's ``action`` runs and its result comes back in ``Choice.result``, and
the protected exits ``X`` and ``Q`` are always offered. ``Q`` is an alias of ``X``.
"""

import pytest

from bbsengine6.menu_next import MenuOption, read_menu
from bbsengine6.menu_next.read import Choice


pytestmark = pytest.mark.unit


class Keys:
    """A scripted key reader with the ``inputchoice`` signature."""

    def __init__(self, *keys):
        self.keys = list(keys)
        self.calls = []

    def __call__(self, prompt, options, default="", **kwargs):
        self.calls.append((prompt, options, default))
        return self.keys.pop(0)


def _spec(**actions):
    """A casino-style root: B and S with actions, X the protected exit (Q is its alias)."""
    return (
        MenuOption(letter="B", label="Blackjack", action=actions.get("b", lambda a: "bj")),
        MenuOption(letter="S", label="Stats", action=actions.get("s", lambda a: "stats")),
        MenuOption(letter="X", label="Exit", aliases=("Q",), action=lambda a: "bye"),
    )


def test_key_runs_its_action_and_returns_it_in_result():
    choice = read_menu("p: ", _spec(), mode="key", reader=Keys("B"))
    assert choice.key == "B"
    assert choice.result == "bj"


def test_key_is_uppercased_before_matching():
    choice = read_menu("p: ", _spec(), mode="key", reader=Keys("b"))
    assert choice.key == "B"
    assert choice.result == "bj"


def test_enter_alone_selects_the_default():
    choice = read_menu("p: ", _spec(), mode="key", default="x", reader=Keys(""))
    assert choice.key == "X"
    assert choice.result == "bye"


def test_default_is_uppercased_in_the_options_string_and_default_arg():
    reader = Keys("S")
    read_menu("p: ", _spec(), mode="key", default="x", reader=reader)
    _prompt, options, default = reader.calls[0]
    assert default == "X"
    assert options == "".join(sorted(options))  # offered keys are sorted and uppercase
    assert options.isupper()


def test_q_returns_x_and_runs_the_exit_action():
    choice = read_menu("p: ", _spec(), mode="key", reader=Keys("Q"))
    assert choice.key == "X"
    assert choice.result == "bye"


def test_unmatched_key_rings_and_reads_again(monkeypatch):
    rang = []
    monkeypatch.setattr("bbsengine6.io.echo", lambda text="", **kw: rang.append(text))
    choice = read_menu("p: ", _spec(), mode="key", reader=Keys("Z", "S"))
    assert choice.key == "S"
    assert any("{bell}" in str(t) for t in rang)


def test_a_gated_option_is_refused_but_x_is_never_gated():
    class Player:
        is_sysop = False

    spec = (
        MenuOption(letter="B", label="Blackjack", action=lambda a: "bj", sysop_only=True),
        MenuOption(letter="X", label="Exit", aliases=("Q",), action=lambda a: "bye", sysop_only=True),
    )
    # B is hidden for a non-sysop, so B rings and the reader is asked again for X.
    choice = read_menu("p: ", spec, mode="key", state=Player(), reader=Keys("B", "X"))
    assert choice.key == "X"


def test_a_spec_without_x_is_refused_at_build_time():
    spec = (MenuOption(letter="B", label="Blackjack", action=lambda a: "bj"),)
    with pytest.raises(ValueError, match="protected key 'X'"):
        read_menu("p: ", spec, mode="key", reader=Keys("B"))


def test_a_spec_may_not_define_q_as_a_normal_option():
    spec = (
        MenuOption(letter="Q", label="Quit", action=lambda a: "q"),
        MenuOption(letter="X", label="Exit", action=lambda a: "bye"),
    )
    with pytest.raises(ValueError, match="protected key"):
        read_menu("p: ", spec, mode="key", reader=Keys("X"))


def test_a_subcommand_option_is_not_offered_in_key_mode(monkeypatch):
    sub = MenuOption(letter="hit", label="hit", action=lambda a: "hit")
    spec = (
        MenuOption(letter="G", label="Game", subcommands={"hit": sub}, action=lambda a: "game"),
        MenuOption(letter="X", label="Exit", aliases=("Q",), action=lambda a: "bye"),
    )
    monkeypatch.setattr("bbsengine6.io.echo", lambda *a, **k: None)
    choice = read_menu("p: ", spec, mode="key", reader=Keys("G", "X"))
    assert choice.key == "X"


def test_an_exception_from_the_action_propagates():
    def boom(args):
        raise RuntimeError("action failed")

    spec = (
        MenuOption(letter="B", label="Blackjack", action=boom),
        MenuOption(letter="X", label="Exit", action=lambda a: "bye"),
    )
    with pytest.raises(RuntimeError, match="action failed"):
        read_menu("p: ", spec, mode="key", protected=("X",), reader=Keys("B"))


def test_an_option_without_an_action_returns_no_result():
    spec = (
        MenuOption(letter="B", label="Blackjack"),
        MenuOption(letter="X", label="Exit"),
    )
    choice = read_menu("p: ", spec, mode="key", protected=("X",), reader=Keys("B"))
    assert choice == Choice("B", None, None, None)
    assert choice.result is None


def test_line_mode_is_unchanged_and_lowercase():
    spec = (
        MenuOption(letter="casino", label="casino"),
        MenuOption(letter="x", label="exit"),
    )

    def reader(prompt, verify=None, completer=None, help=None, **kw):
        return "CASINO"

    choice = read_menu("p: ", spec, reader=reader)
    assert choice.key == "casino"


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match="mode must be"):
        read_menu("p: ", _spec(), mode="sideways", reader=Keys("B"))
