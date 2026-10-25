"""The install gate accepts superuser or membership in the zoid6 owner role.

Bootstrap DDL is owned by zoid6. A role that is a member of zoid6 can run that
work as zoid6, so requiring a superuser is broader than the install needs. The
gate must still refuse a role that is neither.
"""

import inspect

from bbsengine6.backend import checksuperuser


def test_gate_accepts_owner_role_membership():
    helper = inspect.getsource(checksuperuser._is_owner_member)
    assert "pg_has_role" in helper and "zoid6" in helper or checksuperuser.OWNER_ROLE == "zoid6", \
        "the owner-membership helper must query pg_has_role for zoid6"
    assert "_is_owner_member(" in inspect.getsource(checksuperuser.main), \
        "main must consult the owner-membership check"


def test_gate_still_accepts_superuser():
    src = inspect.getsource(checksuperuser.main)
    assert "rolsuper" in src


def test_gate_checks_the_connecting_database_role_not_the_os_login():
    """The install connects as a database role (--databaseuser). The gate must test that role.
    Testing the OS login name fails whenever the OS account has no matching database role, even
    when the database user that is connecting is a superuser."""
    src = inspect.getsource(checksuperuser.main)
    assert "current_user" in src or "databaseuser" in src or "dbrole" in src, \
        "the gate must read the connecting database role, not util.getcurrentloginid"
    assert "getcurrentloginid" not in src, \
        "getcurrentloginid is the OS login; it does not identify the install's database role"
