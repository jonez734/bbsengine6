"""A member may address a named group only if they belong to it (or are a sysop).

Named system sources keep the registry rule; operator/CLI calls with no sender
are unrestricted. ``@everyone`` keeps its own sysop-role rule.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.message import service as svc


@pytest.fixture
def groups():
    """A group ``crew`` with members alice and bob, and a stub DAL."""
    with patch.object(svc, "_resolve_db", return_value="zoid6test"), \
         patch.object(svc, "_make_args", return_value=MagicMock()), \
         patch.object(svc, "dal_recipients") as dr, \
         patch.object(svc, "get_message_group_members", return_value=["alice", "bob"]), \
         patch.object(svc, "dal_groups") as dg:
        dr.get_group_id_by_name.return_value = 7
        yield dr, dg


def _resolve(sender, is_sysop, groups_mod, source="member"):
    dr, dg = groups_mod
    with patch("bbsengine6.member.lib.issysop", return_value=is_sysop):
        return svc.resolve_recipients(["@crew"], sender_moniker=sender, source=source)


@pytest.mark.unit
def test_non_member_cannot_address_group(groups):
    dr, dg = groups
    dg.is_member.return_value = False
    with pytest.raises(PermissionError):
        _resolve("carol", False, groups)


@pytest.mark.unit
def test_member_can_address_their_group(groups):
    dr, dg = groups
    dg.is_member.return_value = True
    assert _resolve("alice", False, groups) == ["alice", "bob"]


@pytest.mark.unit
def test_sysop_can_address_any_group(groups):
    dr, dg = groups
    dg.is_member.return_value = False
    assert _resolve("root", True, groups) == ["alice", "bob"]


@pytest.mark.unit
def test_operator_call_without_sender_unrestricted(groups):
    dr, dg = groups
    dg.is_member.return_value = False
    assert svc.resolve_recipients(["@crew"]) == ["alice", "bob"]


@pytest.mark.unit
def test_named_source_still_uses_registry_not_membership(groups):
    dr, dg = groups
    dg.is_member.return_value = False
    dr.source_may_address_group.return_value = True
    out = svc.resolve_recipients(["@crew"], source="casino.dealer:jam")
    assert out == ["alice", "bob"]
    dr.source_may_address_group.assert_called_once()
