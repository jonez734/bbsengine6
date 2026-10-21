"""New member roles are m_<moniker>; an existing engine.pgrole row wins.

zoid6 maps member jam to the pre-existing role jam, and every other member gets
the m_ prefix. The prefix is applied by role_name_for, which is used only when
no tracking row exists.
"""

import pytest

from bbsengine6 import pgrole


@pytest.mark.unit
@pytest.mark.parametrize("moniker,expected", [
    ("alice", "m_alice"),
    ("Alice", "m_alice"),
    ("bj2p_a_3bf8fa85", "m_bj2p_a_3bf8fa85"),
    ("odd-name.x", "m_odd_name_x"),
])
def test_new_member_role_has_m_prefix(moniker, expected):
    assert pgrole.role_name_for(moniker) == expected
