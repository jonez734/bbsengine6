"""checkcreatedb accepts CREATE on the target database, as its docstring says.

The docstring allows a role that has CREATE on the target database, but the code
required rolcreatedb or superuser. An existing database needs only object
creation rights, so the least-privilege grant should pass the check.
"""

import inspect

from bbsengine6.backend import checkcreatedb


def test_check_accepts_database_create_privilege():
    src = inspect.getsource(checkcreatedb.main)
    assert "has_database_privilege" in src, \
        "checkcreatedb must accept CREATE on the target database"
