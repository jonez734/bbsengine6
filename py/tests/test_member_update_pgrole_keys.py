"""member.lib.update must not write the data role to engine.__member.

psqlrole belongs to engine.pgrole. The member edit form carries it so configurerole can apply
it. Sending it to the engine.__member UPDATE would fail, since the column does not exist there.
"""

import pytest

from bbsengine6.member import lib as libmember


PGROLE_ONLY = ("psqlrole",)


@pytest.mark.unit
def test_pgrole_only_keys_are_removed_before_the_member_write(monkeypatch):
    seen = {}

    def fake_update(args, table, pk, items, **kwargs):
        seen["items"] = dict(items)
        return True

    from bbsengine6 import database
    monkeypatch.setattr(database, "update", fake_update)
    monkeypatch.setattr(libmember, "_update_member_flags", lambda *a, **k: True)

    class _Conn:
        def rollback(self):
            pass

        def commit(self):
            pass

    libmember.update(
        None,
        {"moniker": "jam", "loginid": "jam", "email": "j@x", "psqlrole": "m_jam"},
        moniker="jam",
        conn=_Conn(),
    )
    assert "items" in seen, "the member write was not reached"
    for key in PGROLE_ONLY:
        assert key not in seen["items"], f"{key} would be written to engine.__member"
    assert seen["items"].get("email") == "j@x"
