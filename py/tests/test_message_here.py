"""@here: a dynamic group resolved by the host application for the sender.

bbsengine6 does not know what "here" means. The host registers a resolver
that maps the sender to a group name. @here expands through that group, so the
normal membership rule applies.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.message import service as svc


@pytest.fixture(autouse=True)
def _reset_resolver():
    svc.set_here_resolver(None)
    yield
    svc.set_here_resolver(None)


@pytest.fixture
def groups():
    with patch.object(svc, "_resolve_db", return_value="zoid6test"), \
         patch.object(svc, "_make_args", return_value=MagicMock()), \
         patch.object(svc, "dal_recipients") as dr, \
         patch.object(svc, "dal_groups") as dg, \
         patch.object(svc, "get_message_group_members", return_value=["alice", "bob"]), \
         patch("bbsengine6.member.lib.issysop", return_value=False):
        dr.get_group_id_by_name.return_value = 7
        dg.is_member.return_value = True
        yield dr, dg


@pytest.mark.unit
def test_here_expands_through_the_resolved_group(groups):
    svc.set_here_resolver(lambda sender: f"table:jam")
    assert svc.resolve_recipients(["@here"], sender_moniker="alice") == ["alice", "bob"]


@pytest.mark.unit
def test_here_resolves_per_sender(groups):
    seen = []
    def resolver(sender):
        seen.append(sender)
        return "table:jam"
    svc.set_here_resolver(resolver)
    svc.resolve_recipients(["@here"], sender_moniker="alice")
    assert seen == ["alice"]


@pytest.mark.unit
def test_here_without_resolver_is_refused(groups):
    with pytest.raises(PermissionError, match="not available"):
        svc.resolve_recipients(["@here"], sender_moniker="alice")


@pytest.mark.unit
def test_here_when_sender_has_no_location_is_refused(groups):
    svc.set_here_resolver(lambda sender: None)
    with pytest.raises(PermissionError, match="no current location"):
        svc.resolve_recipients(["@here"], sender_moniker="alice")


@pytest.mark.unit
def test_here_still_requires_membership(groups):
    dr, dg = groups
    dg.is_member.return_value = False
    svc.set_here_resolver(lambda sender: "table:jam")
    with pytest.raises(PermissionError):
        svc.resolve_recipients(["@here"], sender_moniker="carol")


@pytest.mark.unit
def test_plain_group_named_here_is_not_special(groups):
    # A registry group literally named "here" would collide with the keyword.
    # The keyword wins, so the reserved name must be refused at creation.
    assert svc.is_reserved_group_name("here") is True
    assert svc.is_reserved_group_name("crew") is False


@pytest.mark.unit
@pytest.mark.parametrize("name", ["here", "HERE", "everyone", "Everyone"])
def test_creating_a_group_with_a_reserved_name_is_refused(name):
    with patch.object(svc, "_resolve_db", return_value="zoid6test"), \
         patch.object(svc, "_make_args", return_value=MagicMock()), \
         patch.object(svc, "dal_recipients") as dr, \
         patch.object(svc, "dal_groups") as dg:
        with pytest.raises(ValueError, match="reserved"):
            svc.ensure_message_group(name)
        dg.create.assert_not_called()
