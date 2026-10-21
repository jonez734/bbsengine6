"""checkwebserverrole grants member to www-data only when it is not already granted.

Re-running GRANT member TO www-data as a role without ADMIN OPTION on member is
refused, which stopped bootstrap even though the membership already existed.
The check must read the current membership and skip the grant when present.
"""

import inspect

from bbsengine6.backend import checkwebserverrole


def test_member_grant_is_conditional_on_current_membership():
    src = inspect.getsource(checkwebserverrole.main)
    assert "pg_has_role" in src or "pg_auth_members" in src, \
        "checkwebserverrole must check existing membership before granting"
