"""``bbsengine6.message.access`` authorizes the ``send`` op: a member sends only as themselves.

The sender is the ``sender`` field of the message. A sysop may send as anyone, matching the
other message ops. An unbound session, or an empty sender, is always denied.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bbsengine6.message import access as message_access

pytestmark = pytest.mark.unit


def _session(moniker=None, *, is_sysop=False):
    return SimpleNamespace(moniker=moniker, is_sysop=is_sysop)


def test_send_allowed_when_sender_is_the_session_member():
    s = _session("alice")
    assert message_access(None, "send", session=s, message={"sender": "alice"}) is True


def test_send_denied_when_sender_is_someone_else():
    s = _session("alice")
    assert message_access(None, "send", session=s, message={"sender": "bob"}) is False


def test_send_allowed_for_sysop_as_any_sender():
    s = _session("sysop", is_sysop=True)
    assert message_access(None, "send", session=s, message={"sender": "alice"}) is True


def test_send_denied_without_a_sender():
    s = _session("alice")
    assert message_access(None, "send", session=s, message={}) is False


def test_send_denied_when_session_unbound():
    assert message_access(None, "send", session=None, message={"sender": "alice"}) is False
