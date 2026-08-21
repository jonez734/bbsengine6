"""bbsengine6/tests/test_menu_next_visibility.py

Tests for ``bbsengine6.menu_next.visible_options`` -- the duck-typed
filter that hides options the player cannot currently pick.

Pins the four gate rules (order matters when multiple gates fire):

  1. ``requires_seated`` -- drop if not seated.
  2. ``allowed_game_types`` (combined with ``requires_seated``) --
     drop if the seated table's game type is unknown or outside the
     set.
  3. ``hide_if_seated_type`` -- drop if the player is seated at a
     table whose game type is in the set.
  4. ``requires_connected`` -- drop if no connection.

The state object is duck-typed: only ``current_table_moniker``,
``current_table_game_type``, and ``connected`` are read. Missing
attributes are treated as ``None`` / ``False``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bbsengine6.menu_next import MenuOption, visible_options
from bbsengine6.menu_next.registry import clear_registry


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


def _seat(table: str | None, gt: str | None) -> SimpleNamespace:
    """Build a duck-typed state with the given seat."""
    return SimpleNamespace(
        current_table_moniker=table,
        current_table_game_type=gt,
        connected=False,
    )


def test_always_available_passes_through_when_unseated():
    """An option with no flags is visible regardless of seat."""
    opt = MenuOption("a", "Always")
    assert visible_options([opt], _seat(None, None)) == [opt]


def test_requires_seated_hides_when_unseated():
    """Seated-only option is hidden when no table is bound."""
    opt = MenuOption("a", "Seated-only", requires_seated=True)
    assert visible_options([opt], _seat(None, None)) == []


def test_requires_seated_visible_when_seated():
    """Seated-only option is visible when a table is bound, regardless
    of game type (no ``allowed_game_types`` set)."""
    opt = MenuOption("a", "Seated-only", requires_seated=True)
    assert visible_options([opt], _seat("tbl-1", "blackjack")) == [opt]


def test_allowed_game_types_hides_when_type_outside_set():
    """With ``allowed_game_types`` set, an option whose game type is
    not in the set is hidden."""
    opt = MenuOption(
        "h", "Hit",
        requires_seated=True,
        allowed_game_types=frozenset({"blackjack"}),
    )
    assert visible_options([opt], _seat("tbl-1", "poker")) == []


def test_allowed_game_types_visible_when_type_in_set():
    opt = MenuOption(
        "h", "Hit",
        requires_seated=True,
        allowed_game_types=frozenset({"blackjack"}),
    )
    assert visible_options([opt], _seat("tbl-1", "blackjack")) == [opt]


def test_allowed_game_types_hides_post_join_window():
    """When ``current_table_game_type`` is ``None`` (post-join window
    before the first game_state reply), ``allowed_game_types``-bound
    options are hidden. Covers the brief window between
    ``join_table`` and the server's game type reply."""
    opt = MenuOption(
        "h", "Hit",
        requires_seated=True,
        allowed_game_types=frozenset({"blackjack"}),
    )
    assert visible_options([opt], _seat("tbl-1", None)) == []


def test_hide_if_seated_type_hides_launcher_at_matching_table():
    """A Blackjack launcher must hide when the player is already at a
    blackjack table (the same letter cannot be claimed twice)."""
    opt = MenuOption(
        "b", "Blackjack",
        hide_if_seated_type=frozenset({"blackjack"}),
    )
    assert visible_options([opt], _seat("bj-1", "blackjack")) == []
    assert visible_options([opt], _seat(None, None)) == [opt]


def test_hide_if_seated_type_only_fires_when_seated():
    """``hide_if_seated_type`` does nothing when the player is not at
    a table (no claim to hide against)."""
    opt = MenuOption(
        "b", "Blackjack",
        hide_if_seated_type=frozenset({"blackjack"}),
    )
    assert visible_options([opt], _seat(None, None)) == [opt]


def test_requires_connected_hides_when_disconnected():
    """A ``Disconnect`` option hides when no connection is open."""
    opt = MenuOption("x", "Disconnect", requires_connected=True)
    state = SimpleNamespace(
        current_table_moniker=None,
        current_table_game_type=None,
        connected=False,
    )
    assert visible_options([opt], state) == []


def test_requires_connected_visible_when_connected():
    opt = MenuOption("x", "Disconnect", requires_connected=True)
    state = SimpleNamespace(
        current_table_moniker=None,
        current_table_game_type=None,
        connected=True,
    )
    assert visible_options([opt], state) == [opt]


def test_combined_seat_and_connection_gates():
    """A seat-gated AND connected-gated option is visible only when
    BOTH conditions hold."""
    opt = MenuOption(
        "x", "Both",
        requires_seated=True,
        requires_connected=True,
    )
    # only seated: hide
    assert visible_options([opt], _seat("tbl", "blackjack")) == []
    # only connected: hide
    state = SimpleNamespace(
        current_table_moniker=None,
        current_table_game_type=None,
        connected=True,
    )
    assert visible_options([opt], state) == []
    # both: visible
    state.connected = True
    state.current_table_moniker = "tbl"
    state.current_table_game_type = "blackjack"
    assert visible_options([opt], state) == [opt]


def test_partial_state_object_does_not_raise():
    """A state object that lacks ``connected`` (or any of the duck-
    typed attributes) is treated as if the missing attribute were
    ``None`` / ``False``. No ``AttributeError``."""
    opt = MenuOption("x", "Connected-only", requires_connected=True)
    # state with NO attributes at all
    assert visible_options([opt], object()) == []


def test_visible_options_returns_fresh_list():
    """Mutating the result does not affect subsequent calls."""
    opt = MenuOption("a", "A")
    out = visible_options([opt], _seat(None, None))
    out.clear()
    assert visible_options([opt], _seat(None, None)) == [opt]
