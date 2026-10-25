"""insert() must not write the plaintext password into engine.__member.

The add flow inserts the member, then hashes the password with setpassword. insert() passed
the plaintext through to the row, and chk_member_password_bcrypt rejected it. insert() already
drops attrs and id; it must drop password too. update() already strips it.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as libmember


@pytest.mark.unit
def test_insert_does_not_send_the_plaintext_password_to_the_database():
    member = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y",
              "password": "12345", "flags": {}}
    with patch.object(libmember.database, "insert", return_value="lo_test") as dbi, \
         patch.object(libmember, "_validate_moniker_shape"), \
         patch.object(libmember.io, "echo"):
        libmember.insert(object(), member, conn=MagicMock())
    cols = dbi.call_args.args[2]
    assert "password" not in cols, cols


@pytest.mark.unit
def test_insert_still_sends_the_other_columns():
    member = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y",
              "password": "12345", "flags": {}}
    with patch.object(libmember.database, "insert", return_value="lo_test") as dbi, \
         patch.object(libmember, "_validate_moniker_shape"), \
         patch.object(libmember.io, "echo"):
        libmember.insert(object(), member, conn=MagicMock())
    cols = dbi.call_args.args[2]
    assert cols.get("moniker") == "lo_test" and cols.get("email") == "x@y", cols
