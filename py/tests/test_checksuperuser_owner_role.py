"""The install gate accepts only a superuser.

Install-time DDL is run by a database superuser, not by a member of a shared
owner role. Membership in any role (including zoid6) must not pass the gate.
"""

import inspect

from bbsengine6.backend import checksuperuser


def test_gate_has_no_owner_role_constant():
    assert not hasattr(checksuperuser, "OWNER_ROLE"), \
        "OWNER_ROLE was removed: superuser is the only install gate"


def test_gate_has_no_owner_membership_helper():
    assert not hasattr(checksuperuser, "_is_owner_member"), \
        "_is_owner_member was removed with the zoid6 member path"


def test_gate_does_not_name_zoid6():
    src = inspect.getsource(checksuperuser)
    assert "zoid6" not in src, "the install gate must not name a project role"


def test_gate_still_requires_rolsuper():
    src = inspect.getsource(checksuperuser.main)
    assert "rolsuper" in src


def test_gate_checks_the_connecting_database_role_not_the_os_login():
    """The install connects as a database role. The gate must test that role,
    not the OS login name, which can differ from the database role."""
    src = inspect.getsource(checksuperuser.main)
    assert "current_user" in src or "_connecting_role" in src, \
        "the gate must read the connecting database role"
    assert "getcurrentloginid" not in src, \
        "getcurrentloginid is the OS login; it does not identify the install's database role"


def test_refusal_message_does_not_offer_zoid6_membership():
    src = inspect.getsource(checksuperuser.main)
    assert "member of" not in src, "membership is no longer an accepted path"
