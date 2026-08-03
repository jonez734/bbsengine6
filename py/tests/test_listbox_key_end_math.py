"""
Regression tests for Phase 4 listbox.py hardening.

Covers:
- _handle_key_end uses (last_idx - old_idx + 1) * itemheight math
  (matching _handle_key_home) so the cursor lands on the last item, not
  one row below it.
"""

from unittest.mock import patch, MagicMock

import pytest


pytestmark = pytest.mark.unit


def _build_listbox(items_per_page=20, item_height=1, num_items=10):
    from bbsengine6.listbox import Listbox, ListboxItem

    args = MagicMock()
    args.debug = False
    items = [ListboxItem(content=f"item {i}") for i in range(num_items)]
    return Listbox(
        args=args,
        itemsperpage=items_per_page,
        itemheight=item_height,
        items=items,
    )


def test_handle_key_end_uses_plus_one_math():
    """The cursor-down displacement after KEY_END must be
    (last_idx - old_idx + 1) * itemheight — matching the home math — so
    the cursor lands on the last item, not one line below."""
    import inspect

    from bbsengine6 import listbox as listbox_module

    src = inspect.getsource(listbox_module.Listbox._handle_key_end)
    # Must use +1 to account for cursor sitting one row below the
    # unhighlighted redraw line.
    assert "(last_idx - old_idx + 1)" in src, (
        "_handle_key_end must use '(last_idx - old_idx + 1)' — "
        "missing the +1 cursor-row offset causes the highlight to land "
        "one row below the intended item"
    )


def test_handle_key_home_uses_same_math_convention():
    """_handle_key_home must use the symmetric '(old_idx - first_idx + 1)'
    so END and HOME stay consistent."""
    import inspect

    from bbsengine6 import listbox as listbox_module

    src_home = inspect.getsource(listbox_module.Listbox._handle_key_home)
    src_end = inspect.getsource(listbox_module.Listbox._handle_key_end)
    assert "(old_idx - first_idx + 1)" in src_home
    assert "(last_idx - old_idx + 1)" in src_end


def test_handle_key_end_returns_true_when_at_last_item():
    """Pressing END when already at last item should return True (idempotent)
    and not raise."""
    from bbsengine6 import listbox as listbox_module

    lb = _build_listbox(items_per_page=10, item_height=1, num_items=3)

    # First move to last enabled item, then call again to test idempotency.
    last_idx = lb._get_last_enabled_index(lb.fetchitems())
    lb._currentindex = last_idx

    captured = []

    def fake_echo(s, **kwargs):
        captured.append(s)

    with patch.object(listbox_module.io, "echo", fake_echo):
        result = lb._handle_key_end()
    assert result is True


def test_handle_key_end_moves_highlight_to_last_item():
    """Pressing END from index 0 with item_height=1 must move
    _currentindex to the last enabled item on the page."""
    from bbsengine6 import listbox as listbox_module

    lb = _build_listbox(items_per_page=10, item_height=1, num_items=3)
    lb._currentindex = 0

    captured = []

    def fake_echo(s, **kwargs):
        captured.append(s)

    with patch.object(listbox_module.io, "echo", fake_echo):
        lb._handle_key_end()

    assert lb._currentindex == lb._get_last_enabled_index(lb.fetchitems())


def test_handle_key_end_with_itemheight_two_uses_correct_displacement():
    """With itemheight=2 the displacement must be 2x the index delta."""
    from bbsengine6.listbox import Listbox, ListboxItem
    from bbsengine6 import listbox as listbox_module

    lb = _build_listbox(items_per_page=10, item_height=2, num_items=3)
    lb._currentindex = 0
    last_idx = 2

    captured = []

    def fake_echo(s, **kwargs):
        captured.append(s)

    with patch.object(listbox_module.io, "echo", fake_echo):
        lb._handle_key_end()

    # Check that the displacement echo used the corrected +1 math:
    # (last_idx - old_idx + 1) * itemheight = (2 - 0 + 1) * 2 = 6
    # The OLD bug would have produced (last_idx - old_idx - 1) * itemheight = 2.
    expected_disp = (last_idx - 0 + 1) * lb.itemheight
    assert lb._currentindex == last_idx
    # Find the {{cursordown:N}} echo and assert N matches the corrected math.
    # The echo calls may concatenate multiple directives into a single string,
    # so check substring containment rather than exact match.
    expected_token = f"{{cursordown:{expected_disp}}}"
    found = any(
        expected_token in s for s in captured if isinstance(s, str)
    )
    assert found, (
        f"expected {expected_token!r} in echo calls, got: {captured!r}"
    )
    # And the buggy math (last_idx - old_idx - 1) * itemheight = 2 must NOT appear.
    buggy_token = "{cursordown:2}"
    assert not any(
        buggy_token in s for s in captured if isinstance(s, str)
    ), "the pre-Phase-4 buggy displacement ({cursordown:2}) must not appear"
